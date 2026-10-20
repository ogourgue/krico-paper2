#!/usr/bin/env python3
"""Per-subarea retreat and advance day per spawning year, from the per-cell
table that compute.py left in raw/ (laptop step).

    python tidy.py            write the annual files, tidy_log.json and the
                              tidy section of PROVENANCE.md
    python tidy.py --check    recompute in memory and compare with the files
                              on disk; write nothing

Spawning year Y covers the releases of 15 November Y-1 to 14 March Y.
Its retreat is the retreat of ice year Y-1 (the spring before the first
release) and its advance the advance of ice year Y (the autumn after the
last release), both from raw/cell_timing.csv. For each recruiting
subarea (88.3, 48.1, 48.2, 48.4) the value is the mean over the subarea's
NSIDC cells weighted by the particles each cell holds; cells without the
event (no ice that year, or ice all year) are left out and the weights
renormalised, and the share of the weight that had the event is written
beside the value.

Outputs (year,value; one row per spawning year)
    retreat_<sub>_annual.csv         day of retreat, 365-day calendar counted from
                                     1 January of the ice year (values above 365
                                     fall in January-February of the next year)
    retreat_<sub>_share_annual.csv   weight share of cells with a retreat
    advance_<sub>_annual.csv         day-of-year of advance
    advance_<sub>_share_annual.csv   weight share of cells with an advance
    <sub> in 883, 481, 482, 484

numpy and pandas only; nothing imported from elsewhere in the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
TABLE = RAW / "cell_timing.csv"
LOG_FILE = HERE / "tidy_log.json"
PROVENANCE = HERE / "PROVENANCE.md"
RECRUITING = {"88.3": "883", "48.1": "481", "48.2": "482", "48.4": "484"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def weighted(g: pd.DataFrame, col: str) -> tuple[float, float]:
    has = g[col].notna()
    w = g.weight
    share = float((w * has).sum() / w.sum()) if w.sum() > 0 else np.nan
    value = float(np.average(g.loc[has, col], weights=w[has])) if has.any() else np.nan
    return value, share


def tidy() -> tuple[dict[str, pd.DataFrame], dict]:
    t = pd.read_csv(TABLE, dtype={"subarea": str})
    ice_years = sorted(t.ice_year.unique())
    years = [y for y in range(ice_years[0] + 1, ice_years[-1] + 1)]      # Y needs ice years Y-1 and Y
    out: dict[str, pd.DataFrame] = {}
    info = {"ice_years": [int(ice_years[0]), int(ice_years[-1])], "spawning_years": [years[0], years[-1]], "subareas": {}}
    for label, key in RECRUITING.items():
        s = t[t.subarea == label]
        rows = {"retreat": [], "retreat_share": [], "advance": [], "advance_share": []}
        for y in years:
            r_val, r_share = weighted(s[s.ice_year == y - 1], "retreat_doy")
            a_val, a_share = weighted(s[s.ice_year == y], "advance_doy")
            rows["retreat"].append((y, round(r_val, 1))); rows["retreat_share"].append((y, round(r_share, 3)))
            rows["advance"].append((y, round(a_val, 1))); rows["advance_share"].append((y, round(a_share, 3)))
        for name, data in rows.items():
            base, _, suffix = name.partition("_")
            fname = f"{base}_{key}_{suffix + '_' if suffix else ''}annual"
            out[fname] = pd.DataFrame(data, columns=["year", "value"])
        warnings.simplefilter("ignore", RuntimeWarning)          # all-NaN means are legitimate (no event)
        info["subareas"][label] = {
            "cells": int(s.groupby(["row", "col"]).ngroups), "weight": float(s.drop_duplicates(["row", "col"]).weight.sum()),
            "retreat_mean": float(np.nanmean([v for _, v in rows["retreat"]])),
            "retreat_share_mean": float(np.nanmean([v for _, v in rows["retreat_share"]])),
            "advance_mean": float(np.nanmean([v for _, v in rows["advance"]])),
            "advance_share_mean": float(np.nanmean([v for _, v in rows["advance_share"]])),
            "apr1_share_mean": float((s.weight * s.ice_on_apr1).sum() / s.weight.sum())}
    return out, info


def write_provenance(log: dict) -> None:
    i = log["info"]
    section = [
        "",
        "## Tidied series (tidy.py)",
        "",
        f"- Run: {log['date']} UTC on `raw/cell_timing.csv` (sha256 `{log['table_sha256'][:12]}…`)",
        f"- Spawning years {i['spawning_years'][0]}-{i['spawning_years'][1]} from ice years "
        f"{i['ice_years'][0]}-{i['ice_years'][1]} (retreat of Y-1, advance of Y)",
        "- Per subarea (cells; mean retreat day and weight share; mean advance day and weight share; "
        "weight share already in ice on 1 April): "
        + "; ".join(f"{k}: {v['cells']}; {v['retreat_mean']:.0f}, {v['retreat_share_mean']:.2f}; "
                    f"{v['advance_mean']:.0f}, {v['advance_share_mean']:.2f}; {v['apr1_share_mean']:.2f}"
                    for k, v in i["subareas"].items()),
        "- Output: " + ", ".join(f"{k}.csv" for k in log["outputs"]),
    ]
    text = PROVENANCE.read_text(encoding="utf-8") if PROVENANCE.exists() else \
        "# Provenance: sea-ice retreat and advance day on the release cells (local/ice_timing)\n"
    marker = "\n## Tidied series (tidy.py)"
    if marker in text:
        text = text[:text.index(marker)]
    PROVENANCE.write_text(text.rstrip("\n") + "\n" + "\n".join(section) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="recompute in memory and compare with the files; write nothing")
    args = ap.parse_args()
    if not TABLE.exists():
        print(f"{TABLE} missing: run compute.py on ECMWF and copy raw/ here", file=sys.stderr)
        return 2
    out, info = tidy()
    print(f"spawning years {info['spawning_years'][0]}-{info['spawning_years'][1]}")
    for k, v in info["subareas"].items():
        print(f"  {k}: {v['cells']} cells, weight {v['weight']:.0f}; retreat mean day {v['retreat_mean']:.0f} on "
              f"{100 * v['retreat_share_mean']:.0f}% of the weight; advance mean day {v['advance_mean']:.0f} on "
              f"{100 * v['advance_share_mean']:.0f}%; {100 * v['apr1_share_mean']:.0f}% already in ice on 1 April")
    if args.check:
        for name, frame in out.items():
            f = HERE / f"{name}.csv"
            if not f.exists():
                print(f"{f.name}: MISSING"); continue
            old = pd.read_csv(f)
            same = old.shape == frame.shape and np.allclose(old["value"], frame["value"], equal_nan=True) \
                and (old["year"].values == frame["year"].values).all()
            print(f"{f.name}: {'unchanged' if same else 'DIFFERS'}")
        return 0
    for name, frame in out.items():
        frame.to_csv(HERE / f"{name}.csv", index=False)
    log = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "table_sha256": sha256_file(TABLE),
           "info": info, "outputs": list(out)}
    LOG_FILE.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    write_provenance(log)
    print(f"wrote {len(out)} csv files, {LOG_FILE.name}, and the tidy section of {PROVENANCE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
