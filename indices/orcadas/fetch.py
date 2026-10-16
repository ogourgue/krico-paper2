#!/usr/bin/env python3
"""Fetch the SCAR READER monthly mean surface temperature at Orcadas.

    python fetch.py           download into raw/, update PROVENANCE.md and
                              fetch_log.json; re-running without a remote
                              change rewrites nothing in raw/
    python fetch.py --check   compare the remote files with raw/, list the
                              revised months, write nothing
                              (exit 0 unchanged, 1 changed, 2 error)

Kept verbatim in raw/:

    Orcadas.All.temperature.html   the station table, values with the
                                   percentage of synoptic reports and
                                   the data-origin colour; the text
                                   download drops cells below 90% and
                                   is therefore not used
    data.html                      the READER data page with the colour
                                   key and the 90% rule

READER is revised as national operators supply full records (green GTS
values become black), so re-fetches can change values and percentages;
every download that changes a value is logged with the months that
moved. The analysis freezes the values at the download date recorded in
PROVENANCE.md.

Standard library only; the parser comes from tidy.py in this folder.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import zlib
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

DATA_URL = "https://legacy.bas.ac.uk/met/READER/surface/Orcadas.All.temperature.html"
PAGE_URL = "https://legacy.bas.ac.uk/met/READER/data.html"
DATA_FILE = RAW / "Orcadas.All.temperature.html"
PAGE_FILE = RAW / "data.html"

VERSION_NOTE = """\
No version number is published; the table carries its production date,
read into the provenance above. Station: Orcadas, WMO 88968, Laurie
Island, South Orkney Islands, 60.7 S 44.7 W, 6 m. Monthly means are the
average of the 00, 06, 12 and 18 UTC synoptic reports; the percentage
of reports available follows each value (truncated, not rounded, since
3 March 2009). Values before 1956 are CLIMAT monthly means without a
percentage. Months without a value are listed above (the 2012 BAS
station page cited January 1992 and October 2002 as missing; both carry
values in the table of 1 September 2026, so READER has been revised).
Colour key on the READER data page: black, full record from the
national operator; green, preliminary GTS data; blue, CLIMAT monthly
mean only; red, fewer than 90% of reports (dropped from the text
download, kept here)."""

LICENCE_NOTE = ("Open Government Licence v3.0 (stated in the page footer). "
                "Cite Turner, J. et al. (2004), J. Climate 17, 2890-2898, "
                "doi:10.1175/1520-0442(2004)017<2890:TSRPTA>2.0.CO;2, and the "
                "READER dataset DOI given on the data page.")

USER_AGENT = "krico-paper2 indices/orcadas/fetch.py (python urllib)"


def fetch(url: str) -> tuple[bytes, str]:
    """Return (body, headers); gzip or deflate bodies are decompressed."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        headers = str(r.headers)
        enc = (r.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip" or body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    elif enc == "deflate":
        body = zlib.decompress(body)
    return body, headers


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cell(y: int, m: int) -> str:
    return f"{y}-{m:02d}"


def diff_rows(old_rows, new_rows) -> dict:
    a = {(r[0], r[1]): r[2:4] for r in old_rows}
    b = {(r[0], r[1]): r[2:4] for r in new_rows}
    common = sorted(a.keys() & b.keys())
    return {
        "added": [cell(*k) for k in sorted(b.keys() - a.keys())],
        "removed": [cell(*k) for k in sorted(a.keys() - b.keys())],
        "revised": [{"month": cell(*k), "old": a[k][0], "new": b[k][0]}
                    for k in common if a[k][0] != b[k][0]],
        "pct_changed": [{"month": cell(*k), "old": a[k][1], "new": b[k][1]}
                        for k in common if a[k][1] != b[k][1]],
    }


def describe(d: dict) -> str:
    parts = []
    if d["added"]:
        parts.append(f"added {d['added'][0]}..{d['added'][-1]} ({len(d['added'])})")
    if d["removed"]:
        parts.append(f"removed {', '.join(d['removed'])}")
    if d["revised"]:
        parts.append("revised " + ", ".join(
            f"{r['month']} {r['old'] or '-'}->{r['new'] or '-'}" for r in d["revised"]))
    if d["pct_changed"]:
        parts.append("percentage changed in " + ", ".join(
            f"{r['month']} {r['old'] or '-'}->{r['new'] or '-'}" for r in d["pct_changed"]))
    return "; ".join(parts) or "no value or percentage changed"


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"data_url": DATA_URL, "page_url": PAGE_URL,
            "last_checked": None, "page_sha256": None, "downloads": []}


