"""
Paper 2, Figure 1 (per-subarea draft): interannual recruitment by subarea.

Reads data/aggregated_subarea.nc (from aggregate_subarea.py, run on ECMWF)
and draws one panel per release subarea, each showing the season-mean
outcome composition per spawning year as stacked bars (Paper 1 F3 palette)
with the success rate on a twin axis.

"Season-mean" and "per subarea" are defined as in Paper 1 Table S1: for each
release day the fraction of particles *released in that subarea* ending in
each outcome; then averaged over the 120 release days. The denominator is the
subarea's own release count, so panels are comparable in rate even though
48.5 releases ten times more particles than 48.3.

Also prints the subarea x year success matrix and its correlation matrix
(the synchrony question), and a one-line variance partition of the domain
series into subarea contributions.

Usage:
  python plot_subarea.py [--aggregated PATH] [--out PATH] [--by release|fate]
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

mpl.rcParams.update({"font.family": "Arial", "font.size": 8})

LAYERS = ["exited_domain", "killed_M1", "killed_M4", "killed_M5_no_FIV",
          "killed_M5_not_on_shelf", "killed_M6_no_advance", "success"]
LABELS = {
    "exited_domain": "Domain exit", "killed_M1": "Ice at spawning (M1)",
    "killed_M4": "Calyptopis starvation (M4)", "killed_M5_no_FIV": "Under-developed (M5a)",
    "killed_M5_not_on_shelf": "Off-shelf (M5b)", "killed_M6_no_advance": "No winter ice (M6)",
    "success": "Recruitment success",
}
NAMES = {"88.3": "Amundsen Sea", "48.1": "Antarctic Peninsula", "48.2": "South Orkney Is.",
         "48.3": "South Georgia", "48.4": "South Sandwich Is.", "48.5": "Weddell Sea",
         "48.6N": "Bouvet N (>60°S)", "48.6S": "Bouvet S (<60°S)"}
PANEL_ORDER = ["88.3", "48.1", "48.2", "48.3", "48.4", "48.5", "48.6N", "48.6S"]
FORCING_STEP_YEAR = 2019


def layer_colors() -> dict[str, tuple]:
    colors = {"success": mpl.colors.to_rgba("C2"), "exited_domain": mpl.colors.to_rgba("0.7")}
    killed = [l for l in LAYERS if l.startswith("killed_")]
    cmap = mpl.colormaps["YlOrRd"]
    for layer, t in zip(killed, np.linspace(0.35, 0.85, len(killed))):
        colors[layer] = cmap(t)
    return colors


def season_means(ds: xr.Dataset, var: str):
    """(years, subareas, frac[year, subarea, outcome] in %, outcome names, release share[subarea])."""
    names = list(ds["outcome"].values.astype(str))
    subs = list(ds["subarea"].values.astype(str))
    c = ds[var].values.astype(float).copy()          # (year, sd, sub, outcome)
    has = ds["has_data"].values
    ci, mi = names.index("censored"), names.index("killed_M6_no_advance")
    c[..., mi] += c[..., ci]
    c[..., ci] = 0.0
    denom = c.sum(axis=3)                             # particles per (year, sd, sub)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where((has[:, :, None] & (denom > 0))[..., None],
                        100.0 * c / np.maximum(denom[..., None], 1), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        season = np.nanmean(frac, axis=1)             # (year, sub, outcome)
    share = denom.sum(axis=(0, 1)) / denom.sum()      # share of all particles per subarea
    return ds["year"].values, subs, season, names, share


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregated", default=str(here / "data" / "aggregated_subarea.nc"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--by", choices=["release", "fate"], default="release")
    args = ap.parse_args()
    out = args.out or str(here / f"timeseries_subarea_{args.by}.png")

    ds = xr.open_dataset(args.aggregated)
    years, subs, season, names, share = season_means(ds, f"counts_{args.by}")
    colors = layer_colors()
    si = names.index("success")

    fig, axes = plt.subplots(4, 2, figsize=(6.5, 8.5), sharex=True)
    for ax, code in zip(axes.ravel(), PANEL_ORDER):
        k = subs.index(code)
        bottom = np.zeros(len(years))
        for layer in LAYERS:
            v = season[:, k, names.index(layer)]
            ax.bar(years, v, bottom=bottom, width=0.8, color=colors[layer],
                   edgecolor="none", label=LABELS[layer])
            bottom += v
        ax.axvline(FORCING_STEP_YEAR - 0.5, color="0.5", ls=":", lw=0.8)
        ax.set_ylim(0, 100)
        ax.set_title(f"{NAMES[code]} ({code}) — {100 * share[k]:.0f}% of releases",
                     fontsize=8, loc="left")
        ax2 = ax.twinx()
        ax2.plot(years, season[:, k, si], color="k", lw=0.9, marker="o", ms=2)
        ax2.set_ylim(0, max(5.0, np.nanmax(season[:, k, si]) * 1.15))
        ax2.tick_params(labelsize=7)
        ax.tick_params(labelsize=7)
    for ax in axes[-1]:
        ax.set_xticks(years[::4])
        ax.tick_params(axis="x", rotation=90)
    axes[0, 0].set_xlim(years[0] - 0.6, years[-1] + 0.6)
    fig.text(0.015, 0.5, f"Season-mean share of particles released in subarea (%)",
             rotation=90, va="center", fontsize=8)
    fig.text(0.985, 0.5, "Season-mean recruitment success (%, black line)",
             rotation=270, va="center", fontsize=8)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", ncol=4, fontsize=7,
               framealpha=1.0, bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=(0.03, 0.04, 0.97, 1))
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Wrote {out}")

    # ---- numbers for the meeting
    S = season[:, [subs.index(c) for c in PANEL_ORDER], si]   # (year, sub)
    print(f"\nSeason-mean success (%) by {args.by} subarea:")
    print(f"{'year':>6s} " + " ".join(f"{c:>7s}" for c in PANEL_ORDER))
    for i, yr in enumerate(years):
        print(f"{yr:>6d} " + " ".join(f"{S[i, j]:7.2f}" for j in range(S.shape[1])))
    print(f"{'mean':>6s} " + " ".join(f"{np.nanmean(S[:, j]):7.2f}" for j in range(S.shape[1])))
    print(f"{'sd':>6s} " + " ".join(f"{np.nanstd(S[:, j], ddof=1):7.2f}" for j in range(S.shape[1])))
    print(f"{'cv':>6s} " + " ".join(f"{np.nanstd(S[:, j], ddof=1) / np.nanmean(S[:, j]):7.2f}"
                                   for j in range(S.shape[1])))

    print("\nInterannual correlation of success between subareas (synchrony):")
    ok = [j for j in range(S.shape[1]) if np.nanstd(S[:, j]) > 0]
    R = np.corrcoef(S[:, ok].T)
    print(f"{'':>6s} " + " ".join(f"{PANEL_ORDER[j]:>6s}" for j in ok))
    for a, j in enumerate(ok):
        print(f"{PANEL_ORDER[j]:>6s} " + " ".join(f"{R[a, b]:6.2f}" for b in range(len(ok))))

    # Contribution of each subarea to domain interannual variance:
    # domain success = sum_k share_k * S_k (shares are nearly constant).
    sh = np.array([share[subs.index(c)] for c in PANEL_ORDER])
    contrib = sh * S                                   # (year, sub)
    dom = contrib.sum(axis=1)
    cov = np.array([np.cov(contrib[:, j], dom)[0, 1] for j in range(S.shape[1])])
    print("\nShare of domain-wide interannual variance in success attributable to each subarea")
    print("(cov(share_k * S_k, domain) / var(domain); sums to 1):")
    for c, v in zip(PANEL_ORDER, cov / dom.var(ddof=1)):
        print(f"  {c:6s} {100 * v:6.1f}%")


if __name__ == "__main__":
    main()
