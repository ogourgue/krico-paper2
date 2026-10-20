#!/usr/bin/env python3
"""Reduce the ERA5 sector fields in raw/ to the tier-2 series of this
folder, one monthly CSV (year,month,value) per variable and region.

    python compute.py            build raw/spawning_cells.csv if absent,
                                 then write the monthly files, compute_log.json
                                 and the compute section of PROVENANCE.md
    python compute.py --cells    rebuild raw/spawning_cells.csv from the
                                 GLORYS12 bathymetry even if it exists
    python compute.py --check    recompute everything in memory and compare
                                 with the files on disk; write nothing

Spawning cells (raw/spawning_cells.csv, committed)
    The release positions of the simulation are deterministic apart from a
    jitter: a GLORYS12 cell is a release cell when its bathymetry hdept is
    between 1000 and 2000 m and its centre lies in one of the CCAMLR areas
    48.1-48.6 and 88.3; it releases max(1, round(cell area in km2))
    particles (density 1 per km2), uniformly jittered within the cell, and
    particles jittered outside 76S-41S, 114W-39E are discarded. This script
    rebuilds that cell set from $KRICO_GLORYS12/glorys12_bathymetry.nc and
    the CCAMLR shapefile in ../../ccamlr-data/, labels each cell with its
    subarea, and records the particle count and the fraction of the jitter
    box inside the filter window; weight = n_release x inside_fraction is
    the expected number of particles the cell contributes to every cohort.
    The table is committed so that the series can be recomputed without
    the 76 MB bathymetry file.

Series (files in this folder)
    v10_band_<sub>_monthly.csv, t2m_band_<sub>_monthly.csv
        sub in 883, 481, 482, 484: northward 10 m wind and 2 m temperature
        over the spawning band of the subarea, the mean over the band's
        release cells weighted by their particle weight; each release cell
        takes the value of the nearest ERA5 ocean grid point (ocean = sea
        surface temperature defined in every month).
    u10_south_orkney_monthly.csv, v10_south_orkney_monthly.csv
        eastward and northward 10 m wind over the South Orkney Plateau box
        of Young et al. (2024), 60-62.5S, 41-48W (local recruitment and
        retention).
    u10_nw_weddell_monthly.csv, v10_nw_weddell_monthly.csv
        the same over the northwest Weddell Sea box of Young et al. (2024),
        59.5-65S, 39-55W (regional recruitment from upstream).
    curl_weddell_gyre_monthly.csv
        wind-stress curl d(mntss)/dx - d(metss)/dy on the sphere, central
        differences on the 1 degree grid, averaged over the Weddell Gyre
        box of Auckland et al. (2024), 62-70S, 60W-0; negative = cyclonic
        (clockwise) in the Southern Hemisphere, the sense that spins the
        gyre up (Meijers et al. 2016).
    sst_north_edge_monthly.csv
        sea surface temperature in 55-60S, 20-35W, the water in front of the
        advancing ice in this sector (regional form of the subpolar band of
        Kusahara and Tatebe 2025).
    Box means are weighted by cos(latitude). Values keep ERA5 units and
    signs (K, m s-1, N m-2, N m-3).

Inputs: raw/era5_sector_monthly*.nc from fetch.py; raw/spawning_cells.csv
(or the bathymetry file to rebuild it); the shapefile is read with a
minimal reader for the .shp/.dbf formats written here, so no geopandas.
numpy, pandas and xarray only; nothing imported from elsewhere in the
repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CELLS_FILE = RAW / "spawning_cells.csv"
LOG_FILE = HERE / "compute_log.json"
PROVENANCE = HERE / "PROVENANCE.md"
FIELD_GLOB = "era5_sector_monthly*.nc"
SHAPEFILE = HERE.parent.parent / "ccamlr-data" / "CCAMLR_ASD_EPSG4326"   # .shp/.dbf
BATHY_ENV = "KRICO_GLORYS12"
BATHY_NAME = "glorys12_bathymetry.nc"

# Release strategy of the simulation (Runs/KRICO_GLORYS12/run_ter.py).
RELEASE_AREAS = ["48.1", "48.2", "48.3", "48.4", "48.5", "48.6", "88.3"]
SHAPE_FIELD = "GAR_Long_L"
DEPTH_MIN, DEPTH_MAX = 1000.0, 2000.0
PARTICLE_DENSITY = 1.0                                   # per km2
KM_PER_DEG = 111.32
FILTER_LAT, FILTER_LON = (-76.0, -41.0), (-114.0, 39.0)  # jittered particles outside are dropped

RECRUITING = {"88.3": "883", "48.1": "481", "48.2": "482", "48.4": "484"}

# Boxes: (south, north, west, east), edges inclusive on the 1 degree grid.
BOXES = {
    "south_orkney": (-62.5, -60.0, -48.0, -41.0),   # Young et al. 2024, plateau
    "nw_weddell": (-65.0, -59.5, -55.0, -39.0),     # Young et al. 2024, northwest Weddell
    "weddell_gyre": (-70.0, -62.0, -60.0, 0.0),     # Auckland et al. 2024, curl integration
    "north_edge": (-60.0, -55.0, -35.0, -20.0),     # after Kusahara and Tatebe 2025
}
ALIASES = {"avg_iews": "metss", "avg_inss": "mntss"}
TIME_DIMS = ("valid_time", "time", "date")
FREEZING_K = 271.5                                       # ERA5 sst floor under sea ice is ~271.46 K


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------ shapefile

def read_shapefile(stem: Path) -> list[dict]:
    """Polygons of a .shp with their .dbf attributes: [{'attrs': {...},
    'rings': [(N, 2) arrays of lon, lat], 'bbox': (xmin, ymin, xmax, ymax)}]."""
    shp, dbf = stem.with_suffix(".shp"), stem.with_suffix(".dbf")
    shapes = []
    with shp.open("rb") as f:
        head = f.read(100)
        if struct.unpack(">i", head[:4])[0] != 9994:
            raise ValueError(f"{shp.name} is not a shapefile")
        while True:
            rec = f.read(8)
            if len(rec) < 8:
                break
            (length,) = struct.unpack(">i", rec[4:8])
            body = f.read(length * 2)
            (shape_type,) = struct.unpack("<i", body[:4])
            if shape_type == 0:                          # null shape
                shapes.append({"rings": [], "bbox": None})
                continue
            if shape_type not in (5, 15, 25):            # polygon, polygonZ, polygonM
                raise ValueError(f"{shp.name}: unsupported shape type {shape_type}")
            bbox = struct.unpack("<4d", body[4:36])
            n_parts, n_points = struct.unpack("<2i", body[36:44])
            parts = struct.unpack(f"<{n_parts}i", body[44:44 + 4 * n_parts])
            off = 44 + 4 * n_parts
            pts = np.frombuffer(body[off:off + 16 * n_points], dtype="<f8").reshape(n_points, 2)
            bounds = list(parts) + [n_points]
            rings = [pts[bounds[k]:bounds[k + 1]].copy() for k in range(n_parts)]
            shapes.append({"rings": rings, "bbox": bbox})
    with dbf.open("rb") as f:
        head = f.read(32)
        n_rec, head_len, rec_len = struct.unpack("<xxxxIHH", head[:12])
        fields = []
        while True:
            desc = f.read(32)
            if desc[0] == 0x0D:
                break
            name = desc[:11].split(b"\x00")[0].decode("ascii")
            fields.append((name, desc[11:12].decode("ascii"), desc[16]))
        f.seek(head_len)
        for k in range(n_rec):
            rec = f.read(rec_len)
            if k >= len(shapes):
                break
            attrs, pos = {}, 1                           # byte 0 is the deletion flag
            for name, ftype, size in fields:
                raw = rec[pos:pos + size]
                pos += size
                txt = raw.decode("latin-1").strip()
                attrs[name] = txt
            shapes[k]["attrs"] = attrs
    return shapes


def points_in_shape(shape: dict, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Even-odd ray casting over all rings (outer rings and holes alike)."""
    inside = np.zeros(lon.shape, dtype=bool)
    if shape["bbox"] is None:
        return inside
    xmin, ymin, xmax, ymax = shape["bbox"]
    cand = np.nonzero((lon >= xmin) & (lon <= xmax) & (lat >= ymin) & (lat <= ymax))[0]
    if cand.size == 0:
        return inside
    x, y = lon[cand], lat[cand]
    hit = np.zeros(cand.size, dtype=bool)
    for ring in shape["rings"]:
        xr_, yr_ = ring[:, 0], ring[:, 1]
        x0, y0 = xr_[:-1], yr_[:-1]
        x1, y1 = xr_[1:], yr_[1:]
        for a in range(x0.size):
            ya, yb = y0[a], y1[a]
            if ya == yb:
                continue
            crosses = (y >= min(ya, yb)) & (y < max(ya, yb))
            if not crosses.any():
                continue
            xa, xb = x0[a], x1[a]
            xi = xa + (y[crosses] - ya) * (xb - xa) / (yb - ya)
            sub = np.nonzero(crosses)[0]
            hit[sub[x[crosses] < xi]] ^= True
    inside[cand] = hit
    return inside


