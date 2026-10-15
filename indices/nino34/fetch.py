#!/usr/bin/env python3
"""Fetch the NOAA CPC ENSO indices: Niño 3.4, ONI, and their relative versions.

    python fetch.py           download into raw/, update PROVENANCE.md and
                              fetch_log.json; re-running without a remote
                              change rewrites nothing in raw/
    python fetch.py --check   compare the remote files with raw/, list the
                              revised months per file, write nothing
                              (exit 0 unchanged, 1 changed, 2 error)

Kept verbatim in raw/:

    detrend.nino34.ascii.txt   monthly Niño 3.4 anomaly (input to the ONI)
    oni.ascii.txt              Oceanic Niño Index, 3-month running mean
    Rnino34.ascii.txt          monthly relative Niño 3.4 (input to the RONI)
    RONI.ascii.txt             Relative Oceanic Niño Index, 3-month running mean
    index.shtml                the CPC indices page: the only place that
                               states the SST product (ERSSTv6) and base
                               periods behind each file

The ONI/RONI pages warn that values may change up to two months after
first posting (ERSSTv6 high-frequency filter), so re-fetches revise the
recent months; every download that changes a value is logged with the
months that moved. The analysis freezes the values at the download date
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
from tidy import FILES, parse  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LOG_FILE = HERE / "fetch_log.json"
PROVENANCE = HERE / "PROVENANCE.md"

BASE = "https://www.cpc.ncep.noaa.gov/data/indices/"
DATA_URLS = {name: BASE + name for name in FILES}
PAGE_URL = BASE + "index.shtml"
PAGE_FILE = RAW / "index.shtml"
ONI_PAGE = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/"
RONI_PAGE = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/"

# No version string inside the files. Hand-maintained from the index page
# and the ONI/RONI pages; a changed page sha256 in --check is the cue to
# re-read them and update.
VERSION_NOTE = """\
As labelled on the CPC indices page on 15 October 2026: Niño 3.4
(detrend.nino34) and the ONI are computed from ERSSTv6 with centered
30-year base periods updated every 5 years; the relative Niño 3.4
(Rnino34) and the RONI from ERSSTv6 with the 1991-2020 base period, the
Niño 3.4 anomaly minus the tropical-mean (20N-20S) SST anomaly, rescaled
to the variance of Niño 3.4. CPC moved these files from ERSSTv5 to
ERSSTv6 in 2026 (the ONI table moved to oni/v6/, v5 kept for reference)
and, per NWS Public Information Statement 26-05, now uses the RONI for
official ENSO monitoring while continuing to update the ONI. The most
recent two months are provisional (high-frequency filter on ERSSTv6)."""

LICENCE_NOTE = ("US Government work, no licence stated. Cite NOAA Climate "
                "Prediction Center (the indices page and the ONI/RONI pages) "
                "and Huang et al. for ERSSTv6; CPC's page cites Huang et al. "
                "(2025, J. Climate, Parts 1 and 2).")

USER_AGENT = "krico-paper2 indices/nino34/fetch.py (python urllib)"


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
    return "; ".join(parts) or "no cell changed"


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"data_urls": DATA_URLS, "page_url": PAGE_URL,
            "last_checked": None, "page_sha256": None, "downloads": []}


def write_provenance(log: dict, parsed: dict) -> None:
    latest = log["downloads"][-1]
    lines = [
        "# Provenance: NOAA CPC ENSO indices (indices/nino34)",
        "",
        "Written by `fetch.py`; do not edit by hand. The download history is",
        "kept in `fetch_log.json`.",
        "",
        f"- Index page: <{PAGE_URL}>, saved verbatim as `raw/{PAGE_FILE.name}`",
        f"- ONI page: <{ONI_PAGE}>",
        f"- RONI page: <{RONI_PAGE}>",
        f"- Downloaded (current `raw/` data): {latest['date']} UTC",
        f"- Last checked against the remote: {log['last_checked']} UTC",
        f"- sha256 page: `{log['page_sha256']}`",
        "- Data files:",
    ]
    for name, rows in parsed.items():
        y0, m0, _ = rows[0]
        y1, m1, _ = rows[-1]
        f = latest["files"][name]
        lines.append(f"  - `{name}` <{DATA_URLS[name]}>: {f['bytes']} bytes, "
                     f"{len(rows)} rows, {cell(y0, m0)} to {cell(y1, m1)}, "
                     f"sha256 `{f['sha256']}`")
    lines.append("- Version note:")
    lines += ["  " + ln for ln in VERSION_NOTE.splitlines()]
    lines += ["- Licence: " + LICENCE_NOTE, "", "## Download history", ""]
    for d in log["downloads"]:
        lines.append(f"- {d['date']}: {d['note']}")
    PROVENANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="compare remote with raw/ and report; write nothing")
    args = ap.parse_args()

    new: dict[str, bytes] = {}
    parsed: dict[str, list] = {}
    try:
        for name, url in DATA_URLS.items():
            new[name] = fetch(url)
        page = fetch(PAGE_URL)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"download failed: {e}", file=sys.stderr)
        return 2
    try:
        for name, data in new.items():
            parsed[name] = parse(data.decode("utf-8"), name)  # validate first
    except (UnicodeDecodeError, ValueError) as e:
        print(f"remote file does not match the expected format: {e}",
              file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    page_sha = sha256(page)
    old = {name: (RAW / name).read_bytes() if (RAW / name).exists() else None
           for name in FILES}
    old_page = PAGE_FILE.read_bytes() if PAGE_FILE.exists() else None

    if args.check:
        changed = False
        for name, data in new.items():
            last = cell(parsed[name][-1][0], parsed[name][-1][1])
            if old[name] is None:
                print(f"{name}: no raw/ copy yet; remote ends {last}")
                changed = True
            elif old[name] == data:
                print(f"{name}: unchanged (ends {last})")
            else:
                d = diff_rows(parse(old[name].decode("utf-8"), name), parsed[name])
                print(f"{name}: CHANGED, {describe(d)}")
                changed = True
        if old_page is None or sha256(old_page) != page_sha:
            print("index page changed: re-read it and update VERSION_NOTE if the "
                  "product or base periods moved")
            changed = True
        else:
            print("index page unchanged")
        return 1 if changed else 0

    RAW.mkdir(exist_ok=True)
    log = load_log()
    log["last_checked"] = now
    notes = []
    files = {}
    for name, data in new.items():
        files[name] = {"sha256": sha256(data), "bytes": len(data),
                       "last_month": cell(parsed[name][-1][0], parsed[name][-1][1])}
        if old[name] is None:
            (RAW / name).write_bytes(data)
            notes.append(f"{name} initial download, ends {files[name]['last_month']}")
            print(f"downloaded raw/{name}: {len(parsed[name])} rows, ends {files[name]['last_month']}")
        elif old[name] == data:
            print(f"raw/{name} unchanged (ends {files[name]['last_month']})")
        else:
            d = diff_rows(parse(old[name].decode("utf-8"), name), parsed[name])
            (RAW / name).write_bytes(data)
            files[name]["diff"] = d
            notes.append(f"{name}: {describe(d)}")
            print(f"updated raw/{name}: {describe(d)}")
    if notes:
        log["downloads"].append({"date": now, "files": files, "note": "; ".join(notes)})
    elif log["downloads"]:
        log["downloads"][-1]["files"] = files  # unchanged bytes, same checksums
    else:
        log["downloads"].append({"date": now, "files": files, "note": "initial download"})
    if old_page != page:
        PAGE_FILE.write_bytes(page)
        if old_page is not None:
            print("index page changed: re-read it and update VERSION_NOTE if the "
                  "product or base periods moved")
    log["page_sha256"] = page_sha
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log, parsed)
    print(f"wrote {PROVENANCE.name} and {LOG_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
