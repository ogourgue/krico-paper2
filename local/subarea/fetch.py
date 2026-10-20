#!/usr/bin/env python3
"""Fetch the ERA5 monthly-mean surface fields over the sector from the
Copernicus Climate Data Store: 10 m u and v wind, 2 m temperature, sea
surface temperature, and the mean eastward and northward turbulent
surface stress, 1993-2025, 115W-40E, 40S to the pole, 1 x 1 degree.
These are the inputs of compute.py, which reduces them to the subarea
and box series of this folder.

    python fetch.py            submit the request, wait in the CDS queue
                               (minutes to hours), download into raw/,
                               inspect the file, write PROVENANCE.md and
                               fetch_log.json
    python fetch.py --check    compare the sha256 of what is in raw/ with
                               the last download logged; write nothing
    python fetch.py --inspect  print the structure of what is in raw/ and
                               the sanity checks; write nothing

Kept in raw/:

    era5_request.json             the request exactly as sent (committed:
                                  it is the recipe)
    era5_sector_monthly*.nc       the field(s), not committed (see README);
                                  one file when the CDS returns one NetCDF,
                                  or era5_sector_monthly_<member>.nc for
                                  each member when it returns a zip (the
                                  CDS packs instantaneous fields and mean
                                  rates in separate files); the original
                                  member names are in fetch_log.json

Requirements: a free CDS account with the API key in ~/.cdsapirc, the
ERA5 licence accepted once on the dataset page, cdsapi 0.7 or later
(current request keys data_format and download_format), and xarray +
netCDF4 for the inspection and the month-by-month comparison with a
previous download (the download itself needs only cdsapi). Nothing is
imported from elsewhere in the repository.

ERA5 is released under CC-BY 4.0 (Copernicus). The downloaded field is
not committed: it is re-downloadable from a versioned, DOI'd source, and
the request file with the sha256 in PROVENANCE.md and fetch_log.json is
the record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
REQUEST_FILE = RAW / "era5_request.json"
LOG_FILE = HERE / "fetch_log.json"
PROVENANCE = HERE / "PROVENANCE.md"
FILE_STEM = "era5_sector_monthly"
DOWNLOAD_TMP = RAW / f"{FILE_STEM}.download"

CDS_DATASET = "reanalysis-era5-single-levels-monthly-means"
CDS_DOI = "10.24381/cds.f17050d7"
FIRST_YEAR, LAST_YEAR = 1993, 2025
AREA = [-40, -115, -90, 40]          # north, west, south, east (degrees)
GRID = [1.0, 1.0]
VARIABLES = {                        # CDS request name -> short name in the NetCDF
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
    "2m_temperature": "t2m",
    "sea_surface_temperature": "sst",
    "mean_eastward_turbulent_surface_stress": "metss",
    "mean_northward_turbulent_surface_stress": "mntss",
}
# The CDS converter has served the stresses as metss/mntss (GRIB1 names) and,
# since 2026, as avg_iews/avg_inss (time averages of iews/inss, the short
# names of the instantaneous eastward/northward turbulent surface stress);
# both are accepted.
ALIASES = {"metss": ("metss", "avg_iews"), "mntss": ("mntss", "avg_inss")}
EXPECTED_UNITS = {"u10": "m s**-1", "v10": "m s**-1", "t2m": "K", "sst": "K",
                  "metss": "N m**-2", "mntss": "N m**-2"}
TIME_DIMS = ("valid_time", "time", "date")
N_MONTHS = 12 * (LAST_YEAR - FIRST_YEAR + 1)


def build_request() -> dict:
    return {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": list(VARIABLES),
        "year": [str(y) for y in range(FIRST_YEAR, LAST_YEAR + 1)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "time": ["00:00"],
        "area": AREA,
        "grid": GRID,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def field_files() -> list[Path]:
    return sorted(p for p in RAW.glob(f"{FILE_STEM}*.nc") if not p.name.endswith(".previous.nc"))


# ---------------------------------------------------------------- download

def download(request: dict) -> list[dict]:
    """Submit the request, download, unpack a zip if the CDS sent one.
    Returns one entry per NetCDF file now in raw/."""
    try:
        import cdsapi
    except ImportError:
        print("cdsapi is not installed: pip install cdsapi", file=sys.stderr)
        raise SystemExit(2)
    RAW.mkdir(exist_ok=True)
    REQUEST_FILE.write_text(json.dumps({"dataset": CDS_DATASET, "request": request}, indent=2) + "\n",
                            encoding="utf-8")
    print(f"submitting the request to the CDS ({FIRST_YEAR}-{LAST_YEAR}, {len(VARIABLES)} variables, "
          f"{GRID[0]} degree); this waits in the CDS queue, possibly for a long time")
    client = cdsapi.Client()
    client.retrieve(CDS_DATASET, request, str(DOWNLOAD_TMP))
    with DOWNLOAD_TMP.open("rb") as f:
        magic = f.read(8)
    files = []
    if magic.startswith(b"PK"):
        with zipfile.ZipFile(DOWNLOAD_TMP) as z:
            members = [m for m in z.namelist() if m.endswith(".nc")]
            if not members:
                raise RuntimeError(f"the CDS returned a zip without NetCDF members: {z.namelist()}")
            for m in members:
                suffix = Path(m).stem.removeprefix("data_")
                target = RAW / f"{FILE_STEM}_{suffix}.nc"
                with z.open(m) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                files.append({"name": target.name, "member": m})
        DOWNLOAD_TMP.unlink()
        print(f"the CDS returned a zip of {len(files)} NetCDF file(s): " + ", ".join(f["member"] for f in files))
    elif magic.startswith(b"\x89HDF") or magic.startswith(b"CDF"):
        target = RAW / f"{FILE_STEM}.nc"
        DOWNLOAD_TMP.replace(target)
        files.append({"name": target.name, "member": None})
    else:
        raise RuntimeError(f"unrecognised download (first bytes {magic!r}); left as raw/{DOWNLOAD_TMP.name}")
    for f in files:
        p = RAW / f["name"]
        f["bytes"], f["sha256"] = p.stat().st_size, sha256_file(p)
        print(f"raw/{f['name']}: {f['bytes'] / 1e6:.1f} MB, sha256 {f['sha256'][:12]}…")
    return files


# ---------------------------------------------------------------- reading

def canonical(name: str) -> str:
    """Served variable name -> the name used here (avg_iews -> metss)."""
    for short, served in ALIASES.items():
        if name in served:
            return short
    return name


def open_fields(paths: list[Path], stamps: dict | None = None):
    """Merge the file(s) into one Dataset (valid_time, latitude, longitude):
    scalar/auxiliary coordinates dropped, latitude ascending, every time
    stamp floored to the first of its month (the analysis means and the
    forecast means are stamped at different hours of the same month, and
    an outer join on the raw stamps would double the axis), stress
    variables renamed to metss/mntss whatever name they were served under.
    If stamps is a dict, each file's first raw time stamp is recorded in it."""
    import pandas as pd
    import xarray as xr
    parts = []
    for p in paths:
        with xr.open_dataset(p) as ds:
            ds = ds.load()
        tdim = next((d for d in TIME_DIMS if d in ds.dims), None)
        if tdim is None:
            raise ValueError(f"{p.name}: no time dimension among {TIME_DIMS}; dims are {dict(ds.sizes)}")
        if tdim != "valid_time":
            ds = ds.rename({tdim: "valid_time"})
        if stamps is not None:
            stamps[p.name] = str(ds["valid_time"].values[0])[:16]
        months = pd.DatetimeIndex(ds["valid_time"].values).to_period("M")
        if months.has_duplicates:
            raise ValueError(f"{p.name}: more than one time stamp in the same month")
        ds = ds.assign_coords(valid_time=months.to_timestamp())
        drop = [c for c in ("expver", "number") if c in ds.coords or c in ds.variables]
        ds = ds.drop_vars(drop)
        for d in list(ds.dims):
            if d not in ("valid_time", "latitude", "longitude") and ds.sizes[d] == 1:
                ds = ds.squeeze(d, drop=True)
        renames = {v: canonical(v) for v in ds.data_vars if canonical(v) != v}
        ds = ds.rename(renames)
        for served, short in renames.items():
            ds[short].attrs["served_as"] = served
        parts.append(ds)
    ds = xr.merge(parts, compat="no_conflicts", join="outer")
    return ds.sortby("latitude").sortby("valid_time")