# ------------------------------------------------------------ spawning cells

def build_cells(bathy_file: Path) -> tuple[pd.DataFrame, dict]:
    import xarray as xr
    with xr.open_dataset(bathy_file) as ds:
        hdept = ds["hdept"].values
        if hdept.ndim == 3:
            hdept = hdept[0]
        nav_lon = ds["nav_lon"].values.astype("float64")
        nav_lat = ds["nav_lat"].values.astype("float64")
    ny, nx = hdept.shape
    # Cell size from the neighbouring centre, as run_ter.py does (forward
    # difference, backward on the last row/column).
    dlon = np.empty_like(nav_lon)
    dlon[:, :-1] = np.abs(nav_lon[:, 1:] - nav_lon[:, :-1])
    dlon[:, -1] = np.abs(nav_lon[:, -1] - nav_lon[:, -2])
    dlat = np.empty_like(nav_lat)
    dlat[:-1, :] = np.abs(nav_lat[1:, :] - nav_lat[:-1, :])
    dlat[-1, :] = np.abs(nav_lat[-1, :] - nav_lat[-2, :])
    area = dlon * KM_PER_DEG * np.cos(np.radians(nav_lat)) * dlat * KM_PER_DEG
    band = np.isfinite(hdept) & (hdept >= DEPTH_MIN) & (hdept <= DEPTH_MAX)
    jj, ii = np.nonzero(band)
    lon, lat = nav_lon[jj, ii], nav_lat[jj, ii]
    shapes = read_shapefile(SHAPEFILE)
    subarea = np.full(lon.size, "", dtype=object)
    overlap = 0
    for sh in shapes:
        label = sh.get("attrs", {}).get(SHAPE_FIELD, "")
        if label not in RELEASE_AREAS:
            continue
        inside = points_in_shape(sh, lon, lat)
        overlap += int(((subarea != "") & inside).sum())
        subarea[inside] = label
    keep = subarea != ""
    n = np.maximum(1, np.round(PARTICLE_DENSITY * area[jj, ii])).astype(int)
    # Expected fraction of a cell's jittered particles inside the filter window.
    def frac(c, d, lo, hi):
        a, b = c - 0.5 * d, c + 0.5 * d
        return np.clip((np.minimum(b, hi) - np.maximum(a, lo)) / d, 0.0, 1.0)
    inside_fraction = frac(lon, dlon[jj, ii], *FILTER_LON) * frac(lat, dlat[jj, ii], *FILTER_LAT)
    cells = pd.DataFrame({
        "j": jj[keep], "i": ii[keep],
        "lon": np.round(lon[keep], 5), "lat": np.round(lat[keep], 5),
        "depth_m": np.round(hdept[jj, ii][keep], 1),
        "area_km2": np.round(area[jj, ii][keep], 3),
        "n_release": n[keep],
        "inside_fraction": np.round(inside_fraction[keep], 4),
        "subarea": subarea[keep],
    })
    info = {
        "bathymetry_file": str(bathy_file), "bathymetry_sha256": sha256_file(bathy_file),
        "shapefile_sha256": sha256_file(SHAPEFILE.with_suffix(".shp")),
        "grid": [ny, nx], "band_cells_total": int(band.sum()), "cells_in_release_areas": int(keep.sum()),
        "cells_in_two_areas": overlap,
        "particles_per_day": int(cells["n_release"].sum()),
        "particles_per_day_after_filter": float((cells["n_release"] * cells["inside_fraction"]).sum()),
        "per_area": {a: {"cells": int((cells.subarea == a).sum()),
                         "particles": int(cells.loc[cells.subarea == a, "n_release"].sum())}
                     for a in RELEASE_AREAS},
    }
    return cells, info


