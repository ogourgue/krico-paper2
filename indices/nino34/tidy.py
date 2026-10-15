#!/usr/bin/env python3
"""raw/*.txt -> four *_monthly.csv files (year,month,value).

Parser of record for the NOAA CPC ENSO ascii files as served on
15 October 2026. All four are whitespace-separated, one header line,
values to two decimals, no missing-value marker:

    detrend.nino34.ascii.txt   YR MON TOTAL ClimAdjust ANOM   monthly, from 1949-12
    Rnino34.ascii.txt          YR MTH ANOM                    monthly, from 1949-12
    oni.ascii.txt              SEAS YR TOTAL ANOM             3-month seasons, from DJF 1950
    RONI.ascii.txt             SEAS YR ANOM                   3-month seasons, from DJF 1950

Output, schema year,month,value, value = the ANOM column as printed:

    nino34_monthly.csv       Niño 3.4 SST anomaly, ERSSTv6, centered 30-year base periods
    nino34_rel_monthly.csv   relative Niño 3.4: the above minus the tropical-mean anomaly
    oni_monthly.csv          ONI, 3-month running mean of nino34
    roni_monthly.csv         RONI, 3-month running mean of nino34_rel

Seasonal rows are placed on the centre month of the season: DJF of
year Y (Dec Y-1 to Feb Y) -> (Y, 1), JFM -> (Y, 2), ..., NDJ -> (Y, 12).
The season year in the source is the year of that centre month already.

Anything that departs from the layout above raises, on purpose.
Standard library only. fetch.py imports from this file; nothing is
imported from elsewhere in the repository.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

SEASONS = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
           "JJA", "JAS", "ASO", "SON", "OND", "NDJ")
SEASON_MONTH = {s: i for i, s in enumerate(SEASONS, 1)}

# file name -> (output stem, header tokens, layout, index of the value column)
# layout "ym": tokens are year, month, values...; "sy": season, year, values...
FILES = {
    "detrend.nino34.ascii.txt": ("nino34", ("YR", "MON", "TOTAL", "ClimAdjust", "ANOM"), "ym", 4),
    "Rnino34.ascii.txt":        ("nino34_rel", ("YR", "MTH", "ANOM"), "ym", 2),
    "oni.ascii.txt":            ("oni", ("SEAS", "YR", "TOTAL", "ANOM"), "sy", 3),
    "RONI.ascii.txt":           ("roni", ("SEAS", "YR", "ANOM"), "sy", 2),
}
FIRST = {"ym": (1949, 12), "sy": (1950, 1)}

_VALUE = re.compile(r"-?\d+\.\d{2}")


def parse(text: str, name: str) -> list[tuple[int, int, str]]:
    """Return [(year, month, value_as_printed), ...] for one source file."""
    _, header, layout, vcol = FILES[name]
    lines = text.splitlines()
    rows: list[tuple[int, int, str]] = []
    header_seen = False
    for lineno, line in enumerate(lines, 1):
        tokens = line.split()
        if not tokens:
            continue
        if not header_seen:
            if tuple(tokens) != header:
                raise ValueError(f"{name} line {lineno}: unexpected header {line!r}")
            header_seen = True
            continue
        if len(tokens) != len(header):
            raise ValueError(f"{name} line {lineno}: {len(tokens)} fields: {line!r}")
        if layout == "ym":
            if not (tokens[0].isdigit() and tokens[1].isdigit()):
                raise ValueError(f"{name} line {lineno}: bad year/month {line!r}")
            year, month = int(tokens[0]), int(tokens[1])
        else:
            if tokens[0] not in SEASON_MONTH or not tokens[1].isdigit():
                raise ValueError(f"{name} line {lineno}: bad season/year {line!r}")
            year, month = int(tokens[1]), SEASON_MONTH[tokens[0]]
        if not 1 <= month <= 12:
            raise ValueError(f"{name} line {lineno}: month {month}")
        for v in tokens[2:]:
            if not _VALUE.fullmatch(v):
                raise ValueError(f"{name} line {lineno}: {v!r} is not a two-decimal number")
        rows.append((year, month, tokens[vcol]))
    if not rows:
        raise ValueError(f"{name}: no data rows")
    _check_continuity(rows, name, FIRST[layout])
    return rows


def _check_continuity(rows, name, first) -> None:
    y, m = first
    for year, month, _ in rows:
        if (year, month) != (y, m):
            raise ValueError(f"{name}: expected {y}-{m:02d}, found {year}-{month:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def write_csv(rows, path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["year", "month", "value"])
        w.writerows(rows)


def main() -> int:
    missing = [n for n in FILES if not (RAW / n).exists()]
    if missing:
        print(f"missing in raw/: {', '.join(missing)}; run fetch.py first", file=sys.stderr)
        return 2
    for name, (stem, _, _, _) in FILES.items():
        rows = parse((RAW / name).read_text(encoding="utf-8"), name)
        out = HERE / f"{stem}_monthly.csv"
        write_csv(rows, out)
        y0, m0, v0 = rows[0]
        y1, m1, v1 = rows[-1]
        print(f"wrote {out.name}: {len(rows)} rows, "
              f"{y0}-{m0:02d} ({v0}) to {y1}-{m1:02d} ({v1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
