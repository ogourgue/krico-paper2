#!/usr/bin/env python3
"""Daily sea-ice area and extent in the two Antarctic Dipole sectors, from
the NOAA/NSIDC G02202 v6 CDR as stacked by month for KRICO.

    python compute.py --nsidc-dir $KRICO_NSIDC            (on ECMWF)
    python compute.py --nsidc-dir $KRICO_NSIDC --no-hash  (skip the sha256 of the inputs)

Reads every nsidc_ice_YYYY_MM.nc in --nsidc-dir plus
ancillary/G02202-ancillary-pss25-v06r00.nc, and writes

    raw/daily_sectors.csv   one row per day: sea-ice area and extent
                            (1e6 km2) in each sector, and the number of
                            valid ocean cells seen; empty values on days
                            where fewer than half the sector's cells are
                            valid (a missing or partial CDR day)
    raw/sectors.json        the sector definitions and cell counts
    PROVENANCE.md           source product, file list, sha256 (unless
                            --no-hash), run date
    compute_log.json        the same, machine-readable

tidy.py then builds the monthly files and the anomalies on the laptop.
Sectors (methodology.md section 5): Bellingshausen-Amundsen 130W-60W
("pacific") and Weddell 60W-20W ("weddell"), all latitudes on the grid.
Cells are the CDR's ocean cells (surface_type 50) with a valid
concentration on the day; cell areas follow the scale factor of the
polar stereographic projection (true at 70S), not a flat 625 km2.
Extent counts cells at or above 15% concentration.

Requires numpy and xarray (with a NetCDF backend). Nothing is imported
from elsewhere in the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
DAILY_FILE = RAW / "daily_sectors.csv"
SECTORS_FILE = RAW / "sectors.json"
LOG_FILE = HERE / "compute_log.json"
PROVENANCE = HERE / "PROVENANCE.md"

ANCILLARY = "ancillary/G02202-ancillary-pss25-v06r00.nc"
_STACK = re.compile(r"nsidc_ice_(\d{4})_(\d{2})\.nc")

# name -> (west, east) in degrees east, west < east, both negative here
SECTORS = {"pacific": (-130.0, -60.0), "weddell": (-60.0, -20.0)}
OCEAN = 50          # surface_type flag for open ocean in the ancillary file
EXTENT_THRESHOLD = 0.15
MIN_VALID_FRACTION = 0.5

# NSIDC SH polar stereographic: Hughes 1980 ellipsoid, true scale at 70 S
A = 6378273.0
INV_F = 298.279411123064
LAT_TS = 70.0
CELL = 25000.0


def cell_area_km2(lat: np.ndarray) -> np.ndarray:
    """Area of a 25 km grid cell at latitude lat (degrees, negative in the
    south), from the ellipsoidal polar stereographic scale factor
    (Snyder 1987, eq. 21-32 to 21-35), relative to true scale at 70 S."""
    f = 1.0 / INV_F
    e = np.sqrt(2 * f - f * f)
    phi = np.deg2rad(np.abs(lat))

    def t_of(p):
        return np.tan(np.pi / 4 - p / 2) / ((1 - e * np.sin(p)) / (1 + e * np.sin(p))) ** (e / 2)

    def m_of(p):
        return np.cos(p) / np.sqrt(1 - (e * np.sin(p)) ** 2)

    phi_c = np.deg2rad(LAT_TS)
    k = (m_of(phi_c) * t_of(phi)) / (m_of(phi) * t_of(phi_c))
    with np.errstate(divide="ignore", invalid="ignore"):
        k = np.where(np.isfinite(k) & (k > 0), k, np.nan)
    return (CELL / k) ** 2 / 1e6


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_masks(anc: xr.Dataset) -> tuple[dict[str, np.ndarray], np.ndarray]:
    lon = anc["longitude"].values
    lat = anc["latitude"].values
    ocean = anc["surface_type"].values == OCEAN
    area = cell_area_km2(lat)
    masks = {}
    for name, (west, east) in SECTORS.items():
        masks[name] = ocean & (lon >= west) & (lon < east) & np.isfinite(area)
    return masks, area


def process_stack(path: Path, masks, area):
    """Return [(date, {sector: (sia, sie, nvalid)}), ...] for one month."""
    with xr.open_dataset(path) as ds:
        if ds["cdr_seaice_conc"].shape[1:] != area.shape:
            raise ValueError(f"{path.name}: grid {ds['cdr_seaice_conc'].shape[1:]} "
                             f"differs from the ancillary grid {area.shape}")
        conc = ds["cdr_seaice_conc"].values.astype("float64")   # scaled, NaN where fill
        dates = [str(t)[:10] for t in ds["time"].values]
    out = []
    for i, date in enumerate(dates):
        day = conc[i]
        valid = np.isfinite(day)
        rec = {}
        for name, mask in masks.items():
            sel = mask & valid
            n = int(sel.sum())
            if n < MIN_VALID_FRACTION * mask.sum():
                rec[name] = (None, None, n)
                continue
            sia = float(np.sum(day[sel] * area[sel])) / 1e6
            sie = float(np.sum(area[sel & (day >= EXTENT_THRESHOLD)])) / 1e6
            rec[name] = (sia, sie, n)
        out.append((date, rec))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nsidc-dir", default=os.environ.get("KRICO_NSIDC"),
                    help="folder with nsidc_ice_YYYY_MM.nc and ancillary/ (default $KRICO_NSIDC)")
    ap.add_argument("--no-hash", action="store_true", help="do not sha256 the input files")
    args = ap.parse_args()
    if not args.nsidc_dir:
        print("give --nsidc-dir or set $KRICO_NSIDC", file=sys.stderr)
        return 2
    nsidc = Path(args.nsidc_dir)
    stacks = sorted(p for p in nsidc.iterdir() if _STACK.fullmatch(p.name))
    anc_path = nsidc / ANCILLARY
    if not stacks or not anc_path.exists():
        print(f"no stacks or no ancillary file under {nsidc}", file=sys.stderr)
        return 2
    months = [tuple(map(int, _STACK.fullmatch(p.name).groups())) for p in stacks]
    y, m = months[0]
    for ym in months:
        if ym != (y, m):
            print(f"gap in the stacks: expected {y}-{m:02d}, found {ym[0]}-{ym[1]:02d}", file=sys.stderr)
            return 2
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    with xr.open_dataset(anc_path) as anc:
        masks, area = load_masks(anc)
    with xr.open_dataset(stacks[0]) as ds0:
        source_product = ds0.attrs.get("source_product", "")
        stack_title = ds0.attrs.get("title", "")
        created_by = ds0.attrs.get("created_by", "")

    RAW.mkdir(exist_ok=True)
    rows = []
    for i, path in enumerate(stacks, 1):
        for date, rec in process_stack(path, masks, area):
            rows.append((date, rec))
        if i % 24 == 0 or i == len(stacks):
            print(f"{i}/{len(stacks)} stacks, through {rows[-1][0]}")

    def fmt(v):
        return "" if v is None else f"{v:.5f}"

    with DAILY_FILE.open("w", newline="") as f:
        f.write("date,sia_pacific,sia_weddell,sie_pacific,sie_weddell,nvalid_pacific,nvalid_weddell\n")
        for date, rec in rows:
            p, w = rec["pacific"], rec["weddell"]
            f.write(f"{date},{fmt(p[0])},{fmt(w[0])},{fmt(p[1])},{fmt(w[1])},{p[2]},{w[2]}\n")

    sectors = {name: {"lon_west": SECTORS[name][0], "lon_east": SECTORS[name][1],
                      "ocean_cells": int(masks[name].sum()),
                      "ocean_area_1e6km2": round(float(area[masks[name]].sum()) / 1e6, 4)}
               for name in SECTORS}
    sectors["_notes"] = {"ocean_flag": OCEAN, "extent_threshold": EXTENT_THRESHOLD,
                         "min_valid_fraction": MIN_VALID_FRACTION,
                         "cell_area": "ellipsoidal polar stereographic scale factor, true at 70S",
                         "units": "1e6 km2"}
    SECTORS_FILE.write_text(json.dumps(sectors, indent=2) + "\n", encoding="utf-8")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    hashes = {}
    if not args.no_hash:
        print("hashing inputs")
        hashes[ANCILLARY] = sha256_file(anc_path)
        for p in stacks:
            hashes[p.name] = sha256_file(p)
    missing = [d for d, rec in rows if any(v[0] is None for v in rec.values())]
    log = {"run": now, "nsidc_dir": str(nsidc), "source_product": source_product,
           "stack_title": stack_title, "stacks_created_by": created_by,
           "first_day": rows[0][0], "last_day": rows[-1][0], "days": len(rows),
           "days_with_a_missing_sector": missing, "stacks": [p.name for p in stacks],
           "ancillary": ANCILLARY, "sha256": hashes, "sectors": sectors}
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Provenance: Antarctic Dipole sector series (indices/dipole)",
        "",
        "Written by `compute.py`; do not edit by hand. Machine-readable copy in",
        "`compute_log.json`.",
        "",
        f"- Source product: {source_product or '(attribute absent)'}",
        f"- Input: {len(stacks)} monthly stacks `nsidc_ice_YYYY_MM.nc` under `{nsidc}`",
        f"  ({stacks[0].name} to {stacks[-1].name}), produced by `{created_by}`; stack title: {stack_title}",
        f"- Ancillary grid file: `{ANCILLARY}`",
        f"- Computed: {now}",
        f"- Days: {len(rows)}, {rows[0][0]} to {rows[-1][0]}",
        f"- Days with a sector below {MIN_VALID_FRACTION:.0%} valid cells (value left empty): "
        f"{', '.join(missing) if missing else 'none'}",
        "- Sectors (ocean cells, ocean area in 1e6 km2):",
    ]
    for name in SECTORS:
        s = sectors[name]
        lines.append(f"  - {name}: {s['lon_west']} to {s['lon_east']} E, "
                     f"{s['ocean_cells']} cells, {s['ocean_area_1e6km2']}")
    lines += [f"- Output: `raw/daily_sectors.csv` (daily sea-ice area and extent per sector, 1e6 km2) "
              f"and `raw/sectors.json`",
              "- sha256 of inputs: " + ("in `compute_log.json`" if hashes else "not computed (--no-hash)"),
              "- Licence: G02202 is in the public domain (NOAA/NSIDC); cite Meier, W. N. et al., "
              "NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration, Version 6, "
              "doi:10.7265/b18j-z797, and Yuan, X. & Martinson, D. G. (2000), J. Climate 13, 1697-1717, "
              "for the Dipole."]
    PROVENANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote raw/{DAILY_FILE.name} ({len(rows)} days), raw/{SECTORS_FILE.name}, "
          f"{PROVENANCE.name}, {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
