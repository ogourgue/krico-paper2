#!/usr/bin/env python3
"""Retreat and advance day of the sea ice, per NSIDC cell and ice year, on
the cells that hold the release positions of the simulation. Runs where
the NSIDC stacks live (ECMWF) and leaves a small table in raw/ for tidy.py.

    python compute.py --nsidc-dir $KRICO_NSIDC            (on ECMWF)
    python compute.py --nsidc-dir $KRICO_NSIDC --no-hash  skip the sha256 of the stacks
    python compute.py --nsidc-dir $KRICO_NSIDC --check    recompute and compare with raw/; write nothing

Inputs
    $KRICO_NSIDC/nsidc_ice_YYYY_MM.nc     daily cdr_seaice_conc (ubyte 0-100,
                                          255 = fill), 332 x 316, EPSG:3412
    $KRICO_NSIDC/ancillary/G02202-ancillary-pss25-v06r00.nc
                                          latitude, longitude, surface_type
    ../subarea/raw/spawning_cells.csv     the release cells of the simulation
                                          (GLORYS12 cells with particle counts
                                          and subarea), read by path

Cells
    Each release cell centre is projected to the NSIDC grid with the
    polar stereographic projection of the stacks (south pole, true scale
    at 70S, Hughes 1980 ellipsoid), and its NSIDC cell found from the
    GeoTransform. The projection is checked against the ancillary
    latitude/longitude of the selected cells (max error reported, must be
    under 1 m), and every release position must fall within half a
    diagonal of its cell centre. Only ocean cells (surface_type 50) are
    kept; release positions landing on coast cells are reported with the
    weight they carry. The weight of an NSIDC cell in a subarea is the sum
    of n_release x inside_fraction of the release cells it contains, i.e.
    the expected number of particles a cohort starts in that cell.

Timing (per cell and ice year, ice year Y = 15 Feb Y to 14 Feb Y+1)
    Concentration above 15% counts as ice (strictly greater, as in the
    particle classification of KRICO paper 1); a run is 5 or more
    consecutive ice days. Missing days (fill) are interpolated linearly
    in time per cell and counted.
    advance_doy   first day of the first run starting on or after 1 April
                  of Y (the April cutoff of the classification, to avoid
                  lingering previous-winter ice); empty if there is none
    ice_on_apr1   1 if 1 April is itself inside a run (the advance is then
                  reported as 1 April although the ice was already there)
    retreat_doy   the day after the last day of the last run of the ice
                  year; empty if there is no run, or if the last run
                  reaches 14 February (ice still present at the end)
    Days are day-of-year of the calendar year in which the ice year starts,
    on a 365-day calendar (29 February dropped from the label only, so
    1 March is always 60), continuing past 365 into the following January
    and February (10 January of Y+1 is 375): the ice year does not wrap at
    New Year and neither does the label, so averages across cells and
    years stay meaningful.

Output
    raw/cells.csv         one row per (cell, subarea): row, col, subarea,
                          weight, lat, lon, n_release_cells
    raw/cell_timing.csv   one row per (cell, subarea, ice year): ice_year,
                          row, col, subarea, weight, advance_doy, ice_on_apr1,
                          retreat_doy, ice_days, days_interpolated
    PROVENANCE.md, compute_log.json

Requires numpy, pandas and netCDF4 (xarray is not needed). Nothing is
imported from elsewhere in the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LOG_FILE = HERE / "compute_log.json"
PROVENANCE = HERE / "PROVENANCE.md"
CELLS_FILE = HERE.parent / "subarea" / "raw" / "spawning_cells.csv"
ANCILLARY = "ancillary/G02202-ancillary-pss25-v06r00.nc"
STACK_RE = re.compile(r"nsidc_ice_(\d{4})_(\d{2})\.nc$")
VAR = "cdr_seaice_conc"
OCEAN = 50

# EPSG:3412 as written in the stacks' crs variable
A, INV_F = 6378273.0, 298.279411123064
LAT_TS = -70.0
X0, DX, Y0, DY = -3950000.0, 25000.0, 4350000.0, -25000.0     # GeoTransform
NROW, NCOL = 332, 316

RECRUITING = ("88.3", "48.1", "48.2", "48.4")
THRESHOLD = 15            # percent; ice when strictly greater
RUN = 5                   # consecutive days
ICE_YEAR_START = (2, 15)  # 15 February
ADVANCE_FROM = (4, 1)     # 1 April
EPOCH = date(1970, 1, 1)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------ projection

def to_xy(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Forward polar stereographic, south pole, ellipsoid, true scale at
    LAT_TS (Snyder 1987, eqs 21-33 to 21-35, with the south-polar sign
    rule): x = rho sin(lon), y = rho cos(lon)."""
    e = np.sqrt(2 / INV_F - 1 / INV_F ** 2)
    phi = np.radians(-np.asarray(lat, dtype="float64"))      # south -> positive
    lam = np.radians(np.asarray(lon, dtype="float64"))
    phic = np.radians(-LAT_TS)
    t = np.tan(np.pi / 4 - phi / 2) / ((1 - e * np.sin(phi)) / (1 + e * np.sin(phi))) ** (e / 2)
    tc = np.tan(np.pi / 4 - phic / 2) / ((1 - e * np.sin(phic)) / (1 + e * np.sin(phic))) ** (e / 2)
    mc = np.cos(phic) / np.sqrt(1 - e ** 2 * np.sin(phic) ** 2)
    rho = A * mc * t / tc
    return rho * np.sin(lam), rho * np.cos(lam)


