#!/usr/bin/env python3
"""Fetch the inputs for the zonal wave 3 index: ERA5 500 hPa meridional
wind from the Copernicus Climate Data Store, and the published Goyal et
al. (2022) series from Mendeley Data for the overlap check.

    python fetch.py            download into raw/ (the ERA5 request is
                               queued at the CDS and can take minutes to
                               hours; the script waits), write PROVENANCE.md
    python fetch.py --check    report what is in raw/ against the request
                               and the Mendeley listing; write nothing
    python fetch.py --era5-only / --mendeley-only

Kept in raw/:

    era5_v500_monthly.nc          ERA5 monthly-mean v at 500 hPa, 1979-01 to
                                  the last complete month, 40-70S, all
                                  longitudes, 1 x 1 degree (regridded by the
                                  CDS from the native 0.25)
    era5_request.json             the request exactly as sent (committed
                                  beside the data as the recipe)
    mendeley/                     every file of Mendeley dataset
                                  10.17632/382gmc8937.1 (Goyal et al. 2022,
                                  version 1), verbatim

Requirements: a free CDS account with the API key in ~/.cdsapirc, the
ERA5 licence accepted once on the dataset page, and `pip install cdsapi`
(0.7 or later; the request uses the current CDS keys data_format and
download_format). Standard library otherwise. Nothing is imported from
elsewhere in the repository.

ERA5 is released under CC-BY 4.0 (Copernicus). The downloaded field is
not committed (it is re-downloadable from a versioned, DOI'd source; the
request file and the sha256 in PROVENANCE.md are the record); the
Mendeley files are CC-BY 4.0 as well and stay in raw/mendeley/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
ERA5_FILE = RAW / "era5_v500_monthly.nc"
REQUEST_FILE = RAW / "era5_request.json"
MENDELEY_DIR = RAW / "mendeley"
LOG_FILE = HERE / "fetch_log.json"
PROVENANCE = HERE / "PROVENANCE.md"

CDS_DATASET = "reanalysis-era5-pressure-levels-monthly-means"
CDS_DOI = "10.24381/cds.6860a573"
FIRST_YEAR = 1979
MENDELEY_ID = "382gmc8937"
MENDELEY_VERSION = 1
MENDELEY_API = (f"https://data.mendeley.com/public-api/datasets/{MENDELEY_ID}/files"
                f"?folder_id=root&version={MENDELEY_VERSION}")
MENDELEY_DOI = f"10.17632/{MENDELEY_ID}.{MENDELEY_VERSION}"
USER_AGENT = "krico-paper2 indices/zw3/fetch.py (python urllib)"


def last_complete_month(today: date | None = None) -> tuple[int, int]:
    """ERA5 final monthly means appear about two months after the month;
    ask for everything up to the month before last and let the CDS fill
    what exists."""
    today = today or date.today()
    y, m = today.year, today.month - 2
    if m < 1:
        y, m = y - 1, m + 12
    return y, m


def build_request(end: tuple[int, int]) -> dict:
    ey, em = end
    return {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": ["v_component_of_wind"],
        "pressure_level": ["500"],
        "year": [str(y) for y in range(FIRST_YEAR, ey + 1)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "time": ["00:00"],
        "area": [-40, -180, -70, 180],   # north, west, south, east
        "grid": [1.0, 1.0],
        "data_format": "netcdf",
        "download_format": "unarchived",
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch_era5(request: dict) -> None:
    try:
        import cdsapi
    except ImportError:
        print("cdsapi is not installed: pip install cdsapi", file=sys.stderr)
        raise SystemExit(2)
    RAW.mkdir(exist_ok=True)
    REQUEST_FILE.write_text(json.dumps({"dataset": CDS_DATASET, "request": request},
                                       indent=2) + "\n", encoding="utf-8")
    print(f"submitting the ERA5 request to the CDS ({request['year'][0]}-{request['year'][-1]}); "
          "this waits in the CDS queue, possibly for a long time")
    client = cdsapi.Client()
    client.retrieve(CDS_DATASET, request, str(ERA5_FILE))
    print(f"downloaded raw/{ERA5_FILE.name}: {ERA5_FILE.stat().st_size / 1e6:.1f} MB")


def list_mendeley() -> list[dict]:
    data = json.loads(fetch_bytes(MENDELEY_API).decode("utf-8"))
    files = []
    for entry in data:
        name = entry.get("filename") or entry.get("name")
        url = (entry.get("content_details") or {}).get("download_url") or entry.get("download_url")
        if not name or not url:
            raise ValueError(f"unexpected Mendeley listing entry: {json.dumps(entry)[:300]}")
        files.append({"filename": name, "url": url, "size": entry.get("size"),
                      "sha256_listed": (entry.get("content_details") or {}).get("sha256")})
    if not files:
        raise ValueError("Mendeley listing is empty")
    return files


def fetch_mendeley(files: list[dict]) -> list[dict]:
    MENDELEY_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for f in files:
        path = MENDELEY_DIR / f["filename"]
        data = fetch_bytes(f["url"])
        path.write_bytes(data)
        out.append({**f, "sha256": sha256_file(path), "bytes": len(data)})
        print(f"downloaded raw/mendeley/{f['filename']}: {len(data)} bytes")
    return out


def write_provenance(log: dict) -> None:
    e = log.get("era5") or {}
    lines = [
        "# Provenance: zonal wave 3 inputs (indices/zw3)",
        "",
        "Written by `fetch.py`; do not edit by hand. Machine-readable copy in",
        "`fetch_log.json`. The index itself is computed by `compute.py`, which",
        "appends its own section to this file.",
        "",
        "## ERA5",
        "",
        f"- Dataset: {CDS_DATASET} (doi:{CDS_DOI}), Copernicus Climate Data Store",
        f"- Request: `raw/{REQUEST_FILE.name}` (v at 500 hPa, monthly means, "
        f"{FIRST_YEAR}-{e.get('last_year_requested', '?')}, 40-70S, 1 x 1 degree)",
        f"- File: `raw/{ERA5_FILE.name}`, {e.get('bytes', '?')} bytes, sha256 `{e.get('sha256', '?')}`",
        f"- Downloaded: {e.get('date', '?')} UTC",
        "- Licence: CC-BY 4.0; cite Hersbach, H. et al. (2020), QJRMS 146, 1999-2049, "
        "doi:10.1002/qj.3803, and the dataset DOI",
        "",
        "## Goyal et al. (2022) reference series",
        "",
        f"- Mendeley Data doi:{MENDELEY_DOI}, listed through the public API, "
        f"downloaded {(log.get('mendeley') or {}).get('date', '?')} UTC into `raw/mendeley/`",
    ]
    for f in (log.get("mendeley") or {}).get("files", []):
        lines.append(f"  - `{f['filename']}`: {f['bytes']} bytes, sha256 `{f['sha256']}`")
    lines += ["- Licence: CC-BY 4.0; cite Goyal, R., Jucker, M., Sen Gupta, A. & England, M. H. "
              "(2022), J. Climate 35, 5137-5149, doi:10.1175/JCLI-D-21-0927.1",
              ""]
    PROVENANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--era5-only", action="store_true")
    ap.add_argument("--mendeley-only", action="store_true")
    args = ap.parse_args()
    end = last_complete_month()
    request = build_request(end)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.check:
        if ERA5_FILE.exists() and REQUEST_FILE.exists():
            sent = json.loads(REQUEST_FILE.read_text(encoding="utf-8"))["request"]
            same = sent["year"][-1] == request["year"][-1]
            print(f"raw/{ERA5_FILE.name}: {ERA5_FILE.stat().st_size / 1e6:.1f} MB, "
                  f"sha256 {sha256_file(ERA5_FILE)[:12]}…; request ended {sent['year'][-1]}, "
                  f"a request today would end {request['year'][-1]}"
                  + ("" if same else " (re-run fetch.py to extend)"))
        else:
            print("no ERA5 file in raw/")
        try:
            files = list_mendeley()
            print(f"Mendeley lists {len(files)} file(s): " + ", ".join(f["filename"] for f in files))
            for f in files:
                p = MENDELEY_DIR / f["filename"]
                print(f"  {f['filename']}: " + ("present" if p.exists() else "MISSING locally"))
        except (urllib.error.URLError, ValueError, json.JSONDecodeError) as e:
            print(f"Mendeley listing failed: {e}")
        return 0

    log = json.loads(LOG_FILE.read_text(encoding="utf-8")) if LOG_FILE.exists() else {}
    if not args.mendeley_only:
        fetch_era5(request)
        log["era5"] = {"date": now, "dataset": CDS_DATASET, "last_year_requested": request["year"][-1],
                       "bytes": ERA5_FILE.stat().st_size, "sha256": sha256_file(ERA5_FILE)}
    if not args.era5_only:
        try:
            files = fetch_mendeley(list_mendeley())
            log["mendeley"] = {"date": now, "doi": MENDELEY_DOI, "files": files}
        except (urllib.error.URLError, ValueError, json.JSONDecodeError) as e:
            print(f"Mendeley download failed: {e}\n"
                  "download the files by hand from https://data.mendeley.com/datasets/"
                  f"{MENDELEY_ID}/{MENDELEY_VERSION} into raw/mendeley/ and re-run with --check",
                  file=sys.stderr)
            if not args.mendeley_only:
                log.setdefault("mendeley", {"date": None, "doi": MENDELEY_DOI, "files": []})
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log)
    print(f"wrote {PROVENANCE.name} and {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
