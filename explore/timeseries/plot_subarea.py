"""
Paper 2, Figure 1 (per-subarea draft): interannual recruitment by subarea.

Slide-sized (9.32 x 3.74 in). Reads data/aggregated_subarea.nc (from aggregate_subarea.py, run on ECMWF)
and draws one panel per release subarea, each showing the season-mean
outcome composition per spawning year as stacked bars (Paper 1 F3 palette)
(no success line: that is the companion figure success_subarea_<by>.png,
where all subareas share one axis so synchrony can be read directly).

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

mpl.rcParams.update({"font.family": "Arial", "font.size": 10})
SLIDE = (9.32, 3.74)   # Google Slides default content size, inches

LAYERS = ["exited_domain", "killed_M1", "killed_M4", "killed_M5_no_FIV",
          "killed_M5_not_on_shelf", "killed_M6_no_advance", "success"]
LABELS = {
    "exited_domain": "Domain exit", "killed_M1": "Ice at spawning (M1)",
    "killed_M4": "Calyptopis starvation (M4)", "killed_M5_no_FIV": "Under-developed (M5a)",
    "killed_M5_not_on_shelf": "Off-shelf (M5b)", "killed_M6_no_advance": "No winter ice (M6)",
    "success": "Recruitment success",
}
NAMES = {"88.3": "Amundsen Sea", "48.1": "Ant. Peninsula", "48.2": "South Orkney Is.",
         "48.3": "South Georgia", "48.4": "S. Sandwich Is.", "48.5": "Weddell Sea",
         "48.6N": "Bouvet N", "48.6S": "Bouvet S"}
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
    ap.add_argument("--dim", default="",
                    help="comma-separated subarea codes to grey out (slide reveal), e.g. 48.3,48.6N")
    args = ap.parse_args()
    dim = {c.strip() for c in args.dim.split(",") if c.strip()}
    suffix = ("_dim" + "-".join(sorted(dim))) if dim else ""
    out = args.out or str(here / f"timeseries_subarea_{args.by}{suffix}.png")

    ds = xr.open_dataset(args.aggregated)
    years, subs, season, names, share = season_means(ds, f"counts_{args.by}")
    colors = layer_colors()
    si = names.index("success")

    fig, axes = plt.subplots(2, 4, figsize=SLIDE, sharex=True, sharey=True)
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
        ax.set_title(f"{code}  {NAMES[code]}", fontsize=9, loc="left", pad=3,
                     color="0.6" if code in dim else "k")
        if code in dim:
            # Grey veil over the panel: data stays visible but recedes.
            ax.add_patch(mpl.patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                                               facecolor="white", alpha=0.85, zorder=10))
            for sp in ax.spines.values():
                sp.set_color("0.7")
            ax.tick_params(colors="0.6")
        ax.tick_params(labelsize=8)
    for ax in axes[-1]:
        ax.set_xticks(years[years % 10 == 0])
    axes[0, 0].set_xlim(years[0] - 0.6, years[-1] + 0.6)
    fig.supylabel("Share of particles released in subarea (%)", fontsize=9, x=0.01)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", ncol=4, fontsize=8,
               framealpha=1.0, bbox_to_anchor=(0.5, 0.0), handlelength=1.2,
               columnspacing=1.2)
    fig.tight_layout(rect=(0.02, 0.12, 1, 1))
    fig.savefig(out, dpi=300)
    print(f"Wrote {out}")
    if dim:
        return   # reveal variants only need the composition grid

    # ---- companion figure: success rate per subarea on one axis (synchrony).
    # Only the four subareas that carry the recruitment (90% of the domain's
    # interannual variance): 88.3, 48.1, 48.2, 48.4. 48.6S (8%) is left out so
    # the slide is consistent with the two-step pruning that precedes it.
    SUCCESS_SUBAREAS = ["88.3", "48.1", "48.2", "48.4"]
    out2 = out.replace("timeseries_subarea", "success_subarea")
    fig2, ax = plt.subplots(figsize=SLIDE)
    cmap = mpl.colormaps["tab10"]
    for n, code in enumerate(SUCCESS_SUBAREAS):
        k = subs.index(code)
        v = season[:, k, si]
        ax.plot(years, v, color=cmap(n), lw=1.4, marker="o", ms=4,
                markerfacecolor="white", markeredgecolor=cmap(n), markeredgewidth=1.2,
                label=f"{code}  {NAMES[code]}")
    ax.axvline(FORCING_STEP_YEAR - 0.5, color="0.5", ls=":", lw=0.8)
    ax.set_ylim(0, None)
    ax.set_xlim(years[0] - 0.6, years[-1] + 0.6)
    ax.set_xticks(years[years % 5 == 0])
    ax.set_xlabel("Spawning year")
    ax.set_ylabel("Season-mean recruitment success\n(% of particles released in subarea)")
    ax.grid(axis="y", color="#b0b0b0", alpha=0.5)
    h2, l2 = ax.get_legend_handles_labels()
    fig2.legend(h2, l2, loc="lower center", ncol=len(h2), fontsize=9,
                framealpha=1.0, bbox_to_anchor=(0.5, 0.0), handlelength=1.5,
                columnspacing=1.2)
    fig2.tight_layout(rect=(0, 0.09, 1, 1))
    fig2.savefig(out2, dpi=300)
    print(f"Wrote {out2}  (subareas {', '.join(SUCCESS_SUBAREAS)} only)")

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

    # Which constraint drives each subarea's interannual variability?
    # Per subarea: interannual sd of each outcome's share, and its correlation
    # with that subarea's success. Subareas with negligible success skipped.
    killed = [l for l in LAYERS if l.startswith("killed_")]
    print("\nPer-subarea interannual sd of outcome share (pts) | correlation with subarea success:")
    print(f"{'':>6s} " + " ".join(f"{LABELS[l].split(' (')[1][:-1]:>14s}" for l in killed))
    for code in PANEL_ORDER:
        k = subs.index(code)
        sv = season[:, k, si]
        if np.nanmean(sv) < 0.5:
            continue
        cells = []
        for l in killed:
            v = season[:, k, names.index(l)]
            r = np.corrcoef(sv, v)[0, 1] if np.nanstd(v) > 0 else np.nan
            cells.append(f"{np.nanstd(v, ddof=1):5.1f} | {r:+.2f}")
        print(f"{code:>6s} " + " ".join(f"{c:>14s}" for c in cells))

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
