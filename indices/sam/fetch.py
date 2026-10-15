#!/usr/bin/env python3
"""Fetch the Marshall (2003) station-based SAM index from BAS.

    python fetch.py           download into raw/, update PROVENANCE.md and
                              fetch_log.json; re-running without a remote
                              change rewrites nothing in raw/
    python fetch.py --check   compare the remote files with raw/, list the
                              revised months, write nothing
                              (exit 0 unchanged, 1 changed, 2 error)

Two files are kept verbatim in raw/:

    newsam.1957.2007.txt   the monthly index (the filename is historical;
                           the file runs to the present)
    sam.html               the landing page, because the quality colour
                           codes (one or two stations missing, ECMWF
                           interpolation) and the revision notices exist
                           only there, not in the ASCII file

Recent months are revised when late station reports arrive, so every
download that changes the data is logged with the cells that moved
(fetch_log.json, rendered into PROVENANCE.md). The analysis freezes the
values at the download date recorded there.

Standard library only; parse() comes from tidy.py in this folder.
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

PAGE_URL = "https://legacy.bas.ac.uk/met/gjma/sam.html"
DATA_URL = "http://www.nerc-bas.ac.uk/public/icd/gjma/newsam.1957.2007.txt"
DATA_FILE = RAW / "newsam.1957.2007.txt"
PAGE_FILE = RAW / "sam.html"

# No version number is published. Hand-maintained from the landing page;
# a changed page sha256 in --check is the cue to re-read it and update.
VERSION_NOTE = """\
Methodology of Marshall (2003), with the changes announced on the page:
Puerto Montt replaces Valdivia (data from 1960, 11 months of 1961, then
from April 1967; earlier months from Valdivia with a 1971-2000 monthly
offset); Hobart Airport (WMO 94975) replaced by Hobart Airport West
(WMO 94619) from August 2022; means and standard deviations over
1971-2000. Monthly values appear about two weeks after the month ends
and are provisional until all 12 station values are in. As read on
15 October 2026: 'Following the availability of CLIMAT messages for
Gough Island, Feb-May 2026 SAM values have changed slightly'; missing
station data for Marion Island and Gough Island (Jan, Feb, May 2025),
Ile Nouvelle Amsterdam (Mar, Apr 2025) and Marion Island (Feb-Sep 2026)
were interpolated from the ECMWF Operational Analysis. These flags are
colour-coded on the page only; the ASCII file carries no flags."""

LICENCE_NOTE = ("None stated on the page. Cite Marshall, G. J. (2003), "
                "J. Climate 16, 4134-4143, doi:10.1175/1520-0442(2003)016"
                "<4134:TITSAM>2.0.CO;2, and the landing page.")

USER_AGENT = "krico-paper2 indices/sam/fetch.py (python urllib)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell(y: int, m: int) -> str:
    return f"{y}-{m:02d}"


def diff_cells(old_text: str, new_text: str) -> dict:
    """Months added, removed or revised between two versions of the file."""
    a = {(y, m): v for y, m, v in parse(old_text)}
    b = {(y, m): v for y, m, v in parse(new_text)}
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
    return "; ".join(parts) or "no cell changed"


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"data_url": DATA_URL, "page_url": PAGE_URL,
            "last_checked": None, "page_sha256": None, "downloads": []}


def write_provenance(log: dict, rows: list[tuple[int, int, str]]) -> None:
    latest = log["downloads"][-1]
    y0, m0, _ = rows[0]
    y1, m1, _ = rows[-1]
    lines = [
        "# Provenance: Marshall SAM index (indices/sam)",
        "",
        "Written by `fetch.py`; do not edit by hand. The download history is",
        "kept in `fetch_log.json`.",
        "",
        f"- Landing page: <{PAGE_URL}>, saved verbatim as `raw/{PAGE_FILE.name}`",
        f"- Data file: <{DATA_URL}>, saved verbatim as `raw/{DATA_FILE.name}`",
        f"- Downloaded (current `raw/` data): {latest['date']} UTC",
        f"- Last checked against the remote: {log['last_checked']} UTC",
        f"- sha256 data: `{latest['data_sha256']}`",
        f"- sha256 page: `{log['page_sha256']}`",
        f"- Size: {latest['bytes']} bytes, {len(rows)} monthly values",
        f"- First month: {cell(y0, m0)}",
        f"- Last month: {cell(y1, m1)}",
        "- Version note:",
    ]
    lines += ["  " + ln for ln in VERSION_NOTE.splitlines()]
    lines += ["- Licence: " + LICENCE_NOTE, "", "## Download history", ""]
    for d in log["downloads"]:
        lines.append(f"- {d['date']}: last month {d['last_month']}, "
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
        rows = parse(data_text)  # validate before anything is written
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
            print(f"no raw/ copy yet; remote ends {last}, sha256 {data_sha}")
            return 1
        if old_data == data:
            print(f"data unchanged (sha256 {data_sha[:12]}…, ends {last})")
            changed = False
        else:
            d = diff_cells(old_data.decode("utf-8"), data_text)
            print(f"data CHANGED: {describe(d)}")
            changed = True
        if old_page is None or sha256(old_page) != page_sha:
            print("page changed: re-read the notices in it and update "
                  "VERSION_NOTE if they moved")
            changed = True
        else:
            print("page unchanged")
        return 1 if changed else 0

    RAW.mkdir(exist_ok=True)
    log = load_log()
    log["last_checked"] = now
    if old_data is None:
        DATA_FILE.write_bytes(data)
        note = "initial download"
        log["downloads"].append({"date": now, "data_sha256": data_sha,
                                 "bytes": len(data), "last_month": last,
                                 "note": note})
        print(f"downloaded raw/{DATA_FILE.name}: {len(rows)} values, ends {last}")
    elif old_data == data:
        print(f"raw/{DATA_FILE.name} unchanged (ends {last}); provenance refreshed")
    else:
        d = diff_cells(old_data.decode("utf-8"), data_text)
        DATA_FILE.write_bytes(data)
        note = describe(d)
        log["downloads"].append({"date": now, "data_sha256": data_sha,
                                 "bytes": len(data), "last_month": last,
                                 "note": note, "diff": d})
        print(f"updated raw/{DATA_FILE.name}: {note}")
    if old_page != page:
        PAGE_FILE.write_bytes(page)
        if old_page is not None:
            print("landing page changed: re-read its notices and update "
                  "VERSION_NOTE if they moved")
    log["page_sha256"] = page_sha
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log, rows)
    print(f"wrote {PROVENANCE.name} and {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