# ------------------------------------------------------------ ERA5 fields

def open_fields(paths: list[Path]):
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
        ds = ds.rename({v: ALIASES[v] for v in ds.data_vars if v in ALIASES})
        parts.append(ds)
    ds = xr.merge(parts, compat="no_conflicts", join="outer").sortby("latitude").sortby("valid_time")
    for v in ("u10", "v10", "t2m", "sst", "metss", "mntss"):
        if v not in ds:
            raise KeyError(f"{v} missing from the ERA5 files; variables are {list(ds.data_vars)}")
    return ds


def curl(ds):
    """d(tau_y)/dx - d(tau_x)/dy on the sphere, central differences, N m-3.
    Land points carry ERA5's stress over land, so the derivative is defined
    everywhere; the ocean mask is applied at the averaging step."""
    lat = np.radians(ds["latitude"].values)
    dlat = np.gradient(np.radians(ds["latitude"].values))
    dlon = np.gradient(np.radians(ds["longitude"].values))
    r = 6_371_000.0
    tx, ty = ds["metss"].values, ds["mntss"].values           # (t, y, x)
    dty_dx = np.gradient(ty, axis=2) / (r * np.cos(lat)[None, :, None] * dlon[None, None, :])
    dtx_dy = np.gradient(tx, axis=1) / (r * dlat[None, :, None])
    return dty_dx - dtx_dy


