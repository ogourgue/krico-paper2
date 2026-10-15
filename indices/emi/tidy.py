#!/usr/bin/env python3
"""raw/SINTEX_EMI.csv -> emi_monthly.csv (year,month,value).

Parser of record for the JAMSTEC APL VirtualEarth index file as served
on 15 October 2026: a CSV with header

    time,Obs,Mean,F1-Mean,F2-Mean,F2-3DVAR-Mean,<36 SINTEX-F2 member columns>

one row per month, time = YYYY-MM-15. The Obs column holds the observed
El Nino Modoki Index from 1982-01 to the last observed month; the other
columns hold the SINTEX-F2 forecast and are filled only after it. Only
Obs is read; forecast rows (empty Obs) are ignored.

Observed values are printed with binary float noise
(0.06895000000000095 for 0.06895), so they are rounded to five decimals
here, a documented exception to "as printed": the generating values
have at most five. Everything else that departs from the layout raises.

Standard library only. fetch.py imports from this file; nothing is
imported from elsewhere in the repository.
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_FILE = HERE / "raw" / "SINTEX_EMI.csv"
OUT_FILE = HERE / "emi_monthly.csv"

HEADER_START = ("time", "Obs", "Mean")
FIRST = (1982, 1)
DECIMALS = 5
_TIME = re.compile(r"(\d{4})-(\d{2})-15")
_NUMBER = re.compile(r"-?\d+(\.\d+)?([eE]-?\d+)?")


def parse(text: str) -> list[tuple[int, int, str]]:
    """Return [(year, month, obs_rounded), ...] for the observed months."""
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None or tuple(header[:3]) != HEADER_START:
        raise ValueError(f"unexpected header: {header!r}")
    width = len(header)
    rows: list[tuple[int, int, str]] = []
    forecast_started = False
    for lineno, rec in enumerate(reader, 2):
        if not rec or rec == [""]:
            continue
        if len(rec) != width:
            raise ValueError(f"line {lineno}: {len(rec)} fields, header has {width}")
        m = _TIME.fullmatch(rec[0])
        if not m:
            raise ValueError(f"line {lineno}: bad time {rec[0]!r}")
        year, month = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12:
            raise ValueError(f"line {lineno}: bad month {rec[0]!r}")
        obs = rec[1]
        if obs == "":
            forecast_started = True
            continue
        if forecast_started:
            raise ValueError(f"line {lineno}: observed value after a forecast row")
        if not _NUMBER.fullmatch(obs):
            raise ValueError(f"line {lineno}: Obs {obs!r} is not a number")
        rows.append((year, month, f"{round(float(obs), DECIMALS):.{DECIMALS}f}"))
    if not rows:
        raise ValueError("no observed rows")
    _check_continuity(rows)
    return rows


def _check_continuity(rows) -> None:
    y, m = FIRST
    for year, month, _ in rows:
        if (year, month) != (y, m):
            raise ValueError(f"expected {y}-{m:02d}, found {year}-{month:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def write_csv(rows, path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["year", "month", "value"])
        w.writerows(rows)


def main() -> int:
    if not RAW_FILE.exists():
        print(f"missing {RAW_FILE}: run fetch.py first", file=sys.stderr)
        return 2
    rows = parse(RAW_FILE.read_text(encoding="utf-8"))
    write_csv(rows, OUT_FILE)
    y0, m0, v0 = rows[0]
    y1, m1, v1 = rows[-1]
    print(f"wrote {OUT_FILE.name}: {len(rows)} rows, "
          f"{y0}-{m0:02d} ({v0}) to {y1}-{m1:02d} ({v1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
