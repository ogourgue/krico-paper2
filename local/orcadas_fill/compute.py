#!/usr/bin/env python3
"""Compare ERA5 2 m temperature at Base Orcadas with the READER station
series in the clean months, and fill the seven weak 2020-2023 months.

    python compute.py            write the three monthly files, compute_log.json
                                 and the compute section of PROVENANCE.md
    python compute.py --check    recompute in memory and compare with the
                                 files on disk; write nothing

Inputs
    raw/era5_orcadas_monthly*.nc              from fetch.py (t2m in K, lsm)
    ../../indices/orcadas/orcadas_monthly.csv          station, deg C, as published
    ../../indices/orcadas/orcadas_obs_pct_monthly.csv  percentage of the four
                                                       daily reports behind each mean
    (read by path; never written)

Method
    ERA5 at the station: bilinear interpolation of the four 0.25-degree
    points around 60.7S 44.7W, in deg C (the nearest point is computed as
    a check). Clean months: 1993-2025 with a station value and a report
    percentage >= 90 (READER's rule; this drops 2002-2003 at 75% and the
    seven weak months). Offset: mean of (station - ERA5) over the clean
    months of each calendar month. Fill: ERA5 + offset of the calendar
    month, rounded to the station's 0.1 deg C, for the seven listed months
    only; the script stops if any of them is not below 90%, and warns
    about other 2020-2025 months below 90% that are not filled (the
    design uses May-July only).

Outputs (year,month,value)
    orcadas_filled_monthly.csv       the station series, deg C, with the
                                     seven values replaced; same rows as
                                     the station file
    orcadas_filled_flag_monthly.csv  0 = station value, 1 = ERA5 fill
    era5_t2m_orcadas_monthly.csv     ERA5 at the station, K, 1993-2025

numpy, pandas and xarray only; nothing imported from elsewhere in the
repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LOG_FILE = HERE / "compute_log.json"
PROVENANCE = HERE / "PROVENANCE.md"
FIELD_GLOB = "era5_orcadas_monthly*.nc"
STATION_DIR = HERE.parent.parent / "indices" / "orcadas"
STATION_FILE = STATION_DIR / "orcadas_monthly.csv"
PCT_FILE = STATION_DIR / "orcadas_obs_pct_monthly.csv"

STATION = (-60.7, -44.7)             # latitude, longitude of Base Orcadas (WMO 88968)
FIRST_YEAR, LAST_YEAR = 1993, 2025
CLEAN_PCT = 90.0                     # READER's rule
FILL_MONTHS = [(2020, 5), (2021, 5), (2021, 6), (2021, 7), (2022, 6), (2023, 6), (2023, 7)]
TIME_DIMS = ("valid_time", "time", "date")
K0 = 273.15


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def open_field(paths: list[Path]):
    import xarray as xr
    parts = []
    for p in paths:
        with xr.open_dataset(p) as ds:
            ds = ds.load()
        tdim = next(d for d in TIME_DIMS if d in ds.dims)
        if tdim != "valid_time":
            ds = ds.rename({tdim: "valid_time"})
        months = pd.DatetimeIndex(ds["valid_time"].values).to_period("M")
        ds = ds.assign_coords(valid_time=months.to_timestamp())
        ds = ds.drop_vars([c for c in ("expver", "number") if c in ds.coords or c in ds.variables])
        for d in list(ds.dims):
            if d not in ("valid_time", "latitude", "longitude") and ds.sizes[d] == 1:
                ds = ds.squeeze(d, drop=True)
        parts.append(ds)
    ds = xr.merge(parts, compat="no_conflicts", join="outer").sortby("latitude").sortby("valid_time")
    if "t2m" not in ds:
        raise KeyError(f"t2m missing; variables are {list(ds.data_vars)}")
    return ds


def at_station(ds) -> tuple[pd.Series, pd.Series, dict]:
    """ERA5 t2m at the station (K): bilinear and nearest point; weights for the log."""
    lat, lon = ds["latitude"].values, ds["longitude"].values
    t2m = ds["t2m"].values
    months = pd.DatetimeIndex(ds["valid_time"].values)
    y, x = STATION
    j1 = int(np.searchsorted(lat, y)); j0 = j1 - 1            # lat ascending
    i1 = int(np.searchsorted(lon, x)); i0 = i1 - 1
    fy = (y - lat[j0]) / (lat[j1] - lat[j0]); fx = (x - lon[i0]) / (lon[i1] - lon[i0])
    bil = ((1 - fy) * (1 - fx) * t2m[:, j0, i0] + (1 - fy) * fx * t2m[:, j0, i1]
           + fy * (1 - fx) * t2m[:, j1, i0] + fy * fx * t2m[:, j1, i1])
    jn, in_ = int(np.abs(lat - y).argmin()), int(np.abs(lon - x).argmin())
    near = t2m[:, jn, in_]
    idx = pd.MultiIndex.from_arrays([months.year, months.month], names=["year", "month"])
    info = {"corners": [[float(lat[j0]), float(lon[i0])], [float(lat[j1]), float(lon[i1])]],
            "weights": [float((1 - fy) * (1 - fx)), float((1 - fy) * fx), float(fy * (1 - fx)), float(fy * fx)],
            "nearest": [float(lat[jn]), float(lon[in_])]}
    if "lsm" in ds:
        info["land_fraction_nearest"] = float(ds["lsm"].values[0, jn, in_])
    return pd.Series(bil, index=idx), pd.Series(near, index=idx), info


def read_station() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    st = pd.read_csv(STATION_FILE)
    pct = pd.read_csv(PCT_FILE)
    for f in (st, pct):
        f["value"] = pd.to_numeric(f["value"], errors="coerce")
    idx = pd.MultiIndex.from_arrays([st.year, st.month], names=["year", "month"])
    return st, pd.Series(st["value"].values, index=idx), pd.Series(pct["value"].values,
                                                                     index=pd.MultiIndex.from_arrays([pct.year, pct.month], names=["year", "month"]))


def compare(station: pd.Series, era5_c: pd.Series, clean: pd.Index) -> dict:
    s, e = station.loc[clean], era5_c.loc[clean]
    d = s - e
    per_month = {}
    for m in range(1, 13):
        sel = d.index.get_level_values("month") == m
        per_month[m] = {"n": int(sel.sum()), "offset": float(d[sel].mean()), "sd": float(d[sel].std(ddof=1))}
    resid = d - np.array([per_month[m]["offset"] for m in d.index.get_level_values("month")])
    return {"n": int(len(d)), "r": float(np.corrcoef(s, e)[0, 1]), "mean_offset": float(d.mean()),
            "rmse_raw": float(np.sqrt((d ** 2).mean())), "rmse_after_monthly_offset": float(np.sqrt((resid ** 2).mean())),
            "per_month": per_month}


def compute() -> tuple[dict[str, pd.DataFrame], dict]:
    paths = sorted(RAW.glob(FIELD_GLOB))
    if not paths:
        raise SystemExit("no ERA5 file in raw/: run fetch.py first")
    ds = open_field(paths)
    bil_k, near_k, where = at_station(ds)
    st_frame, station, pct = read_station()
    era5_c = bil_k - K0
    years = station.index.get_level_values("year")
    in_period = (years >= FIRST_YEAR) & (years <= LAST_YEAR)
    pct_al = pct.reindex(station.index)
    clean = station.index[in_period & station.notna().values & (pct_al >= CLEAN_PCT).values]
    clean = clean.intersection(era5_c.index)
    stats = compare(station, era5_c, clean)
    stats_near = compare(station, near_k - K0, clean)
    # the seven months
    fills, problems = {}, []
    for ym in FILL_MONTHS:
        p = pct_al.get(ym, np.nan)
        if not (p < CLEAN_PCT):
            problems.append(f"{ym[0]}-{ym[1]:02d} has {p}% of reports, not below {CLEAN_PCT:.0f}%")
            continue
        off = stats["per_month"][ym[1]]["offset"]
        fills[ym] = {"station_value": None if pd.isna(station.get(ym, np.nan)) else float(station[ym]),
                     "pct": float(p), "era5_c": float(era5_c[ym]), "offset": off,
                     "fill": float(np.round(era5_c[ym] + off, 1))}
    if problems:
        raise SystemExit("fill list does not match the percentage file: " + "; ".join(problems))
    weak_other = [f"{y}-{m:02d} ({v:.0f}%)" for (y, m), v in pct_al.items()
                  if 2020 <= y <= LAST_YEAR and v < CLEAN_PCT and (y, m) not in fills]
    # outputs
    filled = st_frame.copy()
    flag = st_frame.copy()
    flag["value"] = 0
    for ym, f in fills.items():
        row = (filled.year == ym[0]) & (filled.month == ym[1])
        filled.loc[row, "value"] = f["fill"]
        flag.loc[row, "value"] = 1
    era5_out = pd.DataFrame({"year": bil_k.index.get_level_values("year"), "month": bil_k.index.get_level_values("month"),
                             "value": np.round(bil_k.values, 2)})
    out = {"orcadas_filled": filled, "orcadas_filled_flag": flag, "era5_t2m_orcadas": era5_out}
    info = {"era5_files": {p.name: sha256_file(p) for p in paths},
            "station_files": {STATION_FILE.name: sha256_file(STATION_FILE), PCT_FILE.name: sha256_file(PCT_FILE)},
            "interpolation": where, "clean_months": stats, "clean_months_nearest_point": stats_near,
            "fills": {f"{y}-{m:02d}": v for (y, m), v in fills.items()}, "weak_months_not_filled": weak_other}
    return out, info


def write_provenance(log: dict) -> None:
    c, f = log["clean_months"], log["fills"]
    pm = c["per_month"]
    section = [
        "",
        "## Computed fill (compute.py)",
        "",
        f"- Run: {log['date']} UTC on " + ", ".join(f"`raw/{n}` (`{h[:12]}…`)" for n, h in log["era5_files"].items())
        + " and " + ", ".join(f"`{n}` (`{h[:12]}…`)" for n, h in log["station_files"].items()),
        f"- ERA5 at the station: bilinear between {log['interpolation']['corners'][0]} and "
        f"{log['interpolation']['corners'][1]}, weights {[round(w, 3) for w in log['interpolation']['weights']]}; "
        f"nearest point {log['interpolation']['nearest']}, land fraction {log['interpolation'].get('land_fraction_nearest', float('nan')):.2f}",
        f"- Clean months ({FIRST_YEAR}-{LAST_YEAR}, >= {CLEAN_PCT:.0f}% of reports): n = {c['n']}, r = {c['r']:.3f}, "
        f"station minus ERA5 = {c['mean_offset']:+.2f} degC on average, RMSE {c['rmse_raw']:.2f} raw and "
        f"{c['rmse_after_monthly_offset']:.2f} after the per-month offset (nearest point instead of bilinear: "
        f"r = {log['clean_months_nearest_point']['r']:.3f}, RMSE after offset {log['clean_months_nearest_point']['rmse_after_monthly_offset']:.2f})",
        "- Offset per calendar month (station minus ERA5, degC; n): "
        + ", ".join(f"{m:02d}: {pm[str(m)]['offset'] if str(m) in pm else pm[m]['offset']:+.2f} ({pm[str(m)]['n'] if str(m) in pm else pm[m]['n']})"
                    for m in range(1, 13)),
        "- Fills (station value at its percentage -> ERA5 + offset): "
        + "; ".join(f"{ym}: {v['station_value']} at {v['pct']:.0f}% -> {v['fill']:+.1f}" for ym, v in f.items()),
        "- Other 2020-" + str(LAST_YEAR) + " months below the rule, not filled: " + (", ".join(log["weak_months_not_filled"]) or "none"),
        "- Output: orcadas_filled_monthly.csv, orcadas_filled_flag_monthly.csv, era5_t2m_orcadas_monthly.csv",
    ]
    text = PROVENANCE.read_text(encoding="utf-8") if PROVENANCE.exists() else \
        "# Provenance: ERA5 2 m temperature around Orcadas (local/orcadas_fill)\n"
    marker = "\n## Computed fill (compute.py)"
    if marker in text:
        text = text[:text.index(marker)]
    PROVENANCE.write_text(text.rstrip("\n") + "\n" + "\n".join(section) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="recompute in memory and compare with the files; write nothing")
    args = ap.parse_args()
    out, info = compute()
    c = info["clean_months"]
    print(f"ERA5 at the station: bilinear, weights {[round(w, 3) for w in info['interpolation']['weights']]}, "
          f"land fraction at the nearest point {info['interpolation'].get('land_fraction_nearest', float('nan')):.2f}")
    print(f"clean months {FIRST_YEAR}-{LAST_YEAR}: n = {c['n']}, r = {c['r']:.3f}, station minus ERA5 {c['mean_offset']:+.2f} degC, "
          f"RMSE {c['rmse_raw']:.2f} raw, {c['rmse_after_monthly_offset']:.2f} after the per-month offset "
          f"(nearest point: r = {info['clean_months_nearest_point']['r']:.3f}, "
          f"RMSE {info['clean_months_nearest_point']['rmse_after_monthly_offset']:.2f})")
    print("  offset per calendar month: " + ", ".join(f"{m:02d} {c['per_month'][m]['offset']:+.2f}" for m in range(1, 13)))
    for ym, v in info["fills"].items():
        print(f"  fill {ym}: station {v['station_value']} at {v['pct']:.0f}% -> ERA5 {v['era5_c']:+.2f} + offset {v['offset']:+.2f} = {v['fill']:+.1f} degC")
    if info["weak_months_not_filled"]:
        print("  other 2020+ months below the rule, not filled: " + ", ".join(info["weak_months_not_filled"]))

    if args.check:
        for name, frame in out.items():
            f = HERE / f"{name}_monthly.csv"
            if not f.exists():
                print(f"{f.name}: MISSING")
                continue
            old = pd.read_csv(f)
            same = old.shape == frame.shape and np.allclose(old["value"].astype(float), frame["value"].astype(float), equal_nan=True) \
                and (old[["year", "month"]].values == frame[["year", "month"]].values).all()
            print(f"{f.name}: {'unchanged' if same else 'DIFFERS'}")
        return 0

    for name, frame in out.items():
        frame.to_csv(HERE / f"{name}_monthly.csv", index=False)
    # json keys must be strings
    info["clean_months"]["per_month"] = {str(k): v for k, v in c["per_month"].items()}
    info["clean_months_nearest_point"]["per_month"] = {str(k): v for k, v in info["clean_months_nearest_point"]["per_month"].items()}
    log = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), **info}
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log)
    print(f"wrote 3 csv files, {LOG_FILE.name}, and the compute section of {PROVENANCE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