def inspect(paths: list[Path]) -> dict:
    """Print the structure and the sanity checks; return a summary for the log."""
    import numpy as np
    stamps: dict = {}
    ds = open_fields(paths, stamps)
    for name, first in stamps.items():
        print(f"  {name}: first raw time stamp {first} (floored to the month)")
    t = ds["valid_time"].values
    months = [f"{str(x)[:7]}" for x in t]
    summary = {"files": [p.name for p in paths], "dims": {k: int(v) for k, v in ds.sizes.items()},
               "first_month": months[0], "last_month": months[-1], "n_months": len(months),
               "latitude": [float(ds.latitude.min()), float(ds.latitude.max())],
               "longitude": [float(ds.longitude.min()), float(ds.longitude.max())],
               "variables": {}, "warnings": []}
    print(f"dims {summary['dims']}; {len(months)} months {months[0]} to {months[-1]}; "
          f"latitude {summary['latitude'][0]:.1f} to {summary['latitude'][1]:.1f}, "
          f"longitude {summary['longitude'][0]:.1f} to {summary['longitude'][1]:.1f}")
    expected_months = [f"{y}-{m:02d}" for y in range(FIRST_YEAR, LAST_YEAR + 1) for m in range(1, 13)]
    if months != expected_months:
        missing = sorted(set(expected_months) - set(months))
        extra = sorted(set(months) - set(expected_months))
        dup = len(months) - len(set(months))
        summary["warnings"].append(f"month axis differs from {FIRST_YEAR}-01..{LAST_YEAR}-12: "
                                   f"{len(missing)} missing, {len(extra)} extra, {dup} duplicated")
    for short in VARIABLES.values():
        if short not in ds:
            summary["warnings"].append(f"variable {short} (or an alias) not found; file has {list(ds.data_vars)}")
            continue
        da = ds[short]
        units = da.attrs.get("units", "?")
        v = da.values
        finite = np.isfinite(v)
        entry = {"dims": list(da.dims), "units": units, "dtype": str(da.dtype),
                 "min": float(np.nanmin(v)), "max": float(np.nanmax(v)),
                 "nan_fraction": float(1 - finite.mean())}
        summary["variables"][short] = entry
        flag = "" if units == EXPECTED_UNITS[short] else f"  (expected units {EXPECTED_UNITS[short]})"
        alias = f"  (served as {da.attrs['served_as']})" if "served_as" in da.attrs else ""
        print(f"  {short:6s} {str(entry['dims']):44s} {units:9s} min {entry['min']:9.3f} max {entry['max']:9.3f} "
              f"NaN {100 * entry['nan_fraction']:.1f}%{flag}{alias}")
        if alias:
            entry["served_as"] = da.attrs["served_as"]
        if flag:
            summary["warnings"].append(f"{short}: units {units!r}, expected {EXPECTED_UNITS[short]!r}")
    # Sign check: the westerly belt must push the surface eastward (positive metss).
    if "metss" in ds and "sst" in ds:
        belt = ds.sel(latitude=slice(-60, -50))
        ocean = belt["metss"].where(np.isfinite(belt["sst"]))
        belt_mean = float(ocean.mean())
        summary["metss_belt_50_60S_mean"] = belt_mean
        verdict = "positive: eastward stress on the surface under the westerlies, as ERA5 defines it" \
            if belt_mean > 0 else "NEGATIVE: not the ERA5 convention, stop and look"
        print(f"  sign check: mean metss over ocean, 50-60S, all months = {belt_mean:+.3f} N m-2 -> {verdict}")
        if belt_mean <= 0:
            summary["warnings"].append("metss belt mean not positive")
    if "t2m" in ds:
        lo, hi = summary["variables"]["t2m"]["min"], summary["variables"]["t2m"]["max"]
        if not (180 < lo < 290 and 250 < hi < 310):
            summary["warnings"].append(f"t2m range {lo:.1f}-{hi:.1f} K looks wrong for 40-90S")
    # ERA5T (preliminary) months carry expver 0005; 1993-2025 must be final (0001) throughout.
    try:
        import xarray as xr
        for p in paths:
            with xr.open_dataset(p) as raw:
                if "expver" in raw:
                    vals = sorted({str(v) for v in raw["expver"].values.ravel()})
                    if vals != ["0001"]:
                        summary["warnings"].append(f"{p.name}: expver values {vals} (0005 = ERA5T, preliminary)")
    except Exception as e:                       # the check is advisory
        summary["warnings"].append(f"expver not checked: {e}")
    for w in summary["warnings"]:
        print(f"  WARNING: {w}")
    if not summary["warnings"]:
        print("  all checks passed")
    return summary