def box_mean(values: np.ndarray, ds, ocean: np.ndarray, box: tuple) -> tuple[np.ndarray, dict]:
    south, north, west, east = box
    lat, lon = ds["latitude"].values, ds["longitude"].values
    sel = ocean & (lat[:, None] >= south) & (lat[:, None] <= north) & (lon[None, :] >= west) & (lon[None, :] <= east)
    w = np.cos(np.radians(lat))[:, None] * sel
    series = np.nansum(values * w[None], axis=(1, 2)) / w.sum()
    return series, {"points": int(sel.sum()), "box": list(box)}


def band_weights(cells: pd.DataFrame, ds, ocean: np.ndarray) -> dict:
    """Per recruiting subarea: a (lat, lon) weight map on the ERA5 grid,
    each release cell assigned to the nearest ocean grid point."""
    lat, lon = ds["latitude"].values, ds["longitude"].values
    oj, oi = np.nonzero(ocean)
    olat, olon = lat[oj], lon[oi]
    out = {}
    for label, key in RECRUITING.items():
        c = cells[cells.subarea == label]
        wgt = (c["n_release"] * c["inside_fraction"]).values
        clat, clon = c["lat"].values, c["lon"].values
        # distance in km, flat approximation at the cell latitude
        dx = (clon[:, None] - olon[None, :]) * KM_PER_DEG * np.cos(np.radians(clat))[:, None]
        dy = (clat[:, None] - olat[None, :]) * KM_PER_DEG
        d = np.hypot(dx, dy)
        k = d.argmin(axis=1)
        wmap = np.zeros(ocean.shape)
        np.add.at(wmap, (oj[k], oi[k]), wgt)
        # how many cells had a land point as plain nearest grid point
        nj = np.abs(lat[None, :] - clat[:, None]).argmin(axis=1)
        ni = np.abs(lon[None, :] - clon[:, None]).argmin(axis=1)
        redirected = int((~ocean[nj, ni]).sum())
        out[key] = {"weights": wmap, "cells": int(len(c)), "weight_total": float(wgt.sum()),
                    "grid_points": int((wmap > 0).sum()), "redirected_from_land": redirected,
                    "max_distance_km": float(d[np.arange(len(k)), k].max()) if len(k) else None}
    return out


