"""
FS1 aggregation: per-(year, season_day, subarea, outcome) particle counts from
the recruitment classification run under one of three sea-ice readings.

Copy of F3_subarea_record/aggregate.py (itself F2's, the Paper 2 aggregate)
with a --source flag selecting the classification to aggregate:

  --source nsidc           $KRICO_POST/recruitment/data_nsidc/
                           NSIDC G02202 v6 sea ice on the 25 km grid (the
                           paper's classification; counts equal F3's)
  --source glorys12        $KRICO_POST/recruitment/data/
                           GLORYS12 sea ice, native 1/12 degree grid (Paper 1's
                           classification, dataset v2.0.0)
  --source glorys12_25km   $KRICO_POST/recruitment/data_glorys12_25km/
                           GLORYS12 sea ice binned onto the 25 km grid, read
                           through the NSIDC sampler

Each source is aggregated into its own file, data/aggregated_<source>.nc,
with the sha256 of the cohort files read in data/cohort_sha256_<source>.txt.
Output of different sea-ice sources is never mixed: the cohort files'
provenance attributes are checked per source (sic_source where the files
carry it, m1_sic_source and m1_spawning_offset_days in every case) and
written to the aggregate, which plot.py checks again before it reads the
three together.

Walks the cohort files YYYY_MM_DD.nc (one per release day), maps each file
to its spawning year and season day (0 = Nov 15, 119 = Mar 14; Feb 29
excluded, so 3840 of the 3848 files are used), assigns every particle to a
CCAMLR subarea twice (release position and fate position; 48.6 split at
60 S) and counts particles per outcome. The domain is the sum over
subareas: sum(counts) == total on every (year, season_day).

Subarea assignment uses a 0.05 degree lookup raster of the subarea polygons
(geopandas + shapely contains_xy once, then vectorised indexing of the
particle positions into the raster).

Inputs:  $KRICO_POST/recruitment/<source dir>/YYYY_MM_DD.nc
         ../ccamlr-data/CCAMLR_ASD_EPSG4326.shp   (or --shapefile)
Outputs: data/aggregated_<source>.nc, data/cohort_sha256_<source>.txt

Usage (reads ~56 GB of cohort files once per source):
  export KRICO_POST=/path/to/krico-post-production   # or the Post/Production dir
  python aggregate.py --source nsidc|glorys12|glorys12_25km
                      [--shapefile PATH] [--limit N] [--compare OTHER.nc]

--compare checks that counts_release, counts_fate and total equal those of
another aggregate with the same schema (for nsidc: F3's aggregate).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
import xarray as xr
from shapely.ops import unary_union

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SPAWNING_YEARS = np.arange(1994, 2026)
N_YEARS = len(SPAWNING_YEARS)
N_SEASON_DAYS = 121          # index 120 (Mar 15) allocated, never populated

OUTCOME_NAMES = (
    "success",
    "censored",
    "killed_M1",
    "killed_M4",
    "killed_M5_no_FIV",
    "killed_M5_not_on_shelf",
    "killed_M6_no_advance",
    "exited_domain",
)
N_OUTCOMES = len(OUTCOME_NAMES)

SUBAREA_CODES = ["48.1", "48.2", "48.3", "48.4", "48.5", "48.6", "88.3"]
SHAPE_FIELD = "GAR_Long_L"
SPLIT_LAT_486 = -60.0
# Output order. "outside" is last.
SUBAREAS = ["88.3", "48.1", "48.2", "48.3", "48.4", "48.5", "48.6N", "48.6S", "outside"]
N_SUBAREAS = len(SUBAREAS)
OUTSIDE = SUBAREAS.index("outside")

# Lookup raster: model domain with a small margin.
LOOKUP_RES = 0.05
LON_MIN, LON_MAX = -116.0, 41.0
LAT_MIN, LAT_MAX = -79.0, -39.0

EXPECTED_N_FILES = 3848       # Nov 15 1993 ... Mar 14 2025, every release day
EXPECTED_N_PROCESSED = 3840   # minus the eight Feb 29
EXPECTED_M1_OFFSET_DAYS = 24  # M1 evaluated at spawning, 24 days before release (v2 classification)

# The three sea-ice readings. Per source: the cohort directory under
# $KRICO_POST/recruitment/; the sic_source the files must carry (None: the
# files predate the attribute and are identified by m1_sic_source); the
# directory name m1_sic_source must then point to (None: sic_source decides);
# whether nsidc_nearest_ocean is written (gridded 25 km readings only; must
# be 0); and the reading's name.
SOURCES = {
    "nsidc": dict(
        subdir="data_nsidc",
        sic_source_prefix="NSIDC G02202 v6",
        m1_sic_dirname=None,
        nearest_ocean=True,
        reading="NSIDC G02202 v6 sea ice (25 km grid, containing cell)",
        run_script="run_year_nsidc.sh",
    ),
    "glorys12": dict(
        subdir="data",
        sic_source_prefix=None,
        m1_sic_dirname="GLORYS12",
        nearest_ocean=False,
        reading="GLORYS12v1 sea ice (native 1/12 degree grid)",
        run_script="run_year.sh",
    ),
    "glorys12_25km": dict(
        subdir="data_glorys12_25km",
        sic_source_prefix="GLORYS12v1 ice binned onto the NSIDC G02202 25 km grid",
        m1_sic_dirname=None,
        nearest_ocean=True,
        reading="GLORYS12v1 sea ice binned onto the NSIDC 25 km grid (containing cell)",
        run_script="run_year_glorys12_25km.sh",
    ),
}
# sic_source written for cohort files that predate the attribute (--source glorys12).
GLORYS12_SIC_SOURCE = "GLORYS12"


# ---------------------------------------------------------------------------
# Date <-> season-day mapping (as in krico-paper1 F3)
# ---------------------------------------------------------------------------

def season_day_index(year: int, month: int, day: int, spawning_year: int) -> int | None:
    if month == 2 and day == 29:
        return None
    if month in (11, 12):
        if year != spawning_year - 1:
            return None
    elif month in (1, 2, 3):
        if year != spawning_year:
            return None
    else:
        return None
    if month == 11:
        if day < 15:
            return None
        idx = day - 15
    elif month == 12:
        idx = (30 - 15) + day
    elif month == 1:
        idx = (30 - 15) + 31 + day
    elif month == 2:
        if day > 28:
            return None
        idx = (30 - 15) + 31 + 31 + day
    elif month == 3:
        if day > 15:
            return None
        idx = (30 - 15) + 31 + 31 + 28 + day
    else:
        return None
    if idx < 0 or idx >= N_SEASON_DAYS:
        return None
    return idx


def spawning_year_for_date(year: int, month: int) -> int:
    return year + 1 if month in (11, 12) else year


COHORT_FILENAME_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})\.nc$")


def find_cohort_files(data_dir: Path) -> list[tuple[int, int, int, Path]]:
    out = []
    for path in sorted(data_dir.iterdir()):
        m = COHORT_FILENAME_RE.match(path.name)
        if m:
            y, mo, d = (int(g) for g in m.groups())
            out.append((y, mo, d, path))
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Subarea lookup raster
# ---------------------------------------------------------------------------

def build_lookup(shp_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Rasterise the subarea polygons. Returns (labels[n_lat, n_lon] int8,
    lon_edges, lat_edges). Cell value = index into SUBAREAS; OUTSIDE where
    no polygon contains the cell centre.
    """
    ccamlr = gpd.read_file(shp_path)
    ccamlr = ccamlr[ccamlr[SHAPE_FIELD].isin(SUBAREA_CODES)]

    lon_edges = np.arange(LON_MIN, LON_MAX + LOOKUP_RES / 2, LOOKUP_RES)
    lat_edges = np.arange(LAT_MIN, LAT_MAX + LOOKUP_RES / 2, LOOKUP_RES)
    lon_c = 0.5 * (lon_edges[:-1] + lon_edges[1:])
    lat_c = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    LON, LAT = np.meshgrid(lon_c, lat_c)

    labels = np.full(LON.shape, OUTSIDE, dtype=np.int8)
    for code in SUBAREA_CODES:
        rows = ccamlr[ccamlr[SHAPE_FIELD] == code]
        if rows.empty:
            print(f"WARNING: subarea {code} not in shapefile", file=sys.stderr)
            continue
        geom = unary_union(rows.geometry.values)
        inside = shapely.contains_xy(geom, LON, LAT) & (labels == OUTSIDE)
        if code == "48.6":
            labels[inside & (LAT >= SPLIT_LAT_486)] = SUBAREAS.index("48.6N")
            labels[inside & (LAT < SPLIT_LAT_486)] = SUBAREAS.index("48.6S")
        else:
            labels[inside] = SUBAREAS.index(code)

    print("Lookup raster built:", labels.shape,
          {s: int((labels == i).sum()) for i, s in enumerate(SUBAREAS)})
    return labels, lon_edges, lat_edges


