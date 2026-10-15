#!/usr/bin/env python3
"""Fetch the BAS Amundsen Sea Low index (ASLI, version 3, ERA5-based).

    python fetch.py           download into raw/, update PROVENANCE.md and
                              fetch_log.json; re-running without a remote
                              change rewrites nothing in raw/
    python fetch.py --check   compare the remote files with raw/, list the
                              revised months per variable, write nothing
                              (exit 0 unchanged, 1 changed, 2 error)

Kept verbatim in raw/:

    asli_calculation_latest.csv   the index; the remote file is replaced
                                  in place every month, so its own header
                                  (id, product_version, date_created,
                                  source) is parsed into the provenance
    asl_index.html                the landing page (method summary)

Months flagged ERA5T are provisional and are replaced by ERA5 final data
about three months later, so re-fetches can change values; every download
that changes the data is logged with the cells that moved. The analysis
freezes the values at the download date recorded in PROVENANCE.md.

Standard library only; the parser comes from tidy.py in this folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tidy import VARIABLES, parse  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LOG_FILE = HERE / "fetch_log.json"
PROVENANCE = HERE / "PROVENANCE.md"

DATA_URL = "https://files.bas.ac.uk/twins/asli/asli_calculation_latest.csv"
PAGE_URL = "https://scotthosking.com/asl_index"
CODE_URL = "https://github.com/antarctica/asli"
DATA_FILE = RAW / "asli_calculation_latest.csv"
PAGE_FILE = RAW / "asl_index.html"

VERSION_NOTE = """\
ASLI version 3 (Hosking et al. 2016 method, Python package `asli`,
ERA5 monthly mean sea level pressure, sector 170-298 E, 80-60 S); the
exact product version, package version and creation date are read from
the file header and listed above. The file's own notes: relative central
pressure is actual minus sector-mean pressure; data_source is ERA5
(final) or ERA5T (initial release, provisional); a known ERA5 issue
affects pressure values and ASL location for May-October 1996 (ECMWF
ERA5 known issue 30). The remote file is overwritten monthly; the former
BAS page bas.ac.uk/data/absl/ is gone (404 on 15 October 2026) and the
GitHub README says the dataset is to move to the UK Polar Data Centre."""

LICENCE_NOTE = ("No licence stated for the data file; the asli code is MIT. "
                "Cite Hosking, J. S., Orr, A., Bracegirdle, T. J. & Turner, J. "
                "(2016), GRL 43, 367-376, doi:10.1002/2015GL067143; the asli "
                "package (Wyld, Zwagerman & Hosking, doi:10.5281/zenodo.20327186); "
                "and ERA5 (doi:10.24381/cds.adbb2d47).")

USER_AGENT = "krico-paper2 indices/asl/fetch.py (python urllib)"
META_KEYS = ("id", "product_version", "source", "date_created",
             "time_coverage_start", "time_coverage_end")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell(y: int, m: int) -> str:
    return f"{y}-{m:02d}"


def table(rows) -> dict[tuple[int, int], tuple[list[str], str]]:
    return {(y, m): (v, s) for y, m, v, s in rows}


def diff_rows(old_rows, new_rows) -> dict:
    """Months added/removed; per variable, cells whose printed value
    changed; months whose data_source flag changed."""
    a, b = table(old_rows), table(new_rows)
    common = sorted(a.keys() & b.keys())
    revised = {}
    for col, stem in VARIABLES.items():
        moved = [{"month": cell(*k), "old": a[k][0][col - 1],
                  "new": b[k][0][col - 1]}
                 for k in common if a[k][0][col - 1] != b[k][0][col - 1]]
        if moved:
            revised[stem] = moved
    flags = [{"month": cell(*k), "old": a[k][1], "new": b[k][1]}
             for k in common if a[k][1] != b[k][1]]
    return {"added": [cell(*k) for k in sorted(b.keys() - a.keys())],
            "removed": [cell(*k) for k in sorted(a.keys() - b.keys())],
            "revised": revised, "source_flag": flags}


def describe(d: dict) -> str:
    parts = []
    if d["added"]:
        parts.append(f"added {d['added'][0]}..{d['added'][-1]} ({len(d['added'])})")
    if d["removed"]:
        parts.append(f"removed {', '.join(d['removed'])}")
    for stem, moved in d["revised"].items():
        months = [r["month"] for r in moved]
        span = months[0] if len(months) == 1 else f"{months[0]}..{months[-1]}"
        parts.append(f"{stem} revised in {len(moved)} months ({span})")
    if d["source_flag"]:
        parts.append("flag " + ", ".join(
            f"{f['month']} {f['old']}->{f['new']}" for f in d["source_flag"]))
    return "; ".join(parts) or "no cell changed"


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"data_url": DATA_URL, "page_url": PAGE_URL, "code_url": CODE_URL,
            "last_checked": None, "page_sha256": None, "downloads": []}


def write_provenance(log: dict, meta: dict, rows) -> None:
    latest = log["downloads"][-1]
    y0, m0, _, _ = rows[0]
    y1, m1, _, _ = rows[-1]
    era5t = [cell(y, m) for y, m, _, s in rows if s == "ERA5T"]
    lines = [
        "# Provenance: Amundsen Sea Low index (indices/asl)",
        "",
        "Written by `fetch.py`; do not edit by hand. The download history is",
        "kept in `fetch_log.json`.",
        "",
        f"- Data file: <{DATA_URL}>, saved verbatim as `raw/{DATA_FILE.name}`",
        f"- Landing page: <{PAGE_URL}>, saved verbatim as `raw/{PAGE_FILE.name}`",
        f"- Code: <{CODE_URL}>",
        f"- Downloaded (current `raw/` data): {latest['date']} UTC",
        f"- Last checked against the remote: {log['last_checked']} UTC",
        f"- sha256 data: `{latest['data_sha256']}`",
        f"- sha256 page: `{log['page_sha256']}`",
        f"- Size: {latest['bytes']} bytes, {len(rows)} months",
        f"- First month: {cell(y0, m0)}",
        f"- Last month: {cell(y1, m1)}",
        "- File header, as read:",
    ]
    lines += [f"  - {k}: {meta.get(k, '(absent)')}" for k in META_KEYS]
    lines += [f"- ERA5T (provisional) months: {', '.join(era5t) or 'none'}",
              "- Version note:"]
    lines += ["  " + ln for ln in VERSION_NOTE.splitlines()]
    lines += ["- Licence: " + LICENCE_NOTE, "", "## Download history", ""]
    for d in log["downloads"]:
        lines.append(f"- {d['date']}: {d['id']}, last month {d['last_month']}, "
                     f"sha256 `{d['data_sha256'][:12]}…`; {d['note']}")
    PROVENANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="compare remote with raw/ and report; write nothing")
    args = ap.parse_args()

    try:
        data = fetch(DATA_URL)
        page = fetch(PAGE_URL)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"download failed: {e}", file=sys.stderr)
        return 2
    try:
        data_text = data.decode("utf-8")
        meta, rows = parse(data_text)  # validate before anything is written
    except (UnicodeDecodeError, ValueError) as e:
        print(f"remote file does not match the expected format: {e}",
              file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_sha, page_sha = sha256(data), sha256(page)
    old_data = DATA_FILE.read_bytes() if DATA_FILE.exists() else None
    old_page = PAGE_FILE.read_bytes() if PAGE_FILE.exists() else None
    last = cell(rows[-1][0], rows[-1][1])
    file_id = meta.get("id", "(no id)")

    if args.check:
        if old_data is None:
            print(f"no raw/ copy yet; remote is {file_id}, ends {last}")
            return 1
        if old_data == data:
            print(f"data unchanged ({file_id}, ends {last})")
            changed = False
        else:
            _, old_rows = parse(old_data.decode("utf-8"))
            print(f"data CHANGED to {file_id}: {describe(diff_rows(old_rows, rows))}")
            changed = True
        if old_page is None or sha256(old_page) != page_sha:
            print("page changed: re-read it and update VERSION_NOTE if needed")
            changed = True
        else:
            print("page unchanged")
        return 1 if changed else 0

    RAW.mkdir(exist_ok=True)
    log = load_log()
    log["last_checked"] = now
    entry = {"date": now, "id": file_id, "data_sha256": data_sha,
             "bytes": len(data), "last_month": last}
    if old_data is None:
        DATA_FILE.write_bytes(data)
        log["downloads"].append({**entry, "note": "initial download"})
        print(f"downloaded raw/{DATA_FILE.name}: {file_id}, {len(rows)} months, ends {last}")
    elif old_data == data:
        print(f"raw/{DATA_FILE.name} unchanged ({file_id}, ends {last}); provenance refreshed")
    else:
        _, old_rows = parse(old_data.decode("utf-8"))
        d = diff_rows(old_rows, rows)
        DATA_FILE.write_bytes(data)
        log["downloads"].append({**entry, "note": describe(d), "diff": d})
        print(f"updated raw/{DATA_FILE.name} to {file_id}: {describe(d)}")
    if old_page != page:
        PAGE_FILE.write_bytes(page)
        if old_page is not None:
            print("landing page changed: re-read it and update VERSION_NOTE if needed")
    log["page_sha256"] = page_sha
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log, meta, rows)
    print(f"wrote {PROVENANCE.name} and {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