def weighted_series(values: np.ndarray, wmap: np.ndarray) -> np.ndarray:
    return np.nansum(values * wmap[None], axis=(1, 2)) / wmap.sum()


def to_frame(series: np.ndarray, months: pd.DatetimeIndex, decimals: int) -> pd.DataFrame:
    return pd.DataFrame({"year": months.year, "month": months.month, "value": np.round(series, decimals)})


# ------------------------------------------------------------ main

def compute(cells: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict]:
    paths = sorted(RAW.glob(FIELD_GLOB))
    if not paths:
        raise SystemExit("no ERA5 file in raw/: run fetch.py first")
    ds = open_fields(paths)
    months = pd.DatetimeIndex(ds["valid_time"].values)
    ocean = np.isfinite(ds["sst"].values).all(axis=0)
    info = {"era5_files": {p.name: sha256_file(p) for p in paths}, "months": len(months),
            "first": f"{months[0]:%Y-%m}", "last": f"{months[-1]:%Y-%m}",
            "ocean_points": int(ocean.sum()), "bands": {}, "boxes": {}}
    out: dict[str, pd.DataFrame] = {}
    bands = band_weights(cells, ds, ocean)
    for key, b in bands.items():
        info["bands"][key] = {k: v for k, v in b.items() if k != "weights"}
        out[f"v10_band_{key}"] = to_frame(weighted_series(ds["v10"].values, b["weights"]), months, 3)
        out[f"t2m_band_{key}"] = to_frame(weighted_series(ds["t2m"].values, b["weights"]), months, 3)
    for key in ("south_orkney", "nw_weddell"):
        s, d = box_mean(ds["u10"].values, ds, ocean, BOXES[key])
        out[f"u10_{key}"] = to_frame(s, months, 3); info["boxes"][key] = d
        s, _ = box_mean(ds["v10"].values, ds, ocean, BOXES[key])
        out[f"v10_{key}"] = to_frame(s, months, 3)
    s, d = box_mean(curl(ds), ds, ocean, BOXES["weddell_gyre"])
    out["curl_weddell_gyre"] = to_frame(s * 1e7, months, 4)              # 1e-7 N m-3 units, see README
    info["boxes"]["weddell_gyre"] = d | {"mean_curl_1e-7_N_m-3": float(np.mean(s) * 1e7)}
    s, d = box_mean(ds["sst"].values, ds, ocean, BOXES["north_edge"])
    out["sst_north_edge"] = to_frame(s, months, 3)
    # ice intrusion into the SST box: fraction of its ocean points at the freezing floor, worst month
    south, north, west, east = BOXES["north_edge"]
    lat, lon = ds["latitude"].values, ds["longitude"].values
    sel = ocean & (lat[:, None] >= south) & (lat[:, None] <= north) & (lon[None, :] >= west) & (lon[None, :] <= east)
    frozen = (ds["sst"].values[:, sel] < FREEZING_K).mean(axis=1)
    k = int(frozen.argmax())
    window = np.isin(months.month, [3, 4, 5, 6])              # the months the design uses the box for
    kw = int(np.where(window, frozen, -1).argmax())
    info["boxes"]["north_edge"] = d | {"max_fraction_at_freezing": float(frozen[k]),
                                       "worst_month": f"{months[k]:%Y-%m}",
                                       "max_fraction_at_freezing_mar_jun": float(frozen[kw]),
                                       "worst_month_mar_jun": f"{months[kw]:%Y-%m}"}
    return out, info


