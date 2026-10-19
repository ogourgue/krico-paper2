"""
Ice-source test for the end-2018 GLORYS12 forcing change: the recruitment
classification run with GLORYS12 sea ice, with GLORYS12 sea ice binned onto
the NSIDC 25 km grid, and with NSIDC G02202 v6 sea ice, on the same
trajectories.

  (a) Season-mean recruitment success per spawning year under the three ice
      readings, on one axis, with the 2019 forcing step marked.
  (b) Per spawning year and outcome (success, M1, M5b, M6), in percentage
      points of released particles: solid, NSIDC minus GLORYS12-on-25-km,
      the product difference at equal resolution; dashed, GLORYS12-on-25-km
      minus native GLORYS12, the resolution and sampling difference. Their
      sum is the total NSIDC-minus-GLORYS12 difference.

The test reads as follows. The level of each difference is a product or
resolution gap and is not the point. What the forcing change would produce is
a change at 2019: if the reanalysis ice drifted relative to observations when
the atmosphere switched, the product difference steps there while the
resolution difference does not, since the grids do not change. The
circulation behind M5b is GLORYS12 in all three runs and is not tested here.

Domain-wide by default (sum of counts_release over subareas); --subarea CODE
restricts to the particles released in one subarea (88.3, 48.1, 48.2, 48.3,
48.4, 48.5, 48.6N, 48.6S). Season mean, censored folded into M6, F3 palette
and the slide figure size follow plot_domain.py.

Inputs:  ../timeseries/data/aggregated_subarea.nc         (GLORYS12 ice, production)
         data/aggregated_subarea_glorys12_25km.nc         (GLORYS12 ice on 25 km, aggregate_glorys12_25km.py)
         data/aggregated_subarea_nsidc.nc                 (NSIDC ice, aggregate_nsidc.py)
Output:  timeseries_ice_source[_SUBAREA].png + stdout table

The stdout ends with an ice-state check per outcome: the product gap depends
on how much ice there is, and the post-2018 years are low-ice years, so the
pre-2019 relation between the difference and the GLORYS12 level of the same
outcome is used to predict the post-2019 difference. A shift the prediction
does not account for, with residuals of one sign, is the forcing signature.
See plot_ice_source_subarea.py for the per-subarea version of panel (b).

Usage:
  python plot_ice_source.py [--subarea 48.2] [--out PATH]
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
    "font.size": 11,
})
SLIDE = (9.32, 3.74)

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
FORCING_STEP_YEAR = 2019
DIFF_LAYERS = ["success", "killed_M1", "killed_M5_not_on_shelf", "killed_M6_no_advance"]

HERE = Path(__file__).resolve().parent
FILES = {
    "GLORYS12": HERE.parent / "timeseries" / "data" / "aggregated_subarea.nc",
    "GLORYS12-25km": HERE / "data" / "aggregated_subarea_glorys12_25km.nc",
    "NSIDC": HERE / "data" / "aggregated_subarea_nsidc.nc",
}
STYLE = {
    "GLORYS12": dict(color="C2", ls="-", marker="o", mfc="white"),
    "GLORYS12-25km": dict(color="0.45", ls="-", marker="^", mfc="white"),
    "NSIDC": dict(color="C0", ls="-", marker="s", mfc="white"),
}
# The three differences, name -> (minuend, subtrahend)
DIFFERENCES = {
    "product": ("NSIDC", "GLORYS12-25km"),        # at equal resolution
    "resolution": ("GLORYS12-25km", "GLORYS12"),  # resolution and sampling
    "total": ("NSIDC", "GLORYS12"),
}


def layer_colors() -> dict[str, tuple]:
    colors = {"success": mpl.colors.to_rgba("C2"),
              "exited_domain": mpl.colors.to_rgba("0.7")}
    killed = [l for l in LAYERS if l.startswith("killed_")]
    cmap = mpl.colormaps["YlOrRd"]
    for layer, t in zip(killed, np.linspace(0.35, 0.85, len(killed))):
        colors[layer] = cmap(t)
    return colors


def season_mean_fractions(ds: xr.Dataset, subarea: str | None
                          ) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    (years, frac[year, outcome] in % of particles released, outcome names),
    censored folded into M6, from counts_release summed over subareas (or
    one subarea). The denominator is the particles released in the selection,
    so the subarea fractions are per-subarea success rates, as in
    plot_subarea.py.
    """
    names = list(ds["outcome"].values.astype(str))
    cr = ds["counts_release"]
    if subarea is not None:
        cr = cr.sel(subarea=subarea)
    else:
        cr = cr.sum(dim="subarea")
    counts = cr.values.astype(float).copy()                 # (year, sd, outcome)
    total = counts.sum(axis=2)
    has = ds["has_data"].values & (total > 0)

    ci, mi = names.index("censored"), names.index("killed_M6_no_advance")
    counts[:, :, mi] += counts[:, :, ci]
    counts[:, :, ci] = 0.0

    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(has[:, :, None], 100.0 * counts / np.maximum(total[:, :, None], 1), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        season = np.nanmean(frac, axis=1)
    return ds["year"].values, season, names


def ice_state_check(years: np.ndarray, level: np.ndarray, diff: np.ndarray,
                    step: int = FORCING_STEP_YEAR) -> dict:
    """
    Does the pre-step relation between the difference and the GLORYS12 level
    of the same outcome predict the post-step difference? Fit diff ~ level on
    the pre-step years, apply to the post-step levels, compare with the
    observed post-step differences. A product gap that merely depends on how
    much ice there is gives small post-step residuals; a change of the gap at
    the step gives residuals of one sign, large against the pre-step
    residual sd.
    """
    pre, post = years < step, years >= step
    slope, icpt = np.polyfit(level[pre], diff[pre], 1)
    r = np.corrcoef(level[pre], diff[pre])[0, 1]
    res_pre = diff[pre] - (slope * level[pre] + icpt)
    res_post = diff[post] - (slope * level[post] + icpt)
    return dict(slope=slope, r=r, predicted=float(np.mean(slope * level[post] + icpt)),
                observed=float(diff[post].mean()), res_mean=float(res_post.mean()),
                res_sd_pre=float(res_pre.std(ddof=1)),
                n_same_sign=int(max((res_post > 0).sum(), (res_post < 0).sum())),
                n_post=int(post.sum()))


def differences(runs: dict) -> dict:
    return {k: runs[a] - runs[b] for k, (a, b) in DIFFERENCES.items()}


def print_shift_table(years: np.ndarray, runs: dict, diff: np.ndarray, names: list[str],
                      scope: str, which: str = "total") -> None:
    a_name, b_name = DIFFERENCES[which]
    pre = years < FORCING_STEP_YEAR
    post = ~pre
    print(f"\n{a_name} minus {b_name} ({which}), {scope}: mean (sd) over years, "
          f"pre-{FORCING_STEP_YEAR} n={pre.sum()} vs {FORCING_STEP_YEAR}-{years[-1]} n={post.sum()}; "
          f"Welch t for a change at the step; r between the two series; ice-state check")
    for l in DIFF_LAYERS:
        li = names.index(l)
        a, b = diff[pre, li], diff[post, li]
        se = np.sqrt(a.var(ddof=1) / a.size + b.var(ddof=1) / b.size)
        t = (b.mean() - a.mean()) / se if se > 0 else np.nan
        r = np.corrcoef(runs[a_name][:, li], runs[b_name][:, li])[0, 1]
        c = ice_state_check(years, runs["GLORYS12"][:, li], diff[:, li])
        print(f"  {LABELS[l]:28s} pre {a.mean():+5.2f} ({a.std(ddof=1):4.2f})  "
              f"post {b.mean():+5.2f} ({b.std(ddof=1):4.2f})  shift {b.mean() - a.mean():+5.2f} pp  "
              f"t = {t:+5.2f}  r = {r:.3f}")
        print(f"  {'':28s} state check: pre-step diff vs level r = {c['r']:+.2f}; "
              f"post diff predicted from level {c['predicted']:+5.2f}, observed {c['observed']:+5.2f}; "
              f"residual {c['res_mean']:+5.2f} = {c['res_mean'] / c['res_sd_pre']:+.1f} pre sd, "
              f"{c['n_same_sign']}/{c['n_post']} of one sign")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subarea", default=None,
                    help="restrict to particles released in this subarea (default: domain)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    tag = f"_{args.subarea}" if args.subarea else ""
    out = Path(args.out) if args.out else HERE / f"timeseries_ice_source{tag}.png"

    runs = {}
    for name, path in FILES.items():
        if not path.is_file():
            raise SystemExit(f"missing {path}")
        with xr.open_dataset(path) as ds:
            years, season, names = season_mean_fractions(ds, args.subarea)
            runs[name] = season
            print(f"{name:9s} {path.name}: sic_source = {ds.attrs.get('sic_source', '?')}")
    diffs = differences(runs)                               # each (year, outcome), pp
    colors = layer_colors()
    scope = f"released in {args.subarea}" if args.subarea else "domain"

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=SLIDE, gridspec_kw={"wspace": 0.3})

    # ---- (a) success under both ice readings
    si = names.index("success")
    for name, season in runs.items():
        ax_a.plot(years, season[:, si], ms=5, lw=1.3, label=f"{name} ice", **STYLE[name])
    ax_a.axvline(FORCING_STEP_YEAR - 0.5, color="0.5", ls=":", lw=0.9)
    ymax = max(np.nanmax(season[:, si]) for season in runs.values())
    ax_a.set_ylim(0, 1.3 * ymax)            # headroom for the legend
    y1 = ax_a.get_ylim()[1]
    ax_a.text(FORCING_STEP_YEAR - 0.8, 0.03 * y1, "ERA-Interim", fontsize=8, color="0.4", ha="right")
    ax_a.text(FORCING_STEP_YEAR - 0.2, 0.03 * y1, "ERA5", fontsize=8, color="0.4")
    ax_a.set_ylabel("Season-mean success (%)")
    ax_a.set_xlabel("Spawning year")
    ax_a.set_title(scope, fontsize=10, loc="left")
    ax_a.legend(frameon=False, fontsize=8, loc="upper left", ncol=3, columnspacing=1.0,
                handlelength=1.6)
    ax_a.grid(axis="y", lw=0.4, alpha=0.5)

    # ---- (b) product difference (solid) and resolution difference (dashed) per outcome
    for layer in DIFF_LAYERS:
        li = names.index(layer)
        ax_b.plot(years, diffs["product"][:, li], color=colors[layer], lw=1.3, marker="o",
                  ms=3.5, label=LABELS[layer])
        ax_b.plot(years, diffs["resolution"][:, li], color=colors[layer], lw=1.0, ls="--",
                  marker="o", ms=2, mfc="white")
    ax_b.axhline(0, color="0.3", lw=0.8)
    ax_b.axvline(FORCING_STEP_YEAR - 0.5, color="0.5", ls=":", lw=0.9)
    ax_b.set_ylabel("Difference (pp)")
    ax_b.set_xlabel("Spawning year")
    ax_b.set_title("solid: NSIDC − GLORYS12-25km (product)   dashed: GLORYS12-25km − GLORYS12 (resolution)",
                   fontsize=7.5, loc="left", color="0.3")
    ax_b.grid(axis="y", lw=0.4, alpha=0.5)
    handles, labels = ax_b.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9, ncol=4,
               loc="lower center", bbox_to_anchor=(0.5, -0.08))

    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Wrote {out}")

    # ---- numbers
    print(f"\nSeason-mean shares (% of released), {scope}, censored folded into M6; "
          f"G = GLORYS12, G25 = GLORYS12 on 25 km, N = NSIDC")
    head = "year  " + "  ".join(f"{LABELS[l][:16]:>16s}" for l in DIFF_LAYERS)
    print(head)
    print("      " + "  ".join(f"{'G / G25 / N':>16s}" for _ in DIFF_LAYERS))
    for k, y in enumerate(years):
        cells = []
        for l in DIFF_LAYERS:
            li = names.index(l)
            cells.append(f"{runs['GLORYS12'][k, li]:4.1f}/{runs['GLORYS12-25km'][k, li]:4.1f}"
                         f"/{runs['NSIDC'][k, li]:4.1f}")
        print(f"{y}  " + "  ".join(f"{c:>16s}" for c in cells))

    for which in ("product", "resolution", "total"):
        print_shift_table(years, runs, diffs[which], names, scope, which)
    print("\nThe level of each difference is a product or resolution gap. A shift at the step in the "
          "product difference that the ice-state check does not predict, with no shift in the "
          "resolution difference, is the forcing signature; t is indicative only (n = 25 vs 7).")


if __name__ == "__main__":
    main()