def write_provenance(log: dict, meta: dict, rows) -> None:
    latest = log["downloads"][-1]
    y0, m0 = rows[0][:2]
    y1, m1 = rows[-1][:2]
    missing = [cell(r[0], r[1]) for r in rows if r[2] == ""]
    low = [f"{cell(r[0], r[1])} ({r[3]}%)" for r in rows if r[3] and int(r[3]) < 90]
    lines = [
        "# Provenance: Orcadas monthly mean surface temperature (indices/orcadas)",
        "",
        "Written by `fetch.py`; do not edit by hand. The download history is",
        "kept in `fetch_log.json`.",
        "",
        f"- Station table: <{DATA_URL}>, saved verbatim as `raw/{DATA_FILE.name}`",
        f"- READER data page: <{PAGE_URL}>, saved verbatim as `raw/{PAGE_FILE.name}`",
        f"- Table produced on: {meta.get('table_produced') or '(not found in page)'}",
        f"- Downloaded (current `raw/` data): {latest['date']} UTC",
        f"- Last checked against the remote: {log['last_checked']} UTC",
        f"- sha256 table: `{latest['data_sha256']}`",
        f"- sha256 page: `{log['page_sha256']}`",
        f"- Size: {latest['bytes']} bytes, {len(rows)} months",
        f"- First month: {cell(y0, m0)}",
        f"- Last month: {cell(y1, m1)}",
        f"- Months without a value: {', '.join(missing) or 'none'}",
        f"- Months below 90% of reports: {', '.join(low) or 'none'}",
        "- Version note:",
    ]
    lines += ["  " + ln for ln in VERSION_NOTE.splitlines()]
    lines += ["- Licence: " + LICENCE_NOTE, "", "## Download history", ""]
    for d in log["downloads"]:
        lines.append(f"- {d['date']}: table of {d['table_produced'] or '?'}, "
                     f"last month {d['last_month']}, sha256 `{d['data_sha256'][:12]}…`; "
                     f"{d['note']}")
    PROVENANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="compare remote with raw/ and report; write nothing")
    args = ap.parse_args()

    try:
        data, data_headers = fetch(DATA_URL)
        page, _ = fetch(PAGE_URL)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"download failed: {e}", file=sys.stderr)
        return 2
    try:
        meta, rows = parse(data.decode("utf-8", errors="replace"))
    except ValueError as e:
        RAW.mkdir(exist_ok=True)
        (RAW / "_unparsed.html").write_bytes(data)
        (RAW / "_unparsed.headers.txt").write_text(data_headers, encoding="utf-8")
        print(f"remote page does not match the expected layout: {e}\n"
              f"response kept as raw/_unparsed.html ({len(data)} bytes) with its "
              f"headers in raw/_unparsed.headers.txt; delete both once resolved",
              file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_sha, page_sha = sha256(data), sha256(page)
    old_data = DATA_FILE.read_bytes() if DATA_FILE.exists() else None
    old_page = PAGE_FILE.read_bytes() if PAGE_FILE.exists() else None
    last = cell(rows[-1][0], rows[-1][1])
    produced = meta.get("table_produced", "")

    if args.check:
        if old_data is None:
            print(f"no raw/ copy yet; remote table of {produced or '?'} ends {last}")
            return 1
        if old_data == data:
            print(f"table unchanged (produced {produced or '?'}, ends {last})")
            changed = False
        else:
            _, old_rows = parse(old_data.decode("utf-8", errors="replace"))
            print(f"table CHANGED (now produced {produced or '?'}): "
                  f"{describe(diff_rows(old_rows, rows))}")
            changed = True
        if old_page is None or sha256(old_page) != page_sha:
            print("READER data page changed: re-read the colour key and update "
                  "VERSION_NOTE if it moved")
            changed = True
        else:
            print("READER data page unchanged")
        return 1 if changed else 0

    RAW.mkdir(exist_ok=True)
    log = load_log()
    log["last_checked"] = now
    entry = {"date": now, "table_produced": produced, "data_sha256": data_sha,
             "bytes": len(data), "last_month": last}
    if old_data is None:
        DATA_FILE.write_bytes(data)
        log["downloads"].append({**entry, "note": "initial download"})
        print(f"downloaded raw/{DATA_FILE.name}: table of {produced or '?'}, "
              f"{len(rows)} months, ends {last}")
    elif old_data == data:
        print(f"raw/{DATA_FILE.name} unchanged (ends {last}); provenance refreshed")
    else:
        _, old_rows = parse(old_data.decode("utf-8", errors="replace"))
        d = diff_rows(old_rows, rows)
        DATA_FILE.write_bytes(data)
        note = describe(d)
        log["downloads"].append({**entry, "note": note, "diff": d})
        print(f"updated raw/{DATA_FILE.name}: {note}")
    if old_page != page:
        PAGE_FILE.write_bytes(page)
        if old_page is not None:
            print("READER data page changed: re-read the colour key and update "
                  "VERSION_NOTE if it moved")
    log["page_sha256"] = page_sha
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log, meta, rows)
    print(f"wrote {PROVENANCE.name} and {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