def to_rowcol(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    col = np.floor((x - X0) / DX).astype(int)
    row = np.floor((y - Y0) / DY).astype(int)
    return row, col


# ------------------------------------------------------------ cells

def select_cells(nsidc: Path) -> tuple[pd.DataFrame, dict]:
    import netCDF4
    rel = pd.read_csv(CELLS_FILE, dtype={"subarea": str})
    x, y = to_xy(rel["lon"].values, rel["lat"].values)
    row, col = to_rowcol(x, y)
    with netCDF4.Dataset(nsidc / ANCILLARY) as ds:
        ds.set_auto_maskandscale(False)
        lat = np.asarray(ds["latitude"][:], dtype="float64")
        lon = np.asarray(ds["longitude"][:], dtype="float64")
        surface = np.asarray(ds["surface_type"][:])
        gx = np.asarray(ds["x"][:], dtype="float64")
        gy = np.asarray(ds["y"][:], dtype="float64")
    if lat.shape != (NROW, NCOL):
        raise SystemExit(f"ancillary grid is {lat.shape}, expected {(NROW, NCOL)}")
    inside = (row >= 0) & (row < NROW) & (col >= 0) & (col < NCOL)
    # The southern grid is a square that reaches 39S only at its corners and
    # about 51-53S along the 0 and 180 meridians; the northern end of the
    # 48.6N band lies beyond it. No ice reaches those cells; they are dropped
    # and reported, and the run stops only if a recruiting subarea loses any.
    off = rel[~inside]
    off_grid = {"release_cells": int(len(off)),
                "weight": float((off["n_release"] * off["inside_fraction"]).sum()),
                "per_subarea": {str(a): int((off.subarea == a).sum()) for a in sorted(off.subarea.unique())},
                "northernmost_lat": float(off["lat"].max()) if len(off) else None}
    if any(a in RECRUITING for a in off_grid["per_subarea"]):
        raise SystemExit(f"release cells of a recruiting subarea project outside the NSIDC grid: {off_grid['per_subarea']}")
    rel = rel[inside].reset_index(drop=True)
    row, col, x, y = row[inside], col[inside], x[inside], y[inside]
    # projection check: the ancillary centres of the selected cells must project onto the grid centres
    ax, ay = to_xy(lon[row, col], lat[row, col])
    proj_err = float(np.max(np.hypot(ax - gx[col], ay - gy[row])))
    # placement check: a release position must sit within half a diagonal of its cell centre
    place_err = float(np.max(np.hypot(x - gx[col], y - gy[row])))
    if proj_err > 1.0 or place_err > DX * np.sqrt(2) / 2 + 1.0:
        raise SystemExit(f"grid placement failed: projection error {proj_err:.2f} m, "
                         f"placement error {place_err:.0f} m")
    rel = rel.assign(row=row, col=col, weight=rel["n_release"] * rel["inside_fraction"],
                     ocean=surface[row, col] == OCEAN)
    dropped = rel[~rel.ocean]
    cells = (rel[rel.ocean].groupby(["row", "col", "subarea"], as_index=False)
             .agg(weight=("weight", "sum"), n_release_cells=("weight", "size")))
    cells["lat"] = np.round(lat[cells.row, cells.col], 4)
    cells["lon"] = np.round(lon[cells.row, cells.col], 4)
    cells["weight"] = np.round(cells["weight"], 3)
    info = {"release_cells": int(len(rel)) + off_grid["release_cells"], "off_grid": off_grid,
            "projection_error_m": proj_err, "placement_error_m": place_err,
            "nsidc_cells": int(len(cells)), "per_subarea": {s: int((cells.subarea == s).sum()) for s in sorted(cells.subarea.unique())},
            "dropped_non_ocean": {"release_cells": int(len(dropped)), "weight": float(dropped.weight.sum()),
                                  "per_subarea": {s: float(dropped.loc[dropped.subarea == s, "weight"].sum())
                                                  for s in sorted(dropped.subarea.unique())}},
            "weight_total": float(cells.weight.sum())}
    return cells, info


# ------------------------------------------------------------ daily series

def stacks(nsidc: Path) -> list[tuple[int, int, Path]]:
    out = []
    for p in sorted(nsidc.glob("nsidc_ice_*.nc")):
        m = STACK_RE.search(p.name)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), p))
    return out


