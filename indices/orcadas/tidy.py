#!/usr/bin/env python3
"""raw/Orcadas.All.temperature.html -> orcadas_*_monthly.csv.

Parser of record for the SCAR READER station page as served on
16 October 2026: one HTML table, header row "Year Jan ... Dec", then one
row per calendar year with twelve cells. The cells are <th> tags that
are never closed (nor are the <h5> and <i> inside them, nor always the
<tr>), and the colour is a <font color = x> tag inside the cell; the
walker closes a cell at the next cell or row, as a browser does. A cell holds "-" (no value), a
temperature in degrees C with one decimal, or a temperature followed by
the percentage of synoptic reports behind it in parentheses, e.g.
"-7.6 (100)". The page colours cells by data origin (black: full record
from the national operator; green: preliminary GTS; blue: CLIMAT
monthly mean; red: fewer than 90% of reports). The text download drops
the red cells, which is why the HTML table is the file kept.

Output, schema year,month,value, from the first month with a value:

    orcadas_monthly.csv          temperature as published; empty where the
                                 table prints "-" (no gap filling)
    orcadas_obs_pct_monthly.csv  percentage of reports; empty where the
                                 table prints none
    orcadas_origin_monthly.csv   the cell's colour attribute as found in
                                 the HTML, if the markup carries one;
                                 written only when at least one cell has it

The markup around the colour could not be inspected before this was
written, so the colour extraction is best-effort: it reads a color=,
bgcolor=, style="color:..." or class attribute on the cell or on any tag
inside it, and main() prints what it found. Everything else that departs
from the layout raises.

Standard library only. fetch.py imports from this file; nothing is
imported from elsewhere in the repository.
"""
from __future__ import annotations

import csv
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_FILE = HERE / "raw" / "Orcadas.All.temperature.html"

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
FIRST_YEAR = 1903
_CELL = re.compile(r"(-?\d+\.\d)\s*(?:\(\s*(\d+)\s*\))?")
_PRODUCED = re.compile(r"Table produced on\s+(\d{2}-[A-Za-z]{3}-\d{4})")
_STYLE_COLOR = re.compile(r"color\s*:\s*([^;\"']+)", re.I)


