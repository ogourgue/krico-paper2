#!/usr/bin/env python3
"""Zonal wave 3 magnitude and phase after Goyal et al. (2022), from
raw/era5_v500_monthly.nc, checked against the published series in
raw/mendeley/.

    python compute.py

Method, as in the authors' notebook (github.com/rishavgoyal55/NEW-ZONAL-
WAVE-3-INDEX): monthly anomalies of 500 hPa meridional wind over 40-70S
relative to the 1979-2020 monthly climatology; EOFs of those anomalies
over 1979-2020 with sqrt(cos lat) weights; PC1 and PC2 scaled to unit
variance; magnitude = sqrt(PC1^2 + PC2^2); phase = atan2(PC2, PC1) in
degrees, -180 to 180. Months after 2020 are projected onto the same
EOFs with the same scaling, so the index is defined identically across
the record. The EOFs are computed here with a plain SVD, which is what
the eofs package does underneath.

EOF signs are arbitrary. If the Mendeley files hold the published series
(magnitude and phase, or PC1 and PC2), the signs and order of the two
EOFs are chosen to match it over the overlap, and the correlations are
reported; with no reference, the signs are fixed by a stated geometric
rule and the README says so.

Output, schema year,month,value:

    zw3_magnitude_monthly.csv   dimensionless (unit-variance PC scaling)
    zw3_phase_monthly.csv       degrees, -180 to 180
    zw3_pc1_monthly.csv, zw3_pc2_monthly.csv

Requires numpy and xarray (NetCDF backend). Nothing is imported from
elsewhere in the repository.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
ERA5_FILE = RAW / "era5_v500_monthly.nc"
MENDELEY_DIR = RAW / "mendeley"
LOG_FILE = HERE / "compute_log.json"
PROVENANCE = HERE / "PROVENANCE.md"

BASE = (1979, 2020)          # climatology and EOF period of Goyal et al. (2022)
LAT_RANGE = (-70.0, -40.0)
TIME_DIMS = ("valid_time", "time", "date")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_v(path: Path):
    """Return (v[time, lat, lon] as float64, years, months, lat, lon)."""
    with xr.open_dataset(path) as ds:
        name = "v" if "v" in ds else next(n for n in ds.data_vars if ds[n].ndim >= 3)
        da = ds[name]
        tdim = next(d for d in TIME_DIMS if d in da.dims)
        for d in list(da.dims):
            if d not in (tdim, "latitude", "longitude") and da.sizes[d] == 1:
                da = da.squeeze(d, drop=True)
        da = da.sortby("latitude").sel(latitude=slice(*LAT_RANGE)).transpose(tdim, "latitude", "longitude")
        t = da[tdim].values
        years = np.array([int(str(x)[:4]) for x in t])
        months = np.array([int(str(x)[5:7]) for x in t])
        v = da.values.astype("float64")
        lat = da["latitude"].values.astype("float64")
        lon = da["longitude"].values.astype("float64")
    if np.isnan(v).any():
        bad = np.unique(years[np.isnan(v).any(axis=(1, 2))])
        raise ValueError(f"NaN in the wind field in years {bad.tolist()}")
    order = np.lexsort((months, years))
    return v[order], years[order], months[order], lat, lon


def anomalies(v, years, months):
    base = (years >= BASE[0]) & (years <= BASE[1])
    clim = np.stack([v[base & (months == m)].mean(axis=0) for m in range(1, 13)])
    return v - clim[months - 1]


def eofs_and_pcs(anom, years, lat):
    """EOF1, EOF2 from the base period; PCs for every month, unit variance
    over the base period (eofs pcscaling=1, projectField eofscaling=1)."""
    base = (years >= BASE[0]) & (years <= BASE[1])
    w = np.sqrt(np.clip(np.cos(np.deg2rad(lat)), 0.0, 1.0))[:, None]
    weighted = anom * w
    n, nlat, nlon = weighted.shape
    a = weighted[base].reshape(base.sum(), nlat * nlon)
    a = a - a.mean(axis=0)
    u, s, vt = np.linalg.svd(a, full_matrices=False)
    lam = s ** 2 / (a.shape[0] - 1)
    frac = lam / lam.sum()
    pcs = (weighted.reshape(n, nlat * nlon) @ vt[:2].T) / np.sqrt(lam[:2])
    return pcs, frac[:4]


def phase_deg(pc1, pc2):
    return np.degrees(np.arctan2(pc2, pc1))


# --- reference series from Mendeley ------------------------------------------

def read_reference():
    """Return (years, months, pc1, pc2, source_file) or None. Accepts a
    NetCDF with zw3index_magnitude/zw3index_phase or pc1/pc2 (the names in
    the authors' notebook), or a text table with such columns."""
    if not MENDELEY_DIR.exists():
        return None
    for path in sorted(MENDELEY_DIR.iterdir()):
        ref = _read_reference_file(path)
        if ref is not None:
            return (*ref, path.name)
    return None


def _read_reference_file(path: Path):
    try:
        with xr.open_dataset(path) as ds:
            names = {n.lower(): n for n in ds.variables}
            tdim = next((d for d in TIME_DIMS if d in ds.dims), None)
            if tdim is None:
                return None
            t = ds[tdim].values
            years = np.array([int(str(x)[:4]) for x in t])
            months = np.array([int(str(x)[5:7]) for x in t])
            pc1 = pc2 = None
            if "pc1" in names and "pc2" in names:
                pc1, pc2 = ds[names["pc1"]].values, ds[names["pc2"]].values
            else:
                mag = next((names[k] for k in names if "magnitude" in k), None)
                pha = next((names[k] for k in names if "phase" in k), None)
                if mag and pha:
                    m, p = ds[mag].values, np.deg2rad(ds[pha].values)
                    pc1, pc2 = m * np.cos(p), m * np.sin(p)
            if pc1 is None:
                return None
            return years, months, np.asarray(pc1, float), np.asarray(pc2, float)
    except Exception:
        pass
    try:  # text table
        rows = [ln.replace(",", " ").split() for ln in path.read_text(errors="replace").splitlines()]
        rows = [r for r in rows if r]
        header = [h.lower() for h in rows[0]]
        if not any("phase" in h or "pc" in h for h in header):
            return None
        data = np.array([[float(x) for x in r] for r in rows[1:]])
        col = {h: i for i, h in enumerate(header)}
        if "year" in col and "month" in col:
            years, months = data[:, col["year"]].astype(int), data[:, col["month"]].astype(int)
        else:
            return None
        if "pc1" in col and "pc2" in col:
            return years, months, data[:, col["pc1"]], data[:, col["pc2"]]
        mag = next((i for h, i in col.items() if "magnitude" in h), None)
        pha = next((i for h, i in col.items() if "phase" in h), None)
        if mag is not None and pha is not None:
            p = np.deg2rad(data[:, pha])
            return years, months, data[:, mag] * np.cos(p), data[:, mag] * np.sin(p)
    except Exception:
        return None
    return None


def align(pcs, years, months, ref):
    """Choose signs (and order) of PC1/PC2 to match the reference over the
    overlap; return (pcs_aligned, report)."""
    ry, rm, rpc1, rpc2 = ref[:4]
    key = {(y, m): i for i, (y, m) in enumerate(zip(years, months))}
    idx = [(key[(y, m)], j) for j, (y, m) in enumerate(zip(ry, rm)) if (y, m) in key]
    if len(idx) < 24:
        return pcs, {"status": "overlap too short", "months": len(idx)}
    ours = np.array([pcs[i] for i, _ in idx])
    theirs = np.array([[rpc1[j], rpc2[j]] for _, j in idx])
    best = None
    for swap in (False, True):
        o = ours[:, ::-1] if swap else ours
        for s1 in (1, -1):
            for s2 in (1, -1):
                r1 = np.corrcoef(s1 * o[:, 0], theirs[:, 0])[0, 1]
                r2 = np.corrcoef(s2 * o[:, 1], theirs[:, 1])[0, 1]
                score = r1 + r2
                if best is None or score > best[0]:
                    best = (score, swap, s1, s2, r1, r2)
    _, swap, s1, s2, r1, r2 = best
    out = pcs[:, ::-1].copy() if swap else pcs.copy()
    out[:, 0] *= s1
    out[:, 1] *= s2
    mag_r = np.corrcoef(np.hypot(out[[i for i, _ in idx], 0], out[[i for i, _ in idx], 1]),
                        np.hypot(theirs[:, 0], theirs[:, 1]))[0, 1]
    return out, {"status": "aligned to reference", "months": len(idx), "swapped": swap,
                 "sign_pc1": s1, "sign_pc2": s2, "r_pc1": round(float(r1), 4),
                 "r_pc2": round(float(r2), 4), "r_magnitude": round(float(mag_r), 4),
                 "reference_file": ref[4]}


def fix_signs_geometric(pcs, anom, years, lat, lon):
    """Without a reference: sign each EOF so that its loading pattern has a
    positive meridional-wind maximum in the longitude band 0-60E for
    EOF1 and 60-120E for EOF2 (the ridge/trough geometry of Goyal et al.
    Fig. 2 to within a quarter wave). Stated in the README; replace by
    the reference alignment when the Mendeley files are present."""
    base = (years >= BASE[0]) & (years <= BASE[1])
    out = pcs.copy()
    report = {"status": "geometric sign rule (no reference found)"}
    for k, band in ((0, (0.0, 60.0)), (1, (60.0, 120.0))):
        pattern = (anom[base] * pcs[base, k][:, None, None]).mean(axis=0)
        sel = (lon >= band[0]) & (lon < band[1])
        if pattern[:, sel].mean() < 0:
            out[:, k] *= -1
            report[f"sign_pc{k + 1}"] = -1
        else:
            report[f"sign_pc{k + 1}"] = 1
    return out, report


def write_csv(rows, path: Path, fmt: str) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["year", "month", "value"])
        w.writerows((y, m, format(v, fmt)) for y, m, v in rows)