def read_series(nsidc: Path, rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Concentration (percent, NaN where fill) for the selected cells on every
    day of the archive, in archive order; and the days as ordinal integers."""
    import netCDF4
    days, blocks = [], []
    for year, month, p in stacks(nsidc):
        with netCDF4.Dataset(p) as ds:
            ds.set_auto_maskandscale(False)
            t = np.asarray(ds["time"][:], dtype="int64")
            v = ds[VAR]
            if v.shape[1:] != (NROW, NCOL):
                raise SystemExit(f"{p.name}: grid {v.shape[1:]}")
            block = np.asarray(v[:])[:, rows, cols].astype("float32")   # (ndays, ncells)
        block[block == 255] = np.nan
        days.append(t)
        blocks.append(block)
    days = np.concatenate(days)
    conc = np.concatenate(blocks, axis=0)
    if not np.all(np.diff(days) == 1):
        gaps = np.nonzero(np.diff(days) != 1)[0]
        raise SystemExit(f"the stacks are not consecutive days; break after archive day index {gaps.tolist()}")
    return conc, days


def interpolate_gaps(conc: np.ndarray) -> np.ndarray:
    """Linear interpolation in time of NaN days, per cell; edges held."""
    out = conc.copy()
    n = conc.shape[0]
    idx = np.arange(n)
    for k in range(conc.shape[1]):
        col = out[:, k]
        bad = np.isnan(col)
        if bad.any() and not bad.all():
            col[bad] = np.interp(idx[bad], idx[~bad], col[~bad])
    return out


def runs(ice: np.ndarray) -> np.ndarray:
    """True on every day that belongs to a run of >= RUN consecutive ice days
    (ice is a boolean 1-D array)."""
    out = np.zeros(ice.size, dtype=bool)
    edges = np.diff(np.concatenate(([0], ice.astype(np.int8), [0])))
    for s, e in zip(np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]):
        if e - s >= RUN:
            out[s:e] = True
    return out


def doy365(d: date, ice_year: int) -> int:
    """Day of year on a 365-day calendar, counted from 1 January of ice_year
    and continuing past 365 for dates in the following year."""
    doy = d.timetuple().tm_yday
    if d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0) and d.month > 2:
        doy -= 1
    return doy + 365 * (d.year - ice_year)


def timing(conc: np.ndarray, days: np.ndarray, cells: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    first, last = EPOCH + timedelta(days=int(days[0])), EPOCH + timedelta(days=int(days[-1]))
    filled = interpolate_gaps(conc)
    ice = filled > THRESHOLD
    rows_out, years_info = [], {}
    y = first.year if first <= date(first.year, *ICE_YEAR_START) else first.year + 1
    while date(y, *ICE_YEAR_START) <= last:
        start = date(y, *ICE_YEAR_START)
        end = date(y + 1, *ICE_YEAR_START) - timedelta(days=1)
        if end > last:
            years_info[y] = {"complete": False, "ends": str(last)}
            break
        i0 = int((start - EPOCH).days - days[0]); i1 = int((end - EPOCH).days - days[0]) + 1
        ia = int((date(y, *ADVANCE_FROM) - EPOCH).days - days[0])
        years_info[y] = {"complete": True, "days": i1 - i0}
        for k in range(conc.shape[1]):
            r = runs(ice[i0:i1, k])
            n_interp = int(np.isnan(conc[i0:i1, k]).sum())
            adv = np.nan; apr1 = 0
            cand = np.nonzero(r[ia - i0:])[0]
            if cand.size:
                adv = doy365(start + timedelta(days=int(ia - i0 + cand[0])), y)
                apr1 = int(cand[0] == 0)
            ret = np.nan
            if r.any():
                last_ice = int(np.nonzero(r)[0][-1])
                if last_ice < i1 - i0 - 1:
                    ret = doy365(start + timedelta(days=last_ice + 1), y)
            rows_out.append((y, int(cells.row.iloc[k]), int(cells.col.iloc[k]), cells.subarea.iloc[k],
                             float(cells.weight.iloc[k]), adv, apr1, ret, int(ice[i0:i1, k].sum()), n_interp))
        y += 1
    table = pd.DataFrame(rows_out, columns=["ice_year", "row", "col", "subarea", "weight", "advance_doy",
                                            "ice_on_apr1", "retreat_doy", "ice_days", "days_interpolated"])
    return table, {"archive": [str(first), str(last)], "ice_years": years_info}


# ------------------------------------------------------------ main

def wquantiles(values: pd.Series, weights: pd.Series, qs=(0.1, 0.5, 0.9)) -> list:
    ok = values.notna()
    if not ok.any():
        return [None, None, None]
    v, w = values[ok].values, weights[ok].values
    order = np.argsort(v)
    cum = np.cumsum(w[order]) / w[order].sum()
    return [float(v[order][np.searchsorted(cum, q)]) for q in qs]


def summarise(table: pd.DataFrame) -> dict:
    out = {}
    for s, g in table.groupby("subarea"):
        w = g.weight
        out[s] = {"ice_years": int(g.ice_year.nunique()),
                  "advance_q10_50_90": wquantiles(g.advance_doy, w),
                  "retreat_q10_50_90": wquantiles(g.retreat_doy, w),
                  "weight_with_advance": float((w * g.advance_doy.notna()).sum() / w.sum()),
                  "weight_with_retreat": float((w * g.retreat_doy.notna()).sum() / w.sum()),
                  "mean_advance_doy": float(np.average(g.advance_doy.dropna(), weights=w[g.advance_doy.notna()])) if g.advance_doy.notna().any() else None,
                  "mean_retreat_doy": float(np.average(g.retreat_doy.dropna(), weights=w[g.retreat_doy.notna()])) if g.retreat_doy.notna().any() else None,
                  "days_interpolated": int(g.days_interpolated.sum())}
    return out


def write_provenance(log: dict) -> None:
    c, t, s = log["cells"], log["timing"], log["summary"]
    lines = [
        "# Provenance: sea-ice retreat and advance day on the release cells (local/ice_timing)",
        "",
        "Written by `compute.py`; do not edit by hand. Machine-readable copy in",
        "`compute_log.json`.",
        "",
        "## Source",
        "",
        "- NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration,",
        "  G02202 v6 (doi:10.7265/b18j-z797), southern hemisphere, daily, 25 km polar",
        "  stereographic grid (EPSG:3412), as stacked by month for KRICO",
        f"- Archive used: {t['archive'][0]} to {t['archive'][1]}, {log['n_stacks']} monthly stacks"
        + (f"; sha256 of every stack and of the ancillary file in `compute_log.json`" if log.get("sha256") else "; stacks not hashed (--no-hash)"),
        f"- Release cells: `../subarea/raw/spawning_cells.csv` (sha256 `{log['cells_sha256'][:12]}…`)",
        "- Licence: G02202 is in the public domain (NOAA/NSIDC); cite Meier, W. N. et al.,",
        "  NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration,",
        "  Version 6, and the DOI",
        "",
        "## Computed table (compute.py)",
        "",
        f"- Run: {log['date']} UTC",
        f"- Cells: {c['release_cells']} release cells placed on {c['nsidc_cells']} (cell, subarea) pairs "
        f"({', '.join(f'{k}: {v}' for k, v in c['per_subarea'].items())}); projection check {c['projection_error_m']:.3f} m, "
        f"placement check {c['placement_error_m']:.0f} m; release cells beyond the grid's northern edge dropped: "
        f"{c['off_grid']['release_cells']} ({', '.join(f'{k}: {v}' for k, v in c['off_grid']['per_subarea'].items()) or 'none'}, "
        f"{c['off_grid']['weight']:.0f} particles, northernmost {c['off_grid']['northernmost_lat']}); "
        f"release cells on non-ocean NSIDC cells dropped: "
        f"{c['dropped_non_ocean']['release_cells']} carrying {c['dropped_non_ocean']['weight']:.0f} particles "
        f"({', '.join(f'{k}: {v:.0f}' for k, v in c['dropped_non_ocean']['per_subarea'].items()) or 'none'}); "
        f"total weight kept {c['weight_total']:.0f}",
        "- Ice years: " + ", ".join(f"{y}" + ("" if v["complete"] else f" (incomplete, archive ends {v['ends']})")
                                   for y, v in t["ice_years"].items()),
        f"- Rule: ice when concentration > {THRESHOLD}%, runs of >= {RUN} days; advance from 1 April; "
        "retreat = day after the last run; day-of-year on a 365-day calendar counted from 1 January of the ice year, "
        "past 365 for January-February of the next year",
        "- Per subarea (weight share with an advance, with a retreat; weighted mean advance and retreat day; interpolated days): "
        + "; ".join(f"{k}: {v['weight_with_advance']:.2f}, {v['weight_with_retreat']:.2f}, "
                    f"{v['mean_advance_doy'] if v['mean_advance_doy'] is None else round(v['mean_advance_doy'])}, "
                    f"{v['mean_retreat_doy'] if v['mean_retreat_doy'] is None else round(v['mean_retreat_doy'])}, "
                    f"{v['days_interpolated']}" for k, v in s.items()),
        "- Output: raw/cells.csv, raw/cell_timing.csv",
        "",
    ]
    PROVENANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nsidc-dir", default=os.environ.get("KRICO_NSIDC"),
                    help="folder with nsidc_ice_YYYY_MM.nc and ancillary/ (default $KRICO_NSIDC)")
    ap.add_argument("--no-hash", action="store_true", help="skip the sha256 of the stacks")
    ap.add_argument("--check", action="store_true", help="recompute and compare with raw/; write nothing")
    args = ap.parse_args()
    if not args.nsidc_dir:
        print("give --nsidc-dir or set $KRICO_NSIDC", file=sys.stderr)
        return 2
    nsidc = Path(args.nsidc_dir)
    if not (nsidc / ANCILLARY).exists() or not stacks(nsidc):
        print(f"no stacks or no ancillary file under {nsidc}", file=sys.stderr)
        return 2
    if not CELLS_FILE.exists():
        print(f"{CELLS_FILE} not found: pull the repository, it is committed", file=sys.stderr)
        return 2

    cells, cinfo = select_cells(nsidc)
    print(f"{cinfo['release_cells']} release cells -> {cinfo['nsidc_cells']} NSIDC (cell, subarea) pairs "
          f"{cinfo['per_subarea']}; off the NSIDC grid: {cinfo['off_grid']['release_cells']} "
          f"{cinfo['off_grid']['per_subarea']} (northernmost {cinfo['off_grid']['northernmost_lat']}); "
          f"projection check {cinfo['projection_error_m']:.3f} m; "
          f"dropped on non-ocean cells: {cinfo['dropped_non_ocean']['release_cells']} "
          f"({cinfo['dropped_non_ocean']['weight']:.0f} particles)")
    print(f"reading {len(stacks(nsidc))} stacks ...")
    conc, days = read_series(nsidc, cells.row.values, cells.col.values)
    table, tinfo = timing(conc, days, cells)
    summary = summarise(table)
    for y, v in tinfo["ice_years"].items():
        if not v["complete"]:
            print(f"  ice year {y} incomplete (archive ends {v['ends']}), not computed")
    fmt = lambda x: "none" if x is None else f"{x:.0f}"
    q = lambda v: "none" if v[0] is None else "/".join(f"{x:.0f}" for x in v)
    for s, v in summary.items():
        print(f"  {s}: {v['ice_years']} ice years; advance on {100 * v['weight_with_advance']:.0f}% of the weight, "
              f"mean day {fmt(v['mean_advance_doy'])} (10/50/90% {q(v['advance_q10_50_90'])}); "
              f"retreat on {100 * v['weight_with_retreat']:.0f}%, mean day {fmt(v['mean_retreat_doy'])} "
              f"(10/50/90% {q(v['retreat_q10_50_90'])}); {v['days_interpolated']} interpolated cell-days")

    if args.check:
        for name, frame in (("cells.csv", cells), ("cell_timing.csv", table)):
            f = RAW / name
            if not f.exists():
                print(f"raw/{name}: MISSING"); continue
            old = pd.read_csv(f, dtype={"subarea": str})
            same = old.shape == frame.shape and all(
                np.allclose(old[c].astype(float), frame[c].astype(float), equal_nan=True) if frame[c].dtype != object
                else (old[c].values == frame[c].values).all() for c in frame.columns)
            print(f"raw/{name}: {'unchanged' if same else 'DIFFERS'}")
        return 0

    RAW.mkdir(exist_ok=True)
    cells.to_csv(RAW / "cells.csv", index=False)
    table.to_csv(RAW / "cell_timing.csv", index=False, float_format="%.3f")
    log = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "nsidc_dir": str(nsidc),
           "n_stacks": len(stacks(nsidc)), "cells_sha256": sha256_file(CELLS_FILE), "cells": cinfo,
           "timing": tinfo, "summary": summary,
           "rule": {"threshold_percent": THRESHOLD, "run_days": RUN, "ice_year_start": "02-15", "advance_from": "04-01"}}
    if not args.no_hash:
        print("hashing the stacks ...")
        log["sha256"] = {p.name: sha256_file(p) for _, _, p in stacks(nsidc)}
        log["sha256"][ANCILLARY] = sha256_file(nsidc / ANCILLARY)
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log)
    print(f"wrote raw/cells.csv ({len(cells)} rows), raw/cell_timing.csv ({len(table)} rows), "
          f"{LOG_FILE.name} and {PROVENANCE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
