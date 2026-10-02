"""
Paper 2, Figure 1 (domain-wide draft): interannual recruitment time series.

Reads the per-(year, season_day, outcome) counts already produced for Paper 1
(krico-paper1/F3_outcome_composition/data/aggregated.nc, committed to that
repo) and draws two panels sharing the year axis:

  (a) Season-mean recruitment success rate per spawning year, with the
      32-year mean and the 2014 minimum / 2024 maximum annotated, and the
      end-2018 GLORYS12 forcing step (ERA-Interim -> ERA5) marked.
  (b) Season-mean outcome composition per spawning year as stacked bars,
      same layer order and palette as Paper 1 Figure 3 (domain exit at the
      bottom, M1 -> M6 in order of action, success on top).

Season mean = mean over the 120 release days of each year's per-day fraction
(Feb 29 excluded upstream), which is the quantity Paper 1 calls "season-mean
success". Censored is folded into M6, as everywhere in Paper 1.

No HPC access needed. Usage:

  python plot_domain.py [--aggregated PATH] [--out PATH]

Default input: data/aggregated_domain.nc, a verbatim copy of
krico-paper1 v2.1.0 F3_outcome_composition/data/aggregated.nc (see data/PROVENANCE.md).
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

mpl.rcParams.update({
    "font.family": "Arial",
    "font.size": 9,
})

# Layer order bottom -> top, identical to Paper 1 F3.
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
FORCING_STEP_YEAR = 2019   # first spawning year whose season straddles the ERA5 switch


def layer_colors() -> dict[str, tuple]:
    colors = {"success": mpl.colors.to_rgba("C2"),
              "exited_domain": mpl.colors.to_rgba("0.7")}
    killed = [l for l in LAYERS if l.startswith("killed_")]
    cmap = mpl.colormaps["YlOrRd"]
    for layer, t in zip(killed, np.linspace(0.35, 0.85, len(killed))):
        colors[layer] = cmap(t)
    return colors


def season_mean_fractions(ds: xr.Dataset) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (years, frac[year, outcome] in %, outcome names) with censored folded into M6."""
    names = list(ds["outcome"].values.astype(str))
    counts = ds["counts"].values.astype(float).copy()   # (year, sd, outcome)
    total = ds["total"].values.astype(float)
    has = ds["has_data"].values

    ci, mi = names.index("censored"), names.index("killed_M6_no_advance")
    counts[:, :, mi] += counts[:, :, ci]
    counts[:, :, ci] = 0.0

    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(has[:, :, None], 100.0 * counts / np.maximum(total[:, :, None], 1), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        season = np.nanmean(frac, axis=1)                 # (year, outcome)
    return ds["year"].values, season, names


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregated",
                    default=str(here / "data" / "aggregated_domain.nc"))
    ap.add_argument("--out", default=str(here / "timeseries_domain.png"))
    args = ap.parse_args()

    ds = xr.open_dataset(args.aggregated)
    years, season, names = season_mean_fractions(ds)
    succ = season[:, names.index("success")]
    colors = layer_colors()

    fig, (ax_a, ax_b) = plt.subplots(2, 1, figsize=(6.5, 6.5), sharex=True,
                                     gridspec_kw={"height_ratios": [1, 1.25]})

    # ---- (a) success time series
    ax_a.plot(years, succ, color="C2", marker="o", ms=3.5, lw=1.2, zorder=3)
    ax_a.axhline(succ.mean(), color="C2", ls="--", lw=0.8, alpha=0.7,
                 label=f"32-year mean ({succ.mean():.1f}%)")
    for yr, va in ((years[np.argmin(succ)], "top"), (years[np.argmax(succ)], "bottom")):
        v = succ[years == yr][0]
        ax_a.annotate(f"{yr}: {v:.1f}%", (yr, v), textcoords="offset points",
                      xytext=(0, -8 if va == "top" else 6), ha="center", va=va, fontsize=8)
    ax_a.axvline(FORCING_STEP_YEAR - 0.5, color="0.5", ls=":", lw=0.9)
    ax_a.text(FORCING_STEP_YEAR - 0.6, 0.3, "ERA-Interim | ERA5",
              fontsize=7, color="0.4", va="bottom", ha="center")
    ax_a.set_ylabel("Season-mean recruitment success (%)")
    ax_a.set_ylim(0, None)
    ax_a.grid(axis="y", color="#b0b0b0", alpha=0.5)
    ax_a.legend(loc="upper left", framealpha=1.0, fontsize=8)
    ax_a.text(0.01, 0.98, "(a)", transform=ax_a.transAxes, va="top", ha="left",
              fontweight="bold")

    # ---- (b) stacked composition per year
    bottom = np.zeros_like(succ)
    for layer in LAYERS:
        vals = season[:, names.index(layer)]
        ax_b.bar(years, vals, bottom=bottom, width=0.8, color=colors[layer],
                 edgecolor="none", label=LABELS[layer])
        bottom += vals
    ax_b.axvline(FORCING_STEP_YEAR - 0.5, color="0.5", ls=":", lw=0.9)
    ax_b.set_ylim(0, 100)
    ax_b.set_ylabel("Season-mean share of particles (%)")
    ax_b.set_xlabel("Spawning year")
    ax_b.set_xticks(years[::2])
    ax_b.tick_params(axis="x", rotation=90)
    ax_b.set_xlim(years[0] - 0.6, years[-1] + 0.6)
    handles, labels = ax_b.get_legend_handles_labels()
    ax_b.legend(handles[::-1], labels[::-1], loc="center left", bbox_to_anchor=(1.01, 0.5),
                framealpha=1.0, fontsize=7.5)
    ax_b.text(0.01, 0.98, "(b)", transform=ax_b.transAxes, va="top", ha="left",
              fontweight="bold", color="white",
              bbox=dict(facecolor="0.2", alpha=0.6, pad=1.5, edgecolor="none"))

    fig.tight_layout()
    fig.savefig(args.out, dpi=300, bbox_inches="tight")
    print(f"Wrote {args.out}")

    # ---- numbers for the meeting
    print("\nSeason-mean outcome shares (%), censored folded into M6:")
    print(f"{'year':>6s} " + " ".join(f"{LABELS[l].split(' (')[0][:12]:>12s}" for l in LAYERS))
    for i, yr in enumerate(years):
        print(f"{yr:>6d} " + " ".join(f"{season[i, names.index(l)]:12.2f}" for l in LAYERS))
    print(f"\nSuccess: mean {succ.mean():.2f}%, sd {succ.std(ddof=1):.2f}%, "
          f"min {succ.min():.2f}% ({years[np.argmin(succ)]}), "
          f"max {succ.max():.2f}% ({years[np.argmax(succ)]})")
    pre, post = succ[years < 2017], succ[years >= 2017]
    print(f"Pre-2017 mean {pre.mean():.2f}% (n={pre.size}); "
          f"2017-2025 mean {post.mean():.2f}% (n={post.size})")

    # Which outcome co-varies with success across years? (sign of the anomaly)
    print("\nCorrelation of each outcome's season-mean share with success (n=32):")
    for l in LAYERS:
        if l == "success":
            continue
        r = np.corrcoef(succ, season[:, names.index(l)])[0, 1]
        sd = season[:, names.index(l)].std(ddof=1)
        print(f"  {LABELS[l]:28s} r = {r:+.2f}   interannual sd = {sd:.2f} pts")


if __name__ == "__main__":
    main()
