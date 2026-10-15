#!/usr/bin/env python3
"""raw/asli_calculation_latest.csv -> five asl_*_monthly.csv files.

Parser of record for the BAS ASLI CSV as served on 15 October 2026:

    '#'-prefixed ACDD metadata lines ('# key: value'; '#: text' continues
    the previous key; some lines are free text without a key),
    one column header line, exactly as in HEADER below,
    one row per month, YYYY-MM-01, five numbers, a data_source flag
    (ERA5 for final data, ERA5T for the provisional initial release).

Output, one file per variable, schema year,month,value:

    asl_longitude_monthly.csv       longitude of the ASL centre, degrees east (170-298)
    asl_latitude_monthly.csv        latitude of the ASL centre, degrees north (-80 to -60)
    asl_pressure_actual_monthly.csv actual central pressure, hPa
    asl_pressure_sector_monthly.csv area-mean sector pressure, hPa
    asl_pressure_rel_monthly.csv    relative central pressure = actual - sector, hPa (negative)

The data_source flag is provenance, not a variable: fetch.py lists the
ERA5T months in PROVENANCE.md. Values are copied as printed, not passed
through float. Anything that departs from this layout raises, on purpose.

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
RAW_FILE = HERE / "raw" / "asli_calculation_latest.csv"

HEADER = ("time (mo),longitude (degree),latitude (degree),"
          "actual_central_pressure (hPa),sector_pressure (hPa) [a],"
          "relative_central_pressure (hPa) [b],data_source [c] [d]")

# column index in the source row -> output file stem
VARIABLES = {
    1: "asl_longitude",
    2: "asl_latitude",
    3: "asl_pressure_actual",
    4: "asl_pressure_sector",
    5: "asl_pressure_rel",
}
SOURCES = {"ERA5", "ERA5T"}
FIRST_YEAR = 1959

_TIME = re.compile(r"(\d{4})-(\d{2})-01")
_NUMBER = re.compile(r"-?\d+(\.\d+)?")


def split_metadata(text: str) -> tuple[list[str], str]:
    """Return (metadata lines without the '#', remaining csv text)."""
    meta: list[str] = []
    rest: list[str] = []
    in_meta = True
    for line in text.splitlines():
        if in_meta and line.startswith("#"):
            meta.append(line[1:].strip())
        else:
            in_meta = False
            rest.append(line)
    return meta, "\n".join(rest) + "\n"


def parse_metadata(meta: list[str]) -> dict[str, str]:
    """'key: value' lines into a dict; ': text' lines extend the last key;
    key-less text is appended to the last key as well."""
    out: dict[str, str] = {}
    last = None
    for line in meta:
        if line.startswith(":"):
            if last is not None:
                out[last] += " | " + line[1:].strip()
            continue
        key, sep, value = line.partition(":")
        if sep and " " not in key.strip():
            last = key.strip()
            out[last] = value.strip()
        elif last is not None:
            out[last] += " " + line
    return out


def parse(text: str) -> tuple[dict[str, str], list[tuple[int, int, list[str], str]]]:
    """Return (metadata, rows); each row is (year, month, [5 values], source)."""
    meta_lines, body = split_metadata(text)
    meta = parse_metadata(meta_lines)
    reader = csv.reader(io.StringIO(body))
    header = next(reader, None)
    if header is None or ",".join(header) != HEADER:
        raise ValueError(f"unexpected column header: {header!r}")
    rows: list[tuple[int, int, list[str], str]] = []
    for lineno, rec in enumerate(reader, len(meta_lines) + 2):
        if not rec or rec == [""]:
            continue
        if len(rec) != 7:
            raise ValueError(f"line {lineno}: {len(rec)} fields: {rec!r}")
        m = _TIME.fullmatch(rec[0])
        if not m:
            raise ValueError(f"line {lineno}: bad time {rec[0]!r}")
        year, month = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12:
            raise ValueError(f"line {lineno}: bad month {rec[0]!r}")
        values = rec[1:6]
        for col, v in zip(VARIABLES, values):
            if not _NUMBER.fullmatch(v):
                raise ValueError(
                    f"line {lineno}: {year}-{month:02d} column {col} "
                    f"value {v!r} is not a number")
        if rec[6] not in SOURCES:
            raise ValueError(f"line {lineno}: data_source {rec[6]!r}")
        rows.append((year, month, values, rec[6]))
    if not rows:
        raise ValueError("no data rows")
    _check_continuity(rows)
    return meta, rows


def _check_continuity(rows) -> None:
    """Consecutive months, no gap, no duplicate, from FIRST_YEAR-01."""
    y, m = FIRST_YEAR, 1
    for year, month, _, _ in rows:
        if (year, month) != (y, m):
            raise ValueError(f"expected {y}-{m:02d}, found {year}-{month:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def write_csvs(rows, out_dir: Path) -> list[Path]:
    written = []
    for col, stem in VARIABLES.items():
        path = out_dir / f"{stem}_monthly.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["year", "month", "value"])
            w.writerows((y, m, v[col - 1]) for y, m, v, _ in rows)
        written.append(path)
    return written


def main() -> int:
    if not RAW_FILE.exists():
        print(f"missing {RAW_FILE}: run fetch.py first", file=sys.stderr)
        return 2
    meta, rows = parse(RAW_FILE.read_text(encoding="utf-8"))
    paths = write_csvs(rows, HERE)
    y0, m0, _, _ = rows[0]
    y1, m1, _, _ = rows[-1]
    print(f"{meta.get('id', '?')}: {len(rows)} months, "
          f"{y0}-{m0:02d} to {y1}-{m1:02d}")
    for p, col in zip(paths, VARIABLES):
        print(f"wrote {p.name}: first {rows[0][2][col - 1]}, "
              f"last {rows[-1][2][col - 1]}")
    era5t = [f"{y}-{m:02d}" for y, m, _, s in rows if s == "ERA5T"]
    print(f"ERA5T (provisional) months: {', '.join(era5t) or 'none'}")
    edge = [f"{y}-{m:02d} ({v[0]}E, {v[1]}N)" for y, m, v, _ in rows
            if float(v[0]) in (170.0, 298.0) or float(v[1]) in (-60.0, -80.0)]
    print(f"minimum on the sector boundary: {', '.join(edge) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
