"""
F3 plot: per-subarea interannual recruitment record, 1994-2025, NSIDC ice.

Reads data/aggregated.nc (per-(year, season_day, subarea, outcome) counts by
release position) and draws four panels, one per recruiting subarea (88.3,
48.1, 48.2, 48.4), each built as F2's single panel:

  - one stacked bar per spawning year, the season-mean composition of the
    particles released in that subarea (left axis, 0-100% of the subarea's
    own releases): domain exit at the bottom as a grey floor, then M1, M4,
    M5a, M5b, M6 in the order the constraints act, and recruitment success
    on top; the seven layers sum to 100%;
  - the season-mean success line over the bars (right axis, 0-30%, shared
    by the four panels so that rates compare across subareas), with its
    32-year mean dashed.

Per-subarea rates use the subarea's own releases as denominator (Paper 2
convention). Season mean = mean over the 120 release days of the per-day
fraction (Feb 29 excluded upstream); censored particles are folded into M6,
as in Paper 1. The end-2018 forcing switch is not marked (shown on F4).

Writes subarea_record.pdf and .png at 6.5 x 5.9 in (2 x 2 panels) and prints
the per-subarea reference numbers: season-mean success per subarea and year;
mean, sd and share of the domain's interannual variance for all eight
subareas; each outcome's interannual sd and r with the subarea's success
for the recruiting four and 48.6S; synchrony between the recruiting four;
and the survivor partition M5b / (M5b + success) per recruiting subarea
with its r with success and with the M1 share.

Usage:  python plot.py [--aggregated PATH]
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.lines import Line2D
from matplotlib.patheffects import withStroke

mpl.rcParams.update({
    "font.family": "Arial",
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 8.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "pdf.fonttype": 42,          # text stays text in the PDF
    "ps.fonttype": 42,
})

PAPER = (6.5, 5.9)               # letter text width; 2 x 2 panels at ~4:3 plus the legend

# Layer order, bottom -> top, as Paper 1 Figure 3 and F2.
LAYERS = [
    "exited_domain",
    "killed_M1",
    "killed_M4",
    "killed_M5_no_FIV",
    "killed_M5_not_on_shelf",
    "killed_M6_no_advance",
    "success",
]
LABELS = {
    "exited_domain":          "Domain exit",
    "killed_M1":              "Ice at spawning (M1)",
    "killed_M4":              "Calyptopis starvation (M4)",
    "killed_M5_no_FIV":       "Under-developed (M5a)",
    "killed_M5_not_on_shelf": "Off-shelf (M5b)",
    "killed_M6_no_advance":   "No winter ice (M6)",
    "success":                "Recruitment success",
}
SHORT = {"killed_M1": "M1", "killed_M4": "M4", "killed_M5_no_FIV": "M5a",
         "killed_M5_not_on_shelf": "M5b", "killed_M6_no_advance": "M6",
         "exited_domain": "exit", "success": "success"}

NAMES = {"88.3": "Amundsen Sea", "48.1": "Antarctic Peninsula", "48.2": "South Orkney Islands",
         "48.3": "South Georgia", "48.4": "South Sandwich Islands", "48.5": "Weddell Sea",
         "48.6N": "Bouvet N", "48.6S": "Bouvet S"}
ALL_SUBAREAS = ["88.3", "48.1", "48.2", "48.3", "48.4", "48.5", "48.6N", "48.6S"]
PANELS = ["88.3", "48.1", "48.2", "48.4"]          # the four recruiting subareas (P2-D03)
TABLE2 = PANELS + ["48.6S"]                        # rows of the outcome sd | r table
PANEL_LABELS = "abcd"

SUCCESS_YMAX = 30.0              # right axis, %, shared by the four panels
EXPECTED_SIC_SOURCE_PREFIX = "NSIDC G02202 v6"


def layer_colors() -> dict[str, tuple]:
    """Paper 1 Figure 3 palette: C2 green for success, YlOrRd gradient for
    the constraints (lightest = earliest), grey for domain exit."""
    colors = {"success": mpl.colors.to_rgba("C2"),
              "exited_domain": mpl.colors.to_rgba("0.7")}
    killed = [l for l in LAYERS if l.startswith("killed_")]
    cmap = mpl.colormaps["YlOrRd"]
    for layer, t in zip(killed, np.linspace(0.35, 0.85, len(killed))):
        colors[layer] = cmap(t)
    return colors


def season_mean_shares(ds: xr.Dataset):
    """
    Returns (years, subareas, season[year, subarea, outcome] in % of the
    subarea's own releases, outcome names, domain[year, outcome] in % of all
    releases, release_share[subarea]). Censored folded into M6.
    """
    names = list(ds["outcome"].values.astype(str))
    subs = list(ds["subarea"].values.astype(str))
    c = ds["counts_release"].values.astype(float).copy()      # (year, sd, sub, outcome)
    total = ds["total"].values.astype(float)                   # (year, sd)
    has = ds["has_data"].values

    ci, mi = names.index("censored"), names.index("killed_M6_no_advance")
    c[..., mi] += c[..., ci]
    c[..., ci] = 0.0

    denom = c.sum(axis=3)                                      # releases per (year, sd, sub)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where((has[:, :, None] & (denom > 0))[..., None],
                        100.0 * c / np.maximum(denom[..., None], 1), np.nan)
        dfrac = np.where(has[:, :, None],
                         100.0 * c.sum(axis=2) / np.maximum(total[:, :, None], 1), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        season = np.nanmean(frac, axis=1)                      # (year, sub, outcome)
        domain = np.nanmean(dfrac, axis=1)                     # (year, outcome), = F2's series
    release_share = denom.sum(axis=(0, 1)) / total.sum()       # fraction of all releases per sub
    return ds["year"].values, subs, season, names, domain, release_share


def draw(years, subs, season, names) -> plt.Figure:
    colors = layer_colors()
    si = names.index("success")
    fig, axes = plt.subplots(2, 2, figsize=PAPER, sharex=True, sharey=True)
    halo = [withStroke(linewidth=3.2, foreground="white")]
    right_axes = []

    for ax, code, lab in zip(axes.ravel(), PANELS, PANEL_LABELS):
        k = subs.index(code)
        succ = season[:, k, si]

        bottom = np.zeros_like(succ)
        for layer in LAYERS:
            vals = season[:, k, names.index(layer)]
            ax.bar(years, vals, bottom=bottom, width=0.8, color=colors[layer],
                   edgecolor="none", label=LABELS[layer])
            bottom += vals
        ax.set_ylim(0, 100)
        ax.set_xlim(years[0] - 0.6, years[-1] + 0.6)
        ax.set_xticks(years[years % 5 == 0])
        ax.set_title(f"({lab}) {code}  {NAMES[code]}", loc="left", pad=3)

        ax2 = ax.twinx()
        ax2.plot(years, succ, color="k", lw=1.2, marker="o", ms=3.0, mfc="white",
                 mec="k", mew=0.9, zorder=6, path_effects=halo)
        ax2.axhline(succ.mean(), color="k", ls="--", lw=0.8, zorder=5)
        ax2.set_ylim(0, SUCCESS_YMAX)
        ax2.tick_params(labelsize=8)
        right_axes.append(ax2)

    # Axis labels once per side; inner tick labels off.
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of releases (%)")
    for ax in axes[-1, :]:
        ax.set_xlabel("Spawning year")
    for ax2, (i, j) in zip(right_axes, [(0, 0), (0, 1), (1, 0), (1, 1)]):
        if j == 1:
            ax2.set_ylabel("Season-mean recruitment success (%)")
        else:
            ax2.tick_params(labelright=False)

    # One legend below: success line, its mean, then the layers top to bottom.
    handles, labels = axes[0, 0].get_legend_handles_labels()
    handles = [Line2D([], [], color="k", lw=1.2, marker="o", ms=3.0, mfc="white", mec="k"),
               Line2D([], [], color="k", ls="--", lw=0.8)] + handles[::-1]
    labels = ["Success (right axis)", "32-year mean"] + labels[::-1]
    fig.legend(handles, labels, loc="lower center", ncol=3,
               bbox_to_anchor=(0.5, 0.0), framealpha=1.0,
               handlelength=1.4, columnspacing=1.5)
    fig.tight_layout(rect=(0, 0.11, 1, 1), h_pad=1.0, w_pad=0.6)
    return fig


def report(years, subs, season, names, domain, release_share) -> None:
    si = names.index("success")
    m5b = names.index("killed_M5_not_on_shelf")
    killed = [l for l in LAYERS if l.startswith("killed_")]
    n = years.size
    S = np.stack([season[:, subs.index(c), si] for c in ALL_SUBAREAS], axis=1)   # (year, sub)

    print("\nSeason-mean success (%) by release subarea, of the subarea's own releases:")
    print(f"{'year':>6s} " + " ".join(f"{c:>7s}" for c in ALL_SUBAREAS))
    for i, yr in enumerate(years):
        print(f"{yr:>6d} " + " ".join(f"{S[i, j]:7.2f}" for j in range(S.shape[1])))
    print(f"{'mean':>6s} " + " ".join(f"{S[:, j].mean():7.2f}" for j in range(S.shape[1])))
    print(f"{'sd':>6s} " + " ".join(f"{S[:, j].std(ddof=1):7.2f}" for j in range(S.shape[1])))

    for code in PANELS:
        s = season[:, subs.index(code), si]
        o = np.argsort(-s)
        print(f"{code}: mean {s.mean():.2f}%, sd {s.std(ddof=1):.2f}%, "
              f"min {s.min():.2f}% ({years[np.argmin(s)]}), max {s.max():.2f}% ({years[np.argmax(s)]}); "
              f"best five {', '.join(str(years[i]) for i in o[:5])}; "
              f"worst five {', '.join(str(years[i]) for i in o[-5:][::-1])}")

    # Share of the domain's interannual variance: domain success = sum over
    # subareas of (release share x subarea rate), the release shares being
    # constant across years to within rounding; cov(term_k, domain) / var(domain).
    dom = domain[:, si]
    terms = np.stack([release_share[subs.index(c)] * S[:, j] for j, c in enumerate(ALL_SUBAREAS)], axis=1)
    cov = np.array([np.cov(terms[:, j], dom)[0, 1] for j in range(terms.shape[1])])
    var_share = 100 * cov / dom.var(ddof=1)
    resid = np.abs(terms.sum(axis=1) - dom).max()
    print(f"\nDomain series check: F2's success {dom.mean():.2f} ± {dom.std(ddof=1):.2f}%; "
          f"the eight subarea terms reproduce it to {resid:.3f} pp (remainder = releases outside any subarea, "
          f"{100 * release_share[subs.index('outside')]:.2f}% of releases).")
    print(f"Share of domain variance summed over the eight subareas: {var_share.sum():.1f}%")

    print("\nMethodology section 4, table 1 (NSIDC ice):")
    print("| | " + " | ".join(ALL_SUBAREAS) + " |")
    print("|---|" + "---:|" * len(ALL_SUBAREAS))
    print("| Mean success (%) | " + " | ".join(f"{S[:, j].mean():.2f}" for j in range(S.shape[1])) + " |")
    print("| sd | " + " | ".join(f"{S[:, j].std(ddof=1):.2f}" for j in range(S.shape[1])) + " |")
    print("| Share of domain variance | " + " | ".join(f"{v:.1f}%" for v in var_share) + " |")
    four = sum(var_share[ALL_SUBAREAS.index(c)] for c in PANELS)
    print(f"The four recruiting subareas carry {four:.0f}% of the domain variance.")

    print("\nMethodology section 4, table 2: interannual sd of each outcome share (pp of the "
          "subarea's releases) | r with the subarea's success:")
    print("| | " + " | ".join(SHORT[l] for l in killed) + " |")
    print("|---|" + "---|" * len(killed))
    for code in TABLE2:
        k = subs.index(code)
        sv = season[:, k, si]
        cells = []
        for l in killed:
            v = season[:, k, names.index(l)]
            r = np.corrcoef(sv, v)[0, 1] if v.std() > 0 else np.nan
            cells.append(f"{v.std(ddof=1):.1f} \\| {r:+.2f}")
        print(f"| {code} | " + " | ".join(cells) + " |")
    print("Mean shares (%) behind table 2:")
    for code in TABLE2:
        k = subs.index(code)
        print(f"  {code:6s} " + "  ".join(f"{SHORT[l]} {season[:, k, names.index(l)].mean():5.1f}"
                                          for l in killed + ['exited_domain']))

    print("\nSynchrony: interannual correlation of success between the recruiting subareas:")
    R = np.corrcoef(np.stack([season[:, subs.index(c), si] for c in PANELS], axis=1).T)
    print(f"{'':>6s} " + " ".join(f"{c:>6s}" for c in PANELS))
    for a, c in enumerate(PANELS):
        print(f"{c:>6s} " + " ".join(f"{R[a, b]:+6.2f}" for b in range(len(PANELS))))
    off = R[np.triu_indices(len(PANELS), k=1)]
    pairs = [(PANELS[a], PANELS[b]) for a in range(len(PANELS)) for b in range(a + 1, len(PANELS))]
    print(f"Range {off.min():+.2f} to {off.max():+.2f}; "
          f"most negative {pairs[np.argmin(off)]}, most positive {pairs[np.argmax(off)]}")

    print("\nSurvivor partition M5b / (M5b + success), ratio of the season-mean shares, per year:")
    print(f"{'year':>6s} " + " ".join(f"{c:>7s}" for c in PANELS))
    P = np.stack([season[:, subs.index(c), m5b] / (season[:, subs.index(c), m5b] + season[:, subs.index(c), si])
                  for c in PANELS], axis=1)
    for i, yr in enumerate(years):
        print(f"{yr:>6d} " + " ".join(f"{P[i, j]:7.3f}" for j in range(P.shape[1])))
    m1 = names.index("killed_M1")
    print("Mean | sd | r with the subarea's success | r with its M1 share | "
          "r of the M5b share itself with success, for comparison:")
    for j, code in enumerate(PANELS):
        k = subs.index(code)
        r_p = np.corrcoef(P[:, j], season[:, k, si])[0, 1]
        r_1 = np.corrcoef(P[:, j], season[:, k, m1])[0, 1]
        r_m = np.corrcoef(season[:, k, m5b], season[:, k, si])[0, 1]
        print(f"  {code:6s} {P[:, j].mean():.3f} | {P[:, j].std(ddof=1):.3f} | {r_p:+.2f} | {r_1:+.2f} | {r_m:+.2f}")


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregated", default=str(here / "data" / "aggregated.nc"))
    args = ap.parse_args()

    ds = xr.open_dataset(args.aggregated)
    sic = str(ds.attrs.get("sic_source", ""))
    if not sic.startswith(EXPECTED_SIC_SOURCE_PREFIX):
        raise ValueError(f"{args.aggregated} is not the NSIDC-ice aggregate (sic_source = {sic!r})")
    years, subs, season, names, domain, release_share = season_mean_shares(ds)
    for code in PANELS:
        if not np.allclose(season[:, subs.index(code), :].sum(axis=1), 100.0):
            raise ValueError(f"season-mean shares of {code} do not sum to 100%")
    if not np.allclose(domain.sum(axis=1), 100.0):
        raise ValueError("domain season-mean shares do not sum to 100%")

    fig = draw(years, subs, season, names)
    for ext in ("pdf", "png"):
        out = here / f"subarea_record.{ext}"
        fig.savefig(out, dpi=300)
        print(f"Wrote {out}")
    plt.close(fig)

    report(years, subs, season, names, domain, release_share)


if __name__ == "__main__":
    main()