class _Table(HTMLParser):
    """Collect rows of (text, colour) cells from every table on the page,
    nested tables included; parse() picks the one headed 'Year'."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[tuple[str, str]]]] = []
        self._stack: list[dict] = []
        self.text: list[str] = []

    @staticmethod
    def _colour_of(attrs) -> str:
        for k, v in attrs:
            if v is None:
                continue
            k = k.lower()
            if k in ("color", "bgcolor"):
                return v.strip()
            if k == "style":
                m = _STYLE_COLOR.search(v)
                if m:
                    return m.group(1).strip()
            if k == "class" and v.strip():
                return "class:" + v.strip()
        return ""

    def _close_cell(self, t: dict) -> None:
        if t["cell"] is not None:
            t["row"].append((" ".join("".join(t["cell"]).split()), t["colour"]))
            t["cell"] = None

    def _close_row(self, t: dict) -> None:
        self._close_cell(t)
        if t["row"]:
            t["rows"].append(t["row"])
        t["row"] = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append({"rows": [], "row": None, "cell": None, "colour": ""})
            return
        if not self._stack:
            return
        t = self._stack[-1]
        if tag == "tr":            # a new row closes the previous one (no </tr> needed)
            self._close_row(t)
            t["row"] = []
        elif tag in ("td", "th"):  # a new cell closes the previous one (no </td> needed)
            if t["row"] is None:
                t["row"] = []
            self._close_cell(t)
            t["cell"] = []
            t["colour"] = self._colour_of(attrs)
        elif t["cell"] is not None and not t["colour"]:
            t["colour"] = self._colour_of(attrs)

    def handle_endtag(self, tag):
        if not self._stack:
            return
        t = self._stack[-1]
        if tag in ("td", "th"):
            self._close_cell(t)
        elif tag == "tr":
            self._close_row(t)
        elif tag == "table":
            self._close_row(t)
            self.tables.append(self._stack.pop()["rows"])

    def handle_data(self, data):
        self.text.append(data)
        if self._stack and self._stack[-1]["cell"] is not None:
            self._stack[-1]["cell"].append(data)


def parse(html: str) -> tuple[dict, list[tuple[int, int, str, str, str]]]:
    """Return (meta, rows); each row is (year, month, value, pct, origin),
    with value and pct as printed ('' when absent), from the first month
    that has a value to the last."""
    t = _Table()
    t.feed(html)
    meta = {}
    m = _PRODUCED.search(" ".join("".join(t.text).split()))
    meta["table_produced"] = m.group(1) if m else ""
    while t._stack:  # unclosed <table> tags: flush what was collected
        t._close_row(t._stack[-1])
        t.tables.append(t._stack.pop()["rows"])
    data = [rows for rows in t.tables if rows and rows[0] and rows[0][0][0] == "Year"]
    if not data:
        found = [[c for c, _ in rows[0]][:3] for rows in t.tables if rows]
        raise ValueError(f"no table headed 'Year'; tables found start with {found!r}")
    header = [c for c, _ in data[0][0]]
    if tuple(header[1:13]) != MONTHS:
        raise ValueError(f"unexpected header row: {header!r}")
    rows: list[tuple[int, int, str, str, str]] = []
    expect = FIRST_YEAR
    for cells in data[0][1:]:
        if len(cells) != 13:
            raise ValueError(f"row {cells[0][0]!r}: {len(cells)} cells, expected 13")
        if not cells[0][0].isdigit() or int(cells[0][0]) != expect:
            raise ValueError(f"expected year {expect}, found {cells[0][0]!r}")
        year = expect
        expect += 1
        for month, (text, colour) in enumerate(cells[1:], 1):
            if text == "-":
                rows.append((year, month, "", "", colour))
                continue
            mm = _CELL.fullmatch(text)
            if not mm:
                raise ValueError(f"{year}-{month:02d}: cannot read cell {text!r}")
            rows.append((year, month, mm.group(1), mm.group(2) or "", colour))
    # trim leading and trailing months without a value
    first = next(i for i, r in enumerate(rows) if r[2] != "")
    last = max(i for i, r in enumerate(rows) if r[2] != "")
    return meta, rows[first:last + 1]


def write_csv(rows, path: Path, col: int) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["year", "month", "value"])
        w.writerows((y, m, r[col]) for r in rows for y, m in [(r[0], r[1])])


def main() -> int:
    if not RAW_FILE.exists():
        print(f"missing {RAW_FILE}: run fetch.py first", file=sys.stderr)
        return 2
    meta, rows = parse(RAW_FILE.read_text(encoding="utf-8", errors="replace"))
    write_csv(rows, HERE / "orcadas_monthly.csv", 2)
    write_csv(rows, HERE / "orcadas_obs_pct_monthly.csv", 3)
    y0, m0 = rows[0][:2]
    y1, m1 = rows[-1][:2]
    missing = [f"{y}-{m:02d}" for y, m, v, _, _ in rows if v == ""]
    low = [f"{y}-{m:02d} ({p}%)" for y, m, v, p, _ in rows if p and int(p) < 90]
    print(f"table produced on {meta['table_produced'] or '?'}; "
          f"{len(rows)} months, {y0}-{m0:02d} to {y1}-{m1:02d}")
    print(f"wrote orcadas_monthly.csv and orcadas_obs_pct_monthly.csv")
    print(f"months without a value: {', '.join(missing) or 'none'}")
    print(f"months below 90% of reports: {', '.join(low) or 'none'}")
    colours = sorted({r[4] for r in rows if r[4]})
    if colours:
        write_csv(rows, HERE / "orcadas_origin_monthly.csv", 4)
        print(f"wrote orcadas_origin_monthly.csv; colour attributes found: {colours}")
    else:
        print("no colour attribute found on any cell; origin file not written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
