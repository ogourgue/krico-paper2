#!/usr/bin/env python3
"""raw/daily_sectors.csv -> dipole_*_monthly.csv (year,month,value).

Runs on the laptop from the daily table compute.py produced on ECMWF.

    dipole_sia_pacific_monthly.csv   monthly mean sea-ice area, Bellingshausen-Amundsen, 1e6 km2
    dipole_sia_weddell_monthly.csv   same, Weddell
    dipole_sie_pacific_monthly.csv   monthly mean sea-ice extent (>= 15%), Bellingshausen-Amundsen
    dipole_sie_weddell_monthly.csv   same, Weddell
    dipole_monthly.csv               the index: Pacific area anomaly minus Weddell area anomaly
    dipole_extent_monthly.csv        the same built on extent

A monthly mean is the mean of the days with a value; months with fewer
than MIN_DAYS such days are left empty. Anomalies are departures from the
monthly climatology over BASE_YEARS (the complete calendar years in the
holding), each month from the base years that have a value (at least
BASE_MIN_FRACTION of them, else the script stops); the base is the one
thing to change here if the paper needs another. Positive index = more ice on the Pacific side than on the
Weddell side, relative to climatology. Values to four decimals.

Standard library only. Nothing is imported from elsewhere in the repository.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAILY_FILE = HERE / "raw" / "daily_sectors.csv"

BASE_YEARS = (1994, 2024)
BASE_MIN_FRACTION = 0.8   # of the base years a month must have to define its climatology
MIN_DAYS = 20
COLUMNS = ("sia_pacific", "sia_weddell", "sie_pacific", "sie_weddell")
INDEX = {"dipole": ("sia_pacific", "sia_weddell"),
         "dipole_extent": ("sie_pacific", "sie_weddell")}


def read_daily(path: Path) -> dict[str, dict[tuple[int, int], list[float]]]:
    """{column: {(year, month): [daily values]}}, skipping empty values."""
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or reader.fieldnames[:5] != ["date", *COLUMNS]:
            raise ValueError(f"unexpected header {reader.fieldnames!r}")
        out = {c: {} for c in COLUMNS}
        last = None
        for rec in reader:
            y, m, d = (int(s) for s in rec["date"].split("-"))
            if last is not None and (y, m, d) <= last:
                raise ValueError(f"dates not increasing at {rec['date']}")
            last = (y, m, d)
            for c in COLUMNS:
                if rec[c] != "":
                    out[c].setdefault((y, m), []).append(float(rec[c]))
    if not out[COLUMNS[0]]:
        raise ValueError("no data")
    return out


def monthly_mean(daily: dict[tuple[int, int], list[float]]) -> dict[tuple[int, int], float | None]:
    return {ym: (sum(v) / len(v) if len(v) >= MIN_DAYS else None) for ym, v in daily.items()}


def climatology(series: dict[tuple[int, int], float | None]) -> dict[int, float]:
    y0, y1 = BASE_YEARS
    clim = {}
    for month in range(1, 13):
        vals = [series[(y, month)] for y in range(y0, y1 + 1)
                if (y, month) in series and series[(y, month)] is not None]
        if len(vals) < BASE_MIN_FRACTION * (y1 - y0 + 1):
            raise ValueError(f"base period {y0}-{y1}: only {len(vals)} years for month {month}")
        if len(vals) != y1 - y0 + 1:
            print(f"climatology for month {month} from {len(vals)} of {y1 - y0 + 1} base years")
        clim[month] = sum(vals) / len(vals)
    return clim


def write_csv(series, path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["year", "month", "value"])
        for (y, m) in sorted(series):
            v = series[(y, m)]
            w.writerow([y, m, "" if v is None else f"{v:.4f}"])


def main() -> int:
    if not DAILY_FILE.exists():
        print(f"missing {DAILY_FILE}: run compute.py on ECMWF first", file=sys.stderr)
        return 2
    daily = read_daily(DAILY_FILE)
    months = sorted(daily[COLUMNS[0]])
    # every month from the first to the last must be present
    y, m = months[0]
    for ym in months:
        if ym != (y, m):
            raise ValueError(f"missing month {y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    means = {c: monthly_mean(daily[c]) for c in COLUMNS}
    for c in COLUMNS:
        write_csv(means[c], HERE / f"dipole_{c}_monthly.csv")
    short = [f"{ym[0]}-{ym[1]:02d}" for ym, v in means[COLUMNS[0]].items() if v is None]
    print(f"{len(months)} months, {months[0][0]}-{months[0][1]:02d} to {months[-1][0]}-{months[-1][1]:02d}; "
          f"months with fewer than {MIN_DAYS} days (left empty): {', '.join(short) or 'none'}")

    for name, (a, b) in INDEX.items():
        clim_a, clim_b = climatology(means[a]), climatology(means[b])
        idx = {}
        for ym in months:
            va, vb = means[a][ym], means[b][ym]
            idx[ym] = None if va is None or vb is None else (va - clim_a[ym[1]]) - (vb - clim_b[ym[1]])
        write_csv(idx, HERE / f"{name}_monthly.csv")
        vals = [v for v in idx.values() if v is not None]
        print(f"wrote {name}_monthly.csv: base {BASE_YEARS[0]}-{BASE_YEARS[1]}, "
              f"sd {(sum(v * v for v in vals) / len(vals)) ** 0.5:.3f}, "
              f"range {min(vals):.3f} to {max(vals):.3f} (1e6 km2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