def main() -> int:
    if not ERA5_FILE.exists():
        print(f"missing {ERA5_FILE}: run fetch.py first", file=sys.stderr)
        return 2
    v, years, months, lat, lon = load_v(ERA5_FILE)
    first, last = f"{years[0]}-{months[0]:02d}", f"{years[-1]}-{months[-1]:02d}"
    if years[0] > BASE[0] or years[-1] < BASE[1]:
        print(f"the file ({first} to {last}) does not cover the base period "
              f"{BASE[0]}-{BASE[1]}", file=sys.stderr)
        return 2
    anom = anomalies(v, years, months)
    pcs, frac = eofs_and_pcs(anom, years, lat)
    ref = read_reference()
    if ref is not None:
        pcs, report = align(pcs, years, months, ref)
    else:
        pcs, report = fix_signs_geometric(pcs, anom, years, lat, lon)
    mag = np.hypot(pcs[:, 0], pcs[:, 1])
    pha = phase_deg(pcs[:, 0], pcs[:, 1])

    write_csv(zip(years, months, mag), HERE / "zw3_magnitude_monthly.csv", ".4f")
    write_csv(zip(years, months, pha), HERE / "zw3_phase_monthly.csv", ".2f")
    write_csv(zip(years, months, pcs[:, 0]), HERE / "zw3_pc1_monthly.csv", ".4f")
    write_csv(zip(years, months, pcs[:, 1]), HERE / "zw3_pc2_monthly.csv", ".4f")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log = {"run": now, "input": ERA5_FILE.name, "input_sha256": sha256_file(ERA5_FILE),
           "grid": {"nlat": int(lat.size), "nlon": int(lon.size),
                    "dlat": round(float(abs(lat[1] - lat[0])), 3)},
           "months": int(len(years)), "first_month": first, "last_month": last,
           "base_period": list(BASE), "variance_fraction_eof1_to_4": [round(float(x), 4) for x in frac],
           "sign_alignment": report}
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")

    section = [
        "",
        "## Computed index (compute.py)",
        "",
        f"- Run: {now} UTC on `raw/{ERA5_FILE.name}` (sha256 `{log['input_sha256'][:12]}…`), "
        f"{lat.size} x {lon.size} grid, {len(years)} months, {first} to {last}",
        f"- Climatology and EOF period: {BASE[0]}-{BASE[1]}; variance fraction of EOF1-4: "
        + ", ".join(f"{x:.1%}" for x in frac),
        "- Sign alignment: " + json.dumps(report),
        "- Output: zw3_magnitude_monthly.csv, zw3_phase_monthly.csv, zw3_pc1_monthly.csv, "
        "zw3_pc2_monthly.csv",
    ]
    text = PROVENANCE.read_text(encoding="utf-8") if PROVENANCE.exists() else "# Provenance: zonal wave 3\n"
    marker = "\n## Computed index (compute.py)"
    if marker in text:
        text = text[:text.index(marker)]
    PROVENANCE.write_text(text.rstrip("\n") + "\n" + "\n".join(section) + "\n", encoding="utf-8")

    print(f"{len(years)} months, {first} to {last}; EOF1-4 variance: "
          + ", ".join(f"{x:.1%}" for x in frac))
    print("sign alignment:", json.dumps(report))
    print(f"magnitude mean {mag.mean():.3f}, max {mag.max():.3f}; wrote four csv files, "
          f"{LOG_FILE.name}, and the compute section of {PROVENANCE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
