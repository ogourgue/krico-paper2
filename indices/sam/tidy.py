#!/usr/bin/env python3
"""raw/newsam.1957.2007.txt -> sam_monthly.csv (year,month,value).

Parser of record for the Marshall SAM ASCII file as served by BAS on
15 October 2026:

    one header line of month abbreviations JAN ... DEC,
    one blank line,
    one line per calendar year: YYYY followed by up to 12 values,
    the current year truncated after the last available month.

Values are copied as printed (two decimals), not re-formatted through
float. Anything that departs from this layout raises, on purpose: the
format has never shown a missing-value marker, and a silent guess here
would propagate into the window tables.

Standard library only. fetch.py imports parse() from this file; nothing
is imported from elsewhere in the repository.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_FILE = HERE / "raw" / "newsam.1957.2007.txt"
OUT_FILE = HERE / "sam_monthly.csv"

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_YEAR = re.compile(r"\d{4}")
_VALUE = re.compile(r"-?\d+\.\d{2}")


def parse(text: str) -> list[tuple[int, int, str]]:
    """Return [(year, month, value_as_printed), ...] in file order."""
    rows: list[tuple[int, int, str]] = []
    header_seen = False
    for lineno, line in enumerate(text.splitlines(), 1):
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == "JAN":
            if tuple(tokens) != MONTHS:
                raise ValueError(f"line {lineno}: unexpected header {line!r}")
            if header_seen:
                raise ValueError(f"line {lineno}: second header")
            header_seen = True
            continue
        if not header_seen:
            raise ValueError(f"line {lineno}: data before header: {line!r}")
        if not _YEAR.fullmatch(tokens[0]):
            raise ValueError(f"line {lineno}: expected a year, got {line!r}")
        year = int(tokens[0])
        values = tokens[1:]
        if not 1 <= len(values) <= 12:
            raise ValueError(f"line {lineno}: {len(values)} values for {year}")
        for month, value in enumerate(values, 1):
            if not _VALUE.fullmatch(value):
                raise ValueError(
                    f"line {lineno}: {year}-{month:02d} value {value!r} "
                    "is not a two-decimal number")
            rows.append((year, month, value))
    if not rows:
        raise ValueError("no data rows")
    _check_continuity(rows)
    return rows


def _check_continuity(rows: list[tuple[int, int, str]]) -> None:
    """Consecutive years, 12 months each except the last year."""
    years = [y for y, m, _ in rows if m == 1]
    if years != list(range(years[0], years[-1] + 1)):
        raise ValueError(f"years are not consecutive: {years}")
    counts = {y: 0 for y in years}
    for y, _, _ in rows:
        counts[y] += 1
    short = [y for y in years[:-1] if counts[y] != 12]
    if short:
        raise ValueError(f"years with fewer than 12 months before the last: {short}")
    if years[0] != 1957:
        raise ValueError(f"first year is {years[0]}, expected 1957")


def write_csv(rows: list[tuple[int, int, str]], path: Path) -> None:
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