def compare_months(old: list[Path], new: list[Path]) -> dict:
    """Months whose values changed between the previous and the new download,
    per variable; {} when identical."""
    import numpy as np
    a, b = open_fields(old), open_fields(new)
    changed = {}
    for short in VARIABLES.values():
        if short not in a or short not in b:
            changed[short] = "not comparable"
            continue
        x, y = a[short], b[short]
        if x.shape != y.shape or not np.array_equal(x.valid_time.values, y.valid_time.values):
            changed[short] = "shape or time axis differs"
            continue
        diff = np.abs(x.values - y.values)
        diff = np.where(np.isnan(x.values) & np.isnan(y.values), 0.0, diff)
        moved = np.nanmax(diff.reshape(diff.shape[0], -1), axis=1) > 0
        months = [str(t)[:7] for t in x.valid_time.values[moved]]
        if months:
            changed[short] = months
    return changed


# ---------------------------------------------------------------- records

def deg(x: float, axis: str) -> str:
    """-115 -> 115W, 40 -> 40E; -40 -> 40S."""
    pos, neg = axis
    return f"{abs(x):g}{pos if x >= 0 else neg}"


def write_provenance(log: dict) -> None:
    last = log["downloads"][-1]
    s = last.get("structure") or {}
    lines = [
        "# Provenance: ERA5 monthly surface fields over the sector (local/subarea)",
        "",
        "Written by `fetch.py`; do not edit by hand. Machine-readable copy in",
        "`fetch_log.json`.",
        "",
        "## Source",
        "",
        f"- Dataset: {CDS_DATASET} (doi:{CDS_DOI}), ERA5 monthly averaged data on",
        "  single levels, Copernicus Climate Data Store",
        f"- Request: `raw/{REQUEST_FILE.name}`, monthly means of {', '.join(VARIABLES.values())},",
        f"  {FIRST_YEAR}-01 to {LAST_YEAR}-12, {deg(AREA[1], 'EW')} to {deg(AREA[3], 'EW')}, "
        f"{deg(AREA[0], 'NS')} to {deg(AREA[2], 'NS')}, "
        f"{GRID[0]} x {GRID[1]} degree (regridded by the CDS from the native 0.25)",
        "- Licence: CC-BY 4.0; cite Hersbach, H. et al. (2020), QJRMS 146, 1999-2049,",
        "  doi:10.1002/qj.3803, and the dataset DOI",
        "",
        "## Last download",
        "",
        f"- Date: {last['date']} UTC, cdsapi {last.get('cdsapi_version', '?')}",
    ]
    for f in last["files"]:
        member = f" (CDS member `{f['member']}`)" if f.get("member") else ""
        lines.append(f"- File: `raw/{f['name']}`{member}, {f['bytes']} bytes, sha256 `{f['sha256']}`")
    if s:
        lines += [f"- Structure: dims {s.get('dims')}, {s.get('n_months')} months "
                  f"{s.get('first_month')} to {s.get('last_month')}; variables "
                  + ", ".join(f"{k} [{v['units']}]" + (f" (served as {v['served_as']})" if "served_as" in v else "")
                              for k, v in s.get("variables", {}).items()),
                  f"- Sign check: mean eastward stress over ocean 50-60S = "
                  f"{s.get('metss_belt_50_60S_mean', float('nan')):+.3f} N m-2 (positive = eastward push on the surface)"]
        if s.get("warnings"):
            lines.append("- Warnings: " + "; ".join(s["warnings"]))
    ch = last.get("changed_since_previous")
    if ch is None:
        lines.append("- Previous download: none")
    elif ch == {}:
        lines.append("- Previous download: identical values in every month")
    else:
        lines.append("- Previous download: values moved in " + json.dumps(ch))
    lines += ["", "The field files are not committed; a run of `fetch.py` reproduces them and",
              "`fetch.py --check` compares the result with the hashes above.", ""]
    PROVENANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare raw/ with the last logged download; write nothing")
    ap.add_argument("--inspect", action="store_true", help="print the structure of raw/ and the checks; write nothing")
    args = ap.parse_args()
    request = build_request()
    log = json.loads(LOG_FILE.read_text(encoding="utf-8")) if LOG_FILE.exists() else \
        {"dataset": CDS_DATASET, "doi": CDS_DOI, "downloads": []}

    if args.check:
        present = field_files()
        if not present:
            print("no field file in raw/: run fetch.py")
            return 0
        if REQUEST_FILE.exists():
            sent = json.loads(REQUEST_FILE.read_text(encoding="utf-8"))["request"]
            print("request on disk " + ("matches" if sent == request else "DIFFERS from") + " the one this script builds")
        if not log["downloads"]:
            print("no download logged; raw/ holds " + ", ".join(p.name for p in present))
            return 0
        logged = {f["name"]: f["sha256"] for f in log["downloads"][-1]["files"]}
        for p in present:
            h = sha256_file(p)
            state = "unchanged" if logged.get(p.name) == h else ("CHANGED since the log" if p.name in logged else "not in the log")
            print(f"raw/{p.name}: {p.stat().st_size / 1e6:.1f} MB, sha256 {h[:12]}…, {state}")
        for name in logged:
            if name not in {p.name for p in present}:
                print(f"raw/{name}: logged but MISSING on disk")
        return 0

    if args.inspect:
        present = field_files()
        if not present:
            print("no field file in raw/: run fetch.py")
            return 0
        inspect(present)
        return 0

    # Keep the previous download aside for the month-by-month comparison.
    previous = []
    for p in field_files():
        q = p.with_name(p.name[:-3] + ".previous.nc")
        p.replace(q)
        previous.append(q)
    try:
        files = download(request)
    except BaseException:
        for q in previous:                      # put the old files back
            q.replace(q.with_name(q.name.replace(".previous.nc", ".nc")))
        raise
    try:
        import cdsapi
        version = getattr(cdsapi, "__version__", "?")
    except ImportError:
        version = "?"
    entry = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "cdsapi_version": version,
             "request_file": REQUEST_FILE.name, "files": files, "structure": None, "changed_since_previous": None}
    try:
        entry["structure"] = inspect(field_files())
        if previous:
            entry["changed_since_previous"] = compare_months(previous, field_files())
            ch = entry["changed_since_previous"]
            print("compared with the previous download: " + ("identical" if ch == {} else json.dumps(ch)))
    except ImportError as e:
        print(f"inspection skipped ({e}); install xarray and netCDF4 and run fetch.py --inspect")
    for q in previous:
        q.unlink()
    log["downloads"].append(entry)
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log)
    print(f"wrote {PROVENANCE.name} and {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