def write_provenance(log: dict) -> None:
    c, r = log["cells"], log["reduction"]
    section = [
        "",
        "## Computed series (compute.py)",
        "",
        f"- Run: {log['date']} UTC",
        f"- Spawning cells: `raw/spawning_cells.csv`, {c['cells_in_release_areas']} GLORYS12 cells with "
        f"{DEPTH_MIN:.0f}-{DEPTH_MAX:.0f} m depth in areas {', '.join(RELEASE_AREAS)}, "
        f"{c['particles_per_day']} particles per release day ({c['particles_per_day_after_filter']:.0f} after the "
        f"domain filter); from `{Path(c['bathymetry_file']).name}` (sha256 `{c['bathymetry_sha256'][:12]}…`) and "
        f"`CCAMLR_ASD_EPSG4326.shp` (sha256 `{c['shapefile_sha256'][:12]}…`); per area "
        + ", ".join(f"{a}: {v['cells']} cells / {v['particles']} particles" for a, v in c["per_area"].items()),
        f"- ERA5 input: " + ", ".join(f"`raw/{n}` (`{h[:12]}…`)" for n, h in r["era5_files"].items())
        + f"; {r['months']} months {r['first']} to {r['last']}; {r['ocean_points']} ocean grid points",
        "- Bands (cells, total weight, ERA5 points used, cells whose nearest point was land, max distance km): "
        + "; ".join(f"{k}: {b['cells']}, {b['weight_total']:.0f}, {b['grid_points']}, {b['redirected_from_land']}, "
                    f"{b['max_distance_km']:.0f}" for k, b in r["bands"].items()),
        "- Boxes: " + "; ".join(f"{k}: {v['box']} ({v['points']} ocean points)" for k, v in r["boxes"].items()),
        f"- Weddell Gyre curl mean {r['boxes']['weddell_gyre']['mean_curl_1e-7_N_m-3']:+.2f} x 1e-7 N m-3 "
        "(negative = cyclonic in the Southern Hemisphere)",
        f"- SST box ice check: at most {100 * r['boxes']['north_edge']['max_fraction_at_freezing']:.0f}% of its points at the "
        f"freezing floor ({r['boxes']['north_edge']['worst_month']}); within Mar-Jun at most "
        f"{100 * r['boxes']['north_edge']['max_fraction_at_freezing_mar_jun']:.0f}% "
        f"({r['boxes']['north_edge']['worst_month_mar_jun']})",
        "- Output: " + ", ".join(f"{k}_monthly.csv" for k in log["outputs"]),
    ]
    text = PROVENANCE.read_text(encoding="utf-8") if PROVENANCE.exists() else \
        "# Provenance: ERA5 monthly surface fields over the sector (local/subarea)\n"
    marker = "\n## Computed series (compute.py)"
    if marker in text:
        text = text[:text.index(marker)]
    PROVENANCE.write_text(text.rstrip("\n") + "\n" + "\n".join(section) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cells", action="store_true", help="rebuild raw/spawning_cells.csv from the bathymetry")
    ap.add_argument("--check", action="store_true", help="recompute in memory and compare with the files; write nothing")
    args = ap.parse_args()
    log = json.loads(LOG_FILE.read_text(encoding="utf-8")) if LOG_FILE.exists() else {}

    if args.cells or not CELLS_FILE.exists():
        bathy = Path(os.environ.get(BATHY_ENV, "")) / BATHY_NAME
        if not os.environ.get(BATHY_ENV) or not bathy.exists():
            raise SystemExit(f"raw/{CELLS_FILE.name} is absent and ${BATHY_ENV}/{BATHY_NAME} was not found: "
                             "set the variable or restore the committed table")
        print(f"building the spawning-cell table from {bathy}")
        cells, cells_info = build_cells(bathy)
        print(f"  {cells_info['cells_in_release_areas']} cells, {cells_info['particles_per_day']} particles per day "
              f"({cells_info['particles_per_day_after_filter']:.0f} after the domain filter), "
              f"{cells_info['cells_in_two_areas']} cells claimed by two areas")
        for a, v in cells_info["per_area"].items():
            print(f"    {a}: {v['cells']:6d} cells {v['particles']:8d} particles")
        if args.check:
            if CELLS_FILE.exists():
                old = pd.read_csv(CELLS_FILE, dtype={"subarea": str})
                same = old.shape == cells.shape and (old.values == cells.values).all()
                print(f"  raw/{CELLS_FILE.name}: {'unchanged' if same else 'DIFFERS from the rebuilt table'}")
        else:
            RAW.mkdir(exist_ok=True)
            cells.to_csv(CELLS_FILE, index=False)
            log["cells"] = cells_info
            print(f"  wrote raw/{CELLS_FILE.name}")
    else:
        cells = pd.read_csv(CELLS_FILE, dtype={"subarea": str})
        if "cells" not in log:
            log["cells"] = {"bathymetry_file": "(committed table)", "bathymetry_sha256": "", "shapefile_sha256": "",
                            "cells_in_release_areas": int(len(cells)),
                            "particles_per_day": int(cells["n_release"].sum()),
                            "particles_per_day_after_filter": float((cells["n_release"] * cells["inside_fraction"]).sum()),
                            "per_area": {a: {"cells": int((cells.subarea == a).sum()),
                                             "particles": int(cells.loc[cells.subarea == a, "n_release"].sum())}
                                         for a in RELEASE_AREAS}}

    out, info = compute(cells)
    for key, b in info["bands"].items():
        print(f"band {key}: {b['cells']} cells on {b['grid_points']} ERA5 points, "
              f"{b['redirected_from_land']} cells redirected from a land point, max distance {b['max_distance_km']:.0f} km")
    for key, b in info["boxes"].items():
        print(f"box {key}: {b['box']}, {b['points']} ocean points")
    print(f"Weddell Gyre curl mean {info['boxes']['weddell_gyre']['mean_curl_1e-7_N_m-3']:+.2f} x 1e-7 N m-3; "
          f"SST box at most {100 * info['boxes']['north_edge']['max_fraction_at_freezing']:.0f}% frozen "
          f"({info['boxes']['north_edge']['worst_month']}), within Mar-Jun at most "
          f"{100 * info['boxes']['north_edge']['max_fraction_at_freezing_mar_jun']:.0f}% "
          f"({info['boxes']['north_edge']['worst_month_mar_jun']})")
    for name, frame in out.items():
        v = frame["value"]
        print(f"  {name + '_monthly.csv':32s} mean {v.mean():9.3f}  sd {v.std():7.3f}  min {v.min():9.3f}  max {v.max():9.3f}")

    if args.check:
        for name, frame in out.items():
            f = HERE / f"{name}_monthly.csv"
            if not f.exists():
                print(f"{f.name}: MISSING")
                continue
            old = pd.read_csv(f)
            same = old.shape == frame.shape and np.allclose(old["value"], frame["value"], atol=0, rtol=0) \
                and (old[["year", "month"]].values == frame[["year", "month"]].values).all()
            print(f"{f.name}: {'unchanged' if same else 'DIFFERS'}")
        return 0

    for name, frame in out.items():
        frame.to_csv(HERE / f"{name}_monthly.csv", index=False)
    log.update({"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "reduction": info,
                "boxes": BOXES, "outputs": list(out)})
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log)
    print(f"wrote {len(out)} csv files, {LOG_FILE.name}, and the compute section of {PROVENANCE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
