"""
Where does the ice-source signature live? Panel (b) of plot_ice_source.py
repeated per release subarea: NSIDC minus GLORYS12, in percentage points of
the particles released in that subarea, per spawning year, for success, M1,
M5b and M6, with 2019 marked. One panel per subarea, 2 x 3: the four
recruiting subareas (88.3, 48.1, 48.2, 48.4) and the two where M1 is large
(48.5, 48.6S), where a flip of the M1 difference at the forcing change
would show most clearly.

Differences are rates (per subarea release), so panels compare as rates and
do not sum to the domain panel of plot_ice_source.py; the domain panel is
the release-weighted sum.

Above each panel: the pre/post-2019 shift of each outcome's
difference, in pp (S = success). Stdout: the full shift table with the
ice-state check, per subarea.

Inputs:  ../timeseries/data/aggregated_subarea.nc   (GLORYS12 ice, production)
         data/aggregated_subarea_nsidc.nc           (NSIDC ice, aggregate_nsidc.py)
Output:  timeseries_ice_source_subarea.png

Usage:
  python plot_ice_source_subarea.py [--out PATH]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from plot_ice_source import (DIFF_LAYERS, FILES, FORCING_STEP_YEAR, HERE, LABELS,
                             layer_colors, print_shift_table, season_mean_fractions)

SUBAREAS = ["88.3", "48.1", "48.2", "48.4", "48.5", "48.6S"]
FIGSIZE = (9.32, 5.6)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = Path(args.out) if args.out else HERE / "timeseries_ice_source_subarea.png"

    per_subarea = {}
    for sub in SUBAREAS:
        runs = {}
        for name, path in FILES.items():
            with xr.open_dataset(path) as ds:
                years, season, names = season_mean_fractions(ds, sub)
                runs[name] = season
        per_subarea[sub] = (years, runs, runs["NSIDC"] - runs["GLORYS12"], names)
    colors = layer_colors()

    fig, axes = plt.subplots(2, 3, figsize=FIGSIZE, sharex=True,
                             gridspec_kw={"wspace": 0.28, "hspace": 0.35})
    for ax, sub in zip(axes.flat, SUBAREAS):
        years, runs, diff, names = per_subarea[sub]
        pre, post = years < FORCING_STEP_YEAR, years >= FORCING_STEP_YEAR
        for layer in DIFF_LAYERS:
            li = names.index(layer)
            ax.plot(years, diff[:, li], color=colors[layer], lw=1.1, marker="o", ms=2.5,
                    label=LABELS[layer])
        ax.axhline(0, color="0.3", lw=0.7)
        ax.axvline(FORCING_STEP_YEAR - 0.5, color="0.5", ls=":", lw=0.9)
        ax.text(0.03, 0.95, sub, transform=ax.transAxes, fontsize=10, fontweight="bold",
                va="top", ha="left")
        ax.grid(axis="y", lw=0.4, alpha=0.5)
        ax.tick_params(labelsize=9)
        shifts = []
        for layer, short in zip(DIFF_LAYERS, ("S", "M1", "M5b", "M6")):
            li = names.index(layer)
            shifts.append(f"{short} {diff[post, li].mean() - diff[pre, li].mean():+.1f}")
        ax.set_title(f"\u0394 at {FORCING_STEP_YEAR} (pp): " + " ".join(shifts), fontsize=7, loc="left",
                     color="0.3")
    for ax in axes[1]:
        ax.set_xlabel("Spawning year", fontsize=10)
    for ax in axes[:, 0]:
        ax.set_ylabel("NSIDC minus GLORYS12 (pp)", fontsize=10)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9, ncol=4,
               loc="lower center", bbox_to_anchor=(0.5, -0.04))
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Wrote {out}")

    for sub in SUBAREAS:
        years, runs, diff, names = per_subarea[sub]
        print_shift_table(years, runs, diff, names, f"released in {sub} (pp of its own releases)")


if __name__ == "__main__":
    main()
