"""
F2 plot: domain-wide interannual recruitment record, 1994-2025, NSIDC ice.

Reads data/aggregated.nc (per-(year, season_day, subarea, outcome) counts;
the domain is the sum over subareas, i.e. all releases) and draws one panel:

  - one stacked bar per spawning year, the season-mean composition of that
    year's releases (left axis, 0-100%): domain exit at the bottom as a grey
    floor, then M1, M4, M5a, M5b, M6 in the order the constraints act, and
    recruitment success on top; the seven layers sum to 100%;
  - the season-mean success line over the bars (right axis, 0-8%), with its
    32-year mean dashed.

The end-2018 forcing switch of GLORYS12 (ERA-Interim -> ERA5) is not marked:
on NSIDC ice only the circulation crosses it; the switch is shown on the
ice-product figure (F4).

Season mean = mean over the 120 release days of the per-day fraction (Feb 29
excluded upstream); censored particles are folded into M6, as in Paper 1.

Writes domain_timeseries.pdf and .png at 6.5 x 4.875 in and prints the
reference numbers: per-year shares, success mean/sd/min/max, ranking, 1994-2016 vs
2017-2025 means, and each outcome's interannual sd and r with success.

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
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "pdf.fonttype": 42,          # text stays text in the PDF
    "ps.fonttype": 42,
})

PAPER = (6.5, 4.875)             # letter text width, 4:3

# Layer order, bottom -> top, as Paper 1 Figure 3.
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
SPLIT_YEAR = 2017                # 1994-2016 fit / 2017-2025 test
SUCCESS_YMAX = 8.0               # right axis, %
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


def season_mean_shares(ds: xr.Dataset) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """(years, share[year, outcome] in %, outcome names), domain = all
    releases, censored folded into M6."""
    names = list(ds["outcome"].values.astype(str))
    counts = ds["counts_release"].sum("subarea").values.astype(float)   # (year, sd, outcome)
    total = ds["total"].values.astype(float)
    has = ds["has_data"].values

    ci, mi = names.index("censored"), names.index("killed_M6_no_advance")
    counts[:, :, mi] += counts[:, :, ci]
    counts[:, :, ci] = 0.0

    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(has[:, :, None], 100.0 * counts / np.maximum(total[:, :, None], 1), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        season = np.nanmean(frac, axis=1)                                 # (year, outcome)
    return ds["year"].values, season, names


def draw(years: np.ndarray, season: np.ndarray, names: list[str]) -> plt.Figure:
    succ = season[:, names.index("success")]
    colors = layer_colors()

    fig, ax = plt.subplots(figsize=PAPER)

    # Stacked composition, left axis.
    bottom = np.zeros_like(succ)
    for layer in LAYERS:
        vals = season[:, names.index(layer)]
        ax.bar(years, vals, bottom=bottom, width=0.8, color=colors[layer],
               edgecolor="none", label=LABELS[layer])
        bottom += vals
    ax.set_ylim(0, 100)
    ax.set_xlim(years[0] - 0.6, years[-1] + 0.6)
    ax.set_xticks(years[years % 5 == 0])
    ax.set_xlabel("Spawning year")
    ax.set_ylabel("Share of releases (%)")

    # Success line, right axis.
    ax2 = ax.twinx()
    halo = [withStroke(linewidth=3.2, foreground="white")]
    ax2.plot(years, succ, color="k", lw=1.4, marker="o", ms=3.5, mfc="white",
             mec="k", mew=1.0, zorder=6, path_effects=halo)
    ax2.axhline(succ.mean(), color="k", ls="--", lw=0.8, zorder=5)
    ax2.set_ylim(0, SUCCESS_YMAX)
    ax2.set_ylabel("Season-mean recruitment success (%)")

    # Legend below: success line, its mean, then the layers top to bottom.
    handles, labels = ax.get_legend_handles_labels()
    handles = [Line2D([], [], color="k", lw=1.4, marker="o", ms=3.5, mfc="white", mec="k"),
               Line2D([], [], color="k", ls="--", lw=0.8)] + handles[::-1]
    labels = ["Success (right axis)", f"32-year mean ({succ.mean():.1f}%)"] + labels[::-1]
    fig.legend(handles, labels, loc="lower center", ncol=3,
               bbox_to_anchor=(0.5, 0.0), framealpha=1.0,
               handlelength=1.4, columnspacing=1.5)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    return fig


def report(years: np.ndarray, season: np.ndarray, names: list[str]) -> None:
    succ = season[:, names.index("success")]
    n = succ.size

    print("\nSeason-mean outcome shares (%), censored folded into M6:")
    print(f"{'year':>6s} " + " ".join(f"{SHORT[l]:>8s}" for l in LAYERS) + f" {'sum':>8s}")
    for i, yr in enumerate(years):
        row = [season[i, names.index(l)] for l in LAYERS]
        print(f"{yr:>6d} " + " ".join(f"{v:8.2f}" for v in row) + f" {sum(row):8.2f}")

    order = np.argsort(-succ)
    print(f"\nSuccess (n = {n}): mean {succ.mean():.2f}%, sd {succ.std(ddof=1):.2f}%, "
          f"min {succ.min():.2f}% ({years[np.argmin(succ)]}), "
          f"max {succ.max():.2f}% ({years[np.argmax(succ)]})")
    print("Ranking, best to worst: " + ", ".join(f"{years[i]} {succ[i]:.2f}" for i in order))
    pre, post = succ[years < SPLIT_YEAR], succ[years >= SPLIT_YEAR]
    print(f"Mean 1994-{SPLIT_YEAR - 1} {pre.mean():.2f}% (n = {pre.size}); "
          f"{SPLIT_YEAR}-{years[-1]} {post.mean():.2f}% (n = {post.size})")

    print("\nInterannual sd of each outcome's share (pp) and r with success:")
    parts = []
    for l in LAYERS:
        if l == "success":
            continue
        v = season[:, names.index(l)]
        sd, r = v.std(ddof=1), np.corrcoef(succ, v)[0, 1]
        print(f"  {LABELS[l]:28s} mean {v.mean():6.2f}   sd {sd:5.2f}   r {r:+.2f}")
        if l != "exited_domain":
            parts.append(f"{SHORT[l]} {sd:.2f} | {r:+.2f}")

    print("\nMethodology section 4, domain line (NSIDC ice):")
    print(f"Domain: season-mean success {succ.mean():.2f} ± {succ.std(ddof=1):.2f}%; "
          f"{succ.min():.2f}% ({years[np.argmin(succ)]}) to {succ.max():.2f}% ({years[np.argmax(succ)]}); "
          f"mean 1994-{SPLIT_YEAR - 1} {pre.mean():.2f}%, {SPLIT_YEAR}-{years[-1]} {post.mean():.2f}%. "
          "Interannual sd of outcome shares and r with success: " + ", ".join(parts) + ".")


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregated", default=str(here / "data" / "aggregated.nc"))
    args = ap.parse_args()

    ds = xr.open_dataset(args.aggregated)
    sic = str(ds.attrs.get("sic_source", ""))
    if not sic.startswith(EXPECTED_SIC_SOURCE_PREFIX):
        raise ValueError(f"{args.aggregated} is not the NSIDC-ice aggregate (sic_source = {sic!r})")
    years, season, names = season_mean_shares(ds)
    if not np.allclose(season.sum(axis=1), 100.0):
        raise ValueError("season-mean shares do not sum to 100%")

    fig = draw(years, season, names)
    for ext in ("pdf", "png"):
        out = here / f"domain_timeseries.{ext}"
        fig.savefig(out, dpi=300)
        print(f"Wrote {out}")
    plt.close(fig)

    report(years, season, names)


if __name__ == "__main__":
    main()
