#!/usr/bin/env python3
"""Fetch the JAMSTEC El Nino Modoki Index (EMI) from APL VirtualEarth.

    python fetch.py           download into raw/, update PROVENANCE.md and
                              fetch_log.json; re-running without a remote
                              change rewrites nothing in raw/
    python fetch.py --check   compare the remote files with raw/, list the
                              revised months, write nothing
                              (exit 0 unchanged, 1 changed, 2 error)

Kept verbatim in raw/:

    SINTEX_EMI.csv        the VirtualEarth graph file: observed EMI in the
                          Obs column from 1982-01, SINTEX-F2 forecast in
                          the other columns; overwritten monthly
    data_download.html    the JAMSTEC page stating the method (OISST v2,
                          1983-2015 climatology, Ashok et al. 2007 boxes)

The file sits behind a JavaScript site with no visible link; its address
follows the pattern VirtualEarth uses for every index graph. JAMSTEC
refuses the default Python user agent, so a browser-like one is sent.
Every download that changes an observed value is logged with the months
that moved; the analysis freezes the values at the download date
recorded in PROVENANCE.md.

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
from tidy import parse  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LOG_FILE = HERE / "fetch_log.json"
PROVENANCE = HERE / "PROVENANCE.md"

DATA_URL = "https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_EMI.csv"
PAGE_URL = "https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html"
SITE_URL = "https://www.jamstec.go.jp/virtualearth/general/en/index.html"
DATA_FILE = RAW / "SINTEX_EMI.csv"
PAGE_FILE = RAW / "data_download.html"

VERSION_NOTE = """\
No version number is published. As stated on the JAMSTEC data page on
15 October 2026: monthly climate indices from 1982 to present based on
NOAA OISST Ver.2, SST anomalies as deviations from the monthly
climatology of 1983-2015; EMI defined after Ashok et al. (2007) as
SSTA(box A) - 0.5 SSTA(box B) - 0.5 SSTA(box C) with A = 165E-140W,
10S-10N, B = 110-70W, 15S-5N, C = 125-145E, 10S-20N. The former file
aplinfo/sintexf/DATA/emi.monthly.txt is a stub redirecting to
VirtualEarth. Observed values carry float noise and are rounded to five
decimals by tidy.py."""

LICENCE_NOTE = ("None stated; JAMSTEC disclaimer applies. Cite Ashok, K., "
                "Behera, S. K., Rao, S. A., Weng, H. & Yamagata, T. (2007), "
                "J. Geophys. Res. 112, C11007, doi:10.1029/2006JC003798, "
                "and JAMSTEC APL VirtualEarth as the data source.")

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
              "krico-paper2/indices/emi")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell(y: int, m: int) -> str:
    return f"{y}-{m:02d}"


def diff_rows(old_rows, new_rows) -> dict:
    a = {(y, m): v for y, m, v in old_rows}
    b = {(y, m): v for y, m, v in new_rows}
    return {
        "added": [cell(*k) for k in sorted(b.keys() - a.keys())],
        "removed": [cell(*k) for k in sorted(a.keys() - b.keys())],
        "revised": [{"month": cell(*k), "old": a[k], "new": b[k]}
                    for k in sorted(a.keys() & b.keys()) if a[k] != b[k]],
    }


def describe(d: dict) -> str:
    parts = []
    if d["added"]:
        parts.append(f"added {d['added'][0]}..{d['added'][-1]} ({len(d['added'])})")
    if d["removed"]:
        parts.append(f"removed {', '.join(d['removed'])}")
    if d["revised"]:
        parts.append("revised " + ", ".join(
            f"{r['month']} {r['old']}->{r['new']}" for r in d["revised"]))
    return "; ".join(parts) or "no observed value changed"


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"data_url": DATA_URL, "page_url": PAGE_URL, "site_url": SITE_URL,
            "last_checked": None, "page_sha256": None, "downloads": []}


def write_provenance(log: dict, rows) -> None:
    latest = log["downloads"][-1]
    y0, m0, _ = rows[0]
    y1, m1, _ = rows[-1]
    lines = [
        "# Provenance: El Nino Modoki Index (indices/emi)",
        "",
        "Written by `fetch.py`; do not edit by hand. The download history is",
        "kept in `fetch_log.json`.",
        "",
        f"- Data file: <{DATA_URL}>, saved verbatim as `raw/{DATA_FILE.name}`",
        f"- Method page: <{PAGE_URL}>, saved verbatim as `raw/{PAGE_FILE.name}`",
        f"- Site: <{SITE_URL}> (Menu > EMI)",
        f"- Downloaded (current `raw/` data): {latest['date']} UTC",
        f"- Last checked against the remote: {log['last_checked']} UTC",
        f"- sha256 data: `{latest['data_sha256']}`",
        f"- sha256 page: `{log['page_sha256']}`",
        f"- Size: {latest['bytes']} bytes, {len(rows)} observed months",
        f"- First month: {cell(y0, m0)}",
        f"- Last observed month: {cell(y1, m1)}",
        "- Version note:",
    ]
    lines += ["  " + ln for ln in VERSION_NOTE.splitlines()]
    lines += ["- Licence: " + LICENCE_NOTE, "", "## Download history", ""]
    for d in log["downloads"]:
        lines.append(f"- {d['date']}: last observed month {d['last_month']}, "
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
        rows = parse(data.decode("utf-8"))  # validate before anything is written
    except (UnicodeDecodeError, ValueError) as e:
        print(f"remote file does not match the expected format: {e}",
              file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_sha, page_sha = sha256(data), sha256(page)
    old_data = DATA_FILE.read_bytes() if DATA_FILE.exists() else None
    old_page = PAGE_FILE.read_bytes() if PAGE_FILE.exists() else None
    last = cell(rows[-1][0], rows[-1][1])

    if args.check:
        if old_data is None:
            print(f"no raw/ copy yet; remote observed series ends {last}")
            return 1
        if old_data == data:
            print(f"data unchanged (ends {last})")
            changed = False
        else:
            d = diff_rows(parse(old_data.decode("utf-8")), rows)
            print(f"data CHANGED: {describe(d)} (forecast columns not compared)")
            changed = True
        if old_page is None or sha256(old_page) != page_sha:
            print("method page changed: re-read it and update VERSION_NOTE if needed")
            changed = True
        else:
            print("method page unchanged")
        return 1 if changed else 0

    RAW.mkdir(exist_ok=True)
    log = load_log()
    log["last_checked"] = now
    entry = {"date": now, "data_sha256": data_sha, "bytes": len(data), "last_month": last}
    if old_data is None:
        DATA_FILE.write_bytes(data)
        log["downloads"].append({**entry, "note": "initial download"})
        print(f"downloaded raw/{DATA_FILE.name}: {len(rows)} observed months, ends {last}")
    elif old_data == data:
        print(f"raw/{DATA_FILE.name} unchanged (ends {last}); provenance refreshed")
    else:
        d = diff_rows(parse(old_data.decode("utf-8")), rows)
        DATA_FILE.write_bytes(data)
        note = describe(d) + " (forecast columns change every month and are not compared)"
        log["downloads"].append({**entry, "note": note, "diff": d})
        print(f"updated raw/{DATA_FILE.name}: {note}")
    if old_page != page:
        PAGE_FILE.write_bytes(page)
        if old_page is not None:
            print("method page changed: re-read it and update VERSION_NOTE if needed")
    log["page_sha256"] = page_sha
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log, rows)
    print(f"wrote {PROVENANCE.name} and {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