def assign(labels: np.ndarray, lon_edges: np.ndarray, lat_edges: np.ndarray,
           lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Vectorised subarea index for arrays of positions; NaN or off-raster -> OUTSIDE."""
    out = np.full(lon.shape, OUTSIDE, dtype=np.int8)
    ok = np.isfinite(lon) & np.isfinite(lat)
    i = np.searchsorted(lat_edges, lat[ok], side="right") - 1
    j = np.searchsorted(lon_edges, lon[ok], side="right") - 1
    inb = (i >= 0) & (i < labels.shape[0]) & (j >= 0) & (j < labels.shape[1])
    vals = np.full(ok.sum(), OUTSIDE, dtype=np.int8)
    vals[inb] = labels[i[inb], j[inb]]
    out[ok] = vals
    return out


# ---------------------------------------------------------------------------
# Provenance checks per source
# ---------------------------------------------------------------------------

def check_provenance(source: str, data_dir: Path, sic_sources: set[str],
                     m1_sic_sources: set[str], offsets: set[int],
                     nearest_ocean: set[int]) -> str:
    """
    Every cohort file must carry the same provenance, and it must be the
    requested reading's. Returns the sic_source to write to the aggregate.
    """
    spec = SOURCES[source]
    if len(sic_sources) != 1:
        raise ValueError(f"cohort files in {data_dir} mix sea-ice sources: {sorted(sic_sources)}")
    if len(m1_sic_sources) != 1:
        raise ValueError(f"cohort files in {data_dir} mix M1 ice directories: {sorted(m1_sic_sources)}")
    if offsets != {EXPECTED_M1_OFFSET_DAYS}:
        raise ValueError(f"m1_spawning_offset_days is not {EXPECTED_M1_OFFSET_DAYS} in every file: "
                         f"{sorted(offsets)}")
    sic_source = next(iter(sic_sources))
    m1_dir = next(iter(m1_sic_sources))

    if spec["sic_source_prefix"] is not None:
        if sic_source is None or not sic_source.startswith(spec["sic_source_prefix"]):
            raise ValueError(f"cohort files in {data_dir} are not the {source} classification: "
                             f"sic_source = {sic_source!r}")
    else:
        # Native GLORYS12: the files either predate the attribute (dataset
        # v2.0.0) or carry the plain "GLORYS12" the current code writes.
        if sic_source not in (None, GLORYS12_SIC_SOURCE):
            raise ValueError(f"cohort files in {data_dir} are not the native GLORYS12 classification: "
                             f"sic_source = {sic_source!r}")
        sic_source = GLORYS12_SIC_SOURCE

    if m1_dir is None:
        raise ValueError(f"cohort files in {data_dir} carry no m1_sic_source: not a v2 classification")
    if spec["m1_sic_dirname"] is not None and Path(m1_dir).name.upper() != spec["m1_sic_dirname"]:
        raise ValueError(f"m1_sic_source of the cohort files in {data_dir} does not point to a "
                         f"{spec['m1_sic_dirname']} directory: {m1_dir!r}")

    if spec["nearest_ocean"]:
        if nearest_ocean != {0}:
            raise ValueError(f"nsidc_nearest_ocean is not 0 in every file: {sorted(nearest_ocean)}")
    elif nearest_ocean != {-1}:
        raise ValueError(f"cohort files in {data_dir} carry nsidc_nearest_ocean, so they were sampled "
                         f"on the 25 km grid, not the native GLORYS12 classification")
    return sic_source


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(source: str, data_dir: Path, shp_path: Path, folder: str,
              limit: int | None = None) -> tuple[xr.Dataset, list[tuple[str, str]]]:
    spec = SOURCES[source]
    labels, lon_e, lat_e = build_lookup(shp_path)
    sic_sources: set[str | None] = set()
    m1_sic_sources: set[str | None] = set()
    offsets: set[int] = set()
    nearest_ocean: set[int] = set()
    hashes: list[tuple[str, str]] = []

    shape = (N_YEARS, N_SEASON_DAYS, N_SUBAREAS, N_OUTCOMES)
    counts_release = np.zeros(shape, dtype=np.int64)
    counts_fate = np.zeros(shape, dtype=np.int64)
    total = np.zeros((N_YEARS, N_SEASON_DAYS), dtype=np.int64)
    has_data = np.zeros((N_YEARS, N_SEASON_DAYS), dtype=bool)

    files = find_cohort_files(data_dir)
    if not files:
        raise FileNotFoundError(f"No cohort files in {data_dir}")
    print(f"Found {len(files)} cohort files in {data_dir}")
    if limit:
        files = files[:limit]
    elif len(files) != EXPECTED_N_FILES:
        raise ValueError(f"expected {EXPECTED_N_FILES} cohort files, found {len(files)}")

    expected_flags = " ".join(OUTCOME_NAMES)
    n_proc = n_skip = 0
    for year, month, day, path in files:
        sy = spawning_year_for_date(year, month)
        sy_idx = sy - SPAWNING_YEARS[0]
        if not (0 <= sy_idx < N_YEARS):
            n_skip += 1
            continue
        sd_idx = season_day_index(year, month, day, sy)
        if sd_idx is None:
            n_skip += 1
            continue

        hashes.append((sha256_file(path), path.name))
        with xr.open_dataset(path) as ds:
            a = ds.attrs
            sic_sources.add(None if "sic_source" not in a else str(a["sic_source"]))
            m1_sic_sources.add(None if "m1_sic_source" not in a else str(a["m1_sic_source"]))
            offsets.add(int(a.get("m1_spawning_offset_days", -1)))
            nearest_ocean.add(int(a.get("nsidc_nearest_ocean", -1)))
            flags = str(ds["outcome"].attrs.get("flag_meanings", ""))
            if flags != expected_flags:
                raise ValueError(f"{path.name}: outcome flag_meanings differ from OUTCOME_NAMES: {flags!r}")
            outcome = ds["outcome"].values.astype(np.int64)
            sub_r = assign(labels, lon_e, lat_e,
                           ds["release_lon"].values, ds["release_lat"].values).astype(np.int64)
            sub_f = assign(labels, lon_e, lat_e,
                           ds["final_lon"].values, ds["final_lat"].values).astype(np.int64)

        key_r = sub_r * N_OUTCOMES + outcome
        key_f = sub_f * N_OUTCOMES + outcome
        counts_release[sy_idx, sd_idx] = np.bincount(
            key_r, minlength=N_SUBAREAS * N_OUTCOMES).reshape(N_SUBAREAS, N_OUTCOMES)
        counts_fate[sy_idx, sd_idx] = np.bincount(
            key_f, minlength=N_SUBAREAS * N_OUTCOMES).reshape(N_SUBAREAS, N_OUTCOMES)
        total[sy_idx, sd_idx] = outcome.size
        has_data[sy_idx, sd_idx] = True
        n_proc += 1
        if n_proc % 200 == 0:
            print(f"  processed {n_proc} / {len(files)}")

    print(f"Done: {n_proc} processed, {n_skip} skipped")
    if not limit and n_proc != EXPECTED_N_PROCESSED:
        raise ValueError(f"expected {EXPECTED_N_PROCESSED} files processed (Feb 29 skipped), got {n_proc}")
    sic_source = check_provenance(source, data_dir, sic_sources, m1_sic_sources, offsets, nearest_ocean)
    m1_sic_source = next(iter(m1_sic_sources))
    print(f"Sea-ice source of the cohort files: {sic_source} (M1 ice directory {m1_sic_source})")

    dims = ("year", "season_day", "subarea", "outcome")
    attrs = {
        "title": f"KRICO Paper 2 {folder.split('_')[0]}: per-subarea outcome counts, {spec['reading']}",
        "description": "Per-(year, season_day, subarea, outcome) particle counts; 48.6 split at 60S; "
                       f"subarea assignment via a {LOOKUP_RES} deg lookup raster of the CCAMLR shapefile. "
                       f"Recruitment classification of the GLORYS12 trajectories with every sea-ice "
                       f"concentration read from {spec['reading']} (krico-post-production, "
                       f"{spec['run_script']}). The domain is the sum over subareas.",
        "ice_source": source,
        "sic_source": sic_source,
        "m1_sic_source": m1_sic_source,
        "m1_spawning_offset_days": EXPECTED_M1_OFFSET_DAYS,
        "source_data_dir": str(data_dir),
        "n_cohort_files": n_proc,
        "cohort_sha256_file": f"cohort_sha256_{source}.txt",
        "shapefile": shp_path.name,
        "shapefile_sha256": sha256_file(shp_path),
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": f"{folder}/aggregate.py (krico-paper2)",
    }
    if spec["nearest_ocean"]:
        attrs["nsidc_nearest_ocean"] = 0
    if spec["sic_source_prefix"] is None:
        attrs["sic_source_note"] = ("cohort files of dataset v2.0.0 predate the sic_source attribute; "
                                    "the reading is identified by m1_sic_source and "
                                    "m1_spawning_offset_days, checked identical in every file")
    ds = xr.Dataset(
        data_vars={
            "counts_release": (dims, counts_release,
                               {"long_name": "particles per outcome, by subarea of release position"}),
            "counts_fate": (dims, counts_fate,
                            {"long_name": "particles per outcome, by subarea of fate position (final_lon/lat)"}),
            "total": (("year", "season_day"), total,
                      {"long_name": "total number of particles released"}),
            "has_data": (("year", "season_day"), has_data),
        },
        coords={
            "year": ("year", SPAWNING_YEARS.astype(np.int32), {"long_name": "spawning year"}),
            "season_day": ("season_day", np.arange(N_SEASON_DAYS, dtype=np.int32),
                           {"description": "0 = Nov 15, 119 = Mar 14; 120 unpopulated; Feb 29 excluded"}),
            "subarea": ("subarea", np.array(SUBAREAS)),
            "outcome": ("outcome", np.array(OUTCOME_NAMES)),
        },
        attrs=attrs,
    )
    return ds, hashes


def compare(ds: xr.Dataset, other_path: Path) -> None:
    other = xr.open_dataset(other_path)
    ok = True
    for v in ("counts_release", "counts_fate", "total"):
        same = ds[v].shape == other[v].shape and bool((ds[v].values == other[v].values).all())
        print(f"  {v:15s} {'identical' if same else 'DIFFERENT'}")
        ok &= same
    print(f"Compared with {other_path}: {'all identical' if ok else 'DIFFERENCES FOUND'}")
    if not ok:
        sys.exit(1)


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=sorted(SOURCES),
                    help="which classification to aggregate (sea-ice reading)")
    ap.add_argument("--shapefile",
                    default=str(here.parent / "ccamlr-data" / "CCAMLR_ASD_EPSG4326.shp"))
    ap.add_argument("--limit", type=int, default=None, help="process only the first N files (test)")
    ap.add_argument("--compare", default=None, help="another aggregate with the same schema to compare with")
    args = ap.parse_args()

    krico_post = os.environ.get("KRICO_POST")
    if not krico_post:
        sys.exit("ERROR: KRICO_POST not set (krico-post-production root).")
    data_dir = Path(krico_post) / "recruitment" / SOURCES[args.source]["subdir"]
    if not data_dir.is_dir():
        sys.exit(f"ERROR: recruitment data dir not found: {data_dir}")
    ds, hashes = aggregate(args.source, data_dir, Path(args.shapefile), here.name, args.limit)

    out_dir = here / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"aggregated_{args.source}.nc"
    enc = {v: {"zlib": True, "complevel": 5} for v in ds.data_vars}
    ds.to_netcdf(out_path, encoding=enc)
    print(f"Wrote {out_path}")

    hash_path = out_dir / f"cohort_sha256_{args.source}.txt"
    with hash_path.open("w") as f:
        f.write(f"# sha256 of the cohort files read by aggregate.py --source {args.source}, "
                f"{ds.attrs['created']}\n")
        f.write(f"# directory: {data_dir}\n")
        f.write(f"# sic_source: {ds.attrs['sic_source']}\n")
        f.write(f"# check with: cd {data_dir} && sha256sum -c /path/to/{hash_path.name}\n")
        for h, name in hashes:
            f.write(f"{h}  {name}\n")
    print(f"Wrote {hash_path} ({len(hashes)} files)")

    # Consistency: per-outcome totals, release "outside" ~0, sum(counts) == total.
    tot = ds["counts_release"].sum(dim=("year", "season_day", "subarea")).values
    print("\nOverall per-outcome counts (release subareas summed = domain):")
    for n, c in zip(OUTCOME_NAMES, tot):
        print(f"  {n:28s} {int(c):14,d}")
    outside_r = int(ds["counts_release"].sel(subarea="outside").sum())
    print(f"Release positions outside any subarea: {outside_r:,d} "
          f"({100 * outside_r / max(tot.sum(), 1):.4f}%)")
    for v in ("counts_release", "counts_fate"):
        if not bool((ds[v].sum(dim=("subarea", "outcome")) == ds["total"]).all()):
            raise ValueError(f"{v} summed over subarea and outcome differs from total")
    print("sum(counts) == total on every (year, season_day): yes")

    if args.compare:
        compare(ds, Path(args.compare))


if __name__ == "__main__":
    main()
