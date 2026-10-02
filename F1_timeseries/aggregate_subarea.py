"""
Paper 2 aggregation: per-(year, season_day, subarea, outcome) counts.

Same walk over the recruitment cohort files as krico-paper1's F3 aggregate
(date -> season-day mapping copied verbatim, Feb 29 excluded, 3840 of 3848
files processed), but each particle is additionally assigned to a CCAMLR
subarea, twice:

  - release subarea, from release_lon / release_lat   -> counts_release
  - fate subarea,    from final_lon   / final_lat     -> counts_fate

Subarea 48.6 is split at 60°S into 48.6N / 48.6S, as in Paper 1 Tables S1/S2.
Particles outside every project subarea are labelled "outside" (expected ~0
for release positions, substantial for M6 fate positions).

Point-in-polygon on 5e5 particles x 3840 cohorts is done through a lookup
raster rather than per-particle geometry tests: the subarea polygons are
rasterised once onto a regular LOOKUP_RES degree grid (shapely 2 vectorised
contains_xy), and every particle is then indexed into that raster. At 0.05°
the raster is ~2000 x 800 cells and is built in seconds; the per-cohort cost
is then dominated by reading the file, as in F3.

Inputs:  $KRICO_POST/recruitment/data/YYYY_MM_DD.nc
         ../ccamlr-data/CCAMLR_ASD_EPSG4326.shp  (or --shapefile)
Output:  data/aggregated_subarea.nc

Run on ECMWF where the cohort files live. Single core; ~the same wall time
as F3's aggregate.py. The output is small (~1 MB) and is what plot_subarea.py
reads locally.

Usage:
  export KRICO_POST=/path/to/krico-post-production
  python aggregate_subarea.py [--shapefile PATH] [--limit N]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
import xarray as xr
from shapely.ops import unary_union

# ---------------------------------------------------------------------------
# Configuration (identical to krico-paper1 F3 / F4 where they overlap)
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
SPLIT_LAT_486 = -60.0
# Output order. "outside" is last.
SUBAREAS = ["88.3", "48.1", "48.2", "48.3", "48.4", "48.5", "48.6N", "48.6S", "outside"]
N_SUBAREAS = len(SUBAREAS)
OUTSIDE = SUBAREAS.index("outside")

# Lookup raster: model domain with a small margin.
LOOKUP_RES = 0.05
LON_MIN, LON_MAX = -116.0, 41.0
LAT_MIN, LAT_MAX = -79.0, -39.0


# ---------------------------------------------------------------------------
# Date <-> season-day mapping (verbatim from F3 aggregate.py)
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
    ccamlr = ccamlr[ccamlr["GAR_Long_L"].isin(SUBAREA_CODES)]

    lon_edges = np.arange(LON_MIN, LON_MAX + LOOKUP_RES / 2, LOOKUP_RES)
    lat_edges = np.arange(LAT_MIN, LAT_MAX + LOOKUP_RES / 2, LOOKUP_RES)
    lon_c = 0.5 * (lon_edges[:-1] + lon_edges[1:])
    lat_c = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    LON, LAT = np.meshgrid(lon_c, lat_c)

    labels = np.full(LON.shape, OUTSIDE, dtype=np.int8)
    for code in SUBAREA_CODES:
        rows = ccamlr[ccamlr["GAR_Long_L"] == code]
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
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(data_dir: Path, shp_path: Path, limit: int | None = None) -> xr.Dataset:
    labels, lon_e, lat_e = build_lookup(shp_path)

    shape = (N_YEARS, N_SEASON_DAYS, N_SUBAREAS, N_OUTCOMES)
    counts_release = np.zeros(shape, dtype=np.int64)
    counts_fate = np.zeros(shape, dtype=np.int64)
    total = np.zeros((N_YEARS, N_SEASON_DAYS), dtype=np.int64)
    has_data = np.zeros((N_YEARS, N_SEASON_DAYS), dtype=bool)

    files = find_cohort_files(data_dir)
    if not files:
        raise FileNotFoundError(f"No cohort files in {data_dir}")
    if limit:
        files = files[:limit]
    print(f"Found {len(files)} cohort files in {data_dir}")

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

        with xr.open_dataset(path) as ds:
            outcome = ds["outcome"].values.astype(np.int64)
            sub_r = assign(labels, lon_e, lat_e,
                           ds["release_lon"].values, ds["release_lat"].values).astype(np.int64)
            sub_f = assign(labels, lon_e, lat_e,
                           ds["final_lon"].values, ds["final_lat"].values).astype(np.int64)

        # 2-D histogram via a combined key -> bincount.
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

    dims = ("year", "season_day", "subarea", "outcome")
    return xr.Dataset(
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
        attrs={
            "title": "KRICO Paper 2 per-subarea outcome aggregation",
            "description": "Per-(year, season_day, subarea, outcome) counts; 48.6 split at 60S; "
                           f"subarea assignment via a {LOOKUP_RES} deg lookup raster of the CCAMLR shapefile.",
        },
    )


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--shapefile",
                    default=str(here.parent / "ccamlr-data" / "CCAMLR_ASD_EPSG4326.shp"))
    ap.add_argument("--limit", type=int, default=None, help="process only the first N files (test)")
    args = ap.parse_args()

    krico_post = os.environ.get("KRICO_POST")
    if not krico_post:
        sys.exit("ERROR: KRICO_POST not set (krico-post-production root).")
    data_dir = Path(krico_post) / "recruitment" / "data"
    if not data_dir.is_dir():
        sys.exit(f"ERROR: recruitment data dir not found: {data_dir}")

    ds = aggregate(data_dir, Path(args.shapefile), args.limit)

    out_dir = here / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "aggregated_subarea.nc"
    enc = {v: {"zlib": True, "complevel": 5} for v in ds.data_vars}
    ds.to_netcdf(out_path, encoding=enc)
    print(f"Wrote {out_path}")

    # Consistency check against F3: summing over subareas must reproduce
    # per-outcome totals; release "outside" must be ~0.
    tot = ds["counts_release"].sum(dim=("year", "season_day", "subarea")).values
    print("\nOverall per-outcome counts (should match F3 aggregate):")
    for n, c in zip(OUTCOME_NAMES, tot):
        print(f"  {n:28s} {int(c):14,d}")
    outside_r = int(ds["counts_release"].sel(subarea="outside").sum())
    print(f"Release positions outside any subarea: {outside_r:,d} "
          f"({100 * outside_r / max(tot.sum(), 1):.4f}%)")


if __name__ == "__main__":
    main()
