"""
FS1 plot: the recruitment classification under three sea-ice readings,
spawning years 1994-2025, whole domain.

Reads data/aggregated_glorys12.nc, data/aggregated_glorys12_25km.nc and
data/aggregated_nsidc.nc (per-(year, season_day, subarea, outcome) counts
from the same trajectories classified with GLORYS12 ice on its native grid,
GLORYS12 ice binned onto the NSIDC 25 km grid, and NSIDC G02202 v6 ice) and
draws two panels:

  (a) season-mean recruitment success per spawning year under the three
      readings, on one axis;
  (b) per spawning year and outcome (success, M1, M4, M5a, M5b, M6), in
      percentage points of all particles released, NSIDC minus
      GLORYS12-25km: the product difference at equal grid and sampling;
  (c) the same for GLORYS12-25km minus GLORYS12: the resolution and
      sampling difference, on the same axis as (b). The sum of (b) and (c)
      is the total NSIDC-minus-GLORYS12 difference.

The end-2018 switch of the GLORYS12 atmospheric forcing (ERA-Interim to
ERA5) is marked between spawning years 2018 and 2019 on both panels.

Season mean = mean over the 120 release days of the per-day fraction (Feb 29
excluded upstream); censored particles are folded into M6, as in Paper 1.
Domain = counts summed over release subareas, in % of all releases.

Writes ice_product.pdf and .png at 6.5 x 8.0 in (three full-width panels) and prints the numbers the
figure supports: season-mean success and M1 share per year under the three
readings; for each of the three differences (product, resolution, total) and
each outcome, the pre-2019 and 2019-2025 mean difference, the shift between
them, the correlation of the two readings, and the ice-state check; the
decomposition of the total shift into product and resolution; and the
32-year totals per outcome under each reading.

The ice-state check asks whether the shift at 2019 is explained by the ice
there being less: the pre-2019 relation between the difference and the
GLORYS12 level of the same outcome is fitted and applied to the post-2019
levels; the mean residual of the observed post-2019 difference from that
prediction, in units of the pre-2019 residual sd, with the count of
post-2019 residuals of one sign, is the shift the ice state does not
account for.

Usage:  python plot.py [--data DIR]
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
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 8.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "pdf.fonttype": 42,          # text stays text in the PDF
    "ps.fonttype": 42,
})

PAPER = (6.5, 8.0)               # letter text width; three full-width panels within one page
OUTFILE = "ice_product"

# The three readings, in the order they are drawn and printed, with the
# sic_source each aggregate must carry (written by aggregate.py).
READINGS = {
    "glorys12":      dict(label="GLORYS12",       short="G",   sic_prefix="GLORYS12"),
    "glorys12_25km": dict(label="GLORYS12-25km",  short="G25", sic_prefix="GLORYS12v1 ice binned onto the NSIDC"),
    "nsidc":         dict(label="NSIDC",          short="N",   sic_prefix="NSIDC G02202 v6"),
}
LEGEND_A = ["nsidc", "glorys12", "glorys12_25km"]   # the paper's record first
MARKER = dict(marker="o", ms=4.5, mfc="white", mew=1.0)   # between the default (6, 1) and F2/F3 (3, 0.9)
STYLE = {   # panel (a): the paper's record in black, the two GLORYS12 readings in grey, the 25 km one dashed
    "nsidc":         dict(color="k",   ls="-",  zorder=5),
    "glorys12":      dict(color="0.5", ls="-",  zorder=3),
    "glorys12_25km": dict(color="0.5", ls="--", zorder=4),
}
# The three differences, name -> (minuend, subtrahend).
DIFFERENCES = {
    "product":    ("nsidc", "glorys12_25km"),        # same grid and sampling, only the ice values differ
    "resolution": ("glorys12_25km", "glorys12"),     # same ice, grid and sampling differ
    "total":      ("nsidc", "glorys12"),
}
DIFF_LABEL = {"product": "NSIDC − GLORYS12-25km (product)",
              "resolution": "GLORYS12-25km − GLORYS12 (resolution)",
              "total": "NSIDC − GLORYS12 (total)"}

# Outcomes drawn in (b) and (c), success first then the constraints in the
# order they act, in the matplotlib colour cycle. Domain exit is not drawn
# (its difference is below 0.03 pp); censored is folded into M6.
OUTCOMES = ["success", "killed_M1", "killed_M4", "killed_M5_no_FIV",
            "killed_M5_not_on_shelf", "killed_M6_no_advance"]
LABELS = {
    "success":                "Recruitment success",
    "killed_M1":              "Ice at spawning (M1)",
    "killed_M4":              "Calyptopis starvation (M4)",
    "killed_M5_no_FIV":       "Under-developed (M5a)",
    "killed_M5_not_on_shelf": "Off-shelf (M5b)",
    "killed_M6_no_advance":   "No winter ice (M6)",
}
SHORT = {"success": "success", "killed_M1": "M1", "killed_M4": "M4", "killed_M5_no_FIV": "M5a",
         "killed_M5_not_on_shelf": "M5b", "killed_M6_no_advance": "M6"}
COLOR = {layer: f"C{i}" for i, layer in enumerate(OUTCOMES)}

FORCING_STEP_YEAR = 2019         # first spawning year on ERA5 (2019 straddles the switch)
SUCCESS_YMAX = 8.0               # (a), %, as F2's success axis
DIFF_YLIM = 5.0                  # (b), pp, symmetric


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_readings(data_dir: Path) -> dict[str, xr.Dataset]:
    """Open the three aggregates and check they are the readings they claim
    to be, on the same years, subareas, outcomes and releases."""
    runs = {}
    for key, spec in READINGS.items():
        path = data_dir / f"aggregated_{key}.nc"
        ds = xr.open_dataset(path)
        sic = str(ds.attrs.get("sic_source", ""))
        src = str(ds.attrs.get("ice_source", ""))
        if src != key or not sic.startswith(spec["sic_prefix"]):
            raise ValueError(f"{path} is not the {spec['label']} aggregate "
                             f"(ice_source = {src!r}, sic_source = {sic!r})")
        runs[key] = ds
        print(f"{spec['label']:14s} {path.name}: sic_source = {sic}")
    ref = runs["nsidc"]
    for key, ds in runs.items():
        for c in ("year", "subarea", "outcome"):
            if not np.array_equal(ds[c].values, ref[c].values):
                raise ValueError(f"{key}: coordinate {c} differs from the NSIDC aggregate")
        if not np.array_equal(ds["total"].values, ref["total"].values):
            raise ValueError(f"{key}: particles released per day differ from the NSIDC aggregate; "
                             "the three readings must classify the same trajectories")
    return runs


def season_mean_shares(ds: xr.Dataset, subarea: str | None = None
                       ) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    (years, share[year, outcome] in %, outcome names): season mean of the
    per-day outcome fractions, censored folded into M6, from counts_release
    summed over subareas (domain, % of all releases) or for one subarea (%
    of the subarea's own releases).
    """
    names = list(ds["outcome"].values.astype(str))
    cr = ds["counts_release"]
    cr = cr.sel(subarea=subarea) if subarea is not None else cr.sum(dim="subarea")
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


def differences(shares: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {k: shares[a] - shares[b] for k, (a, b) in DIFFERENCES.items()}


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def mark_switch(ax: plt.Axes, label: bool) -> None:
    ax.axvline(FORCING_STEP_YEAR - 0.5, color="0.4", ls=":", lw=0.9, zorder=1)
    if label:
        y = ax.get_ylim()[1]
        ax.text(FORCING_STEP_YEAR - 0.7, 0.97 * y, "ERA-Interim", color="0.4", fontsize=7.5,
                ha="right", va="top")
        ax.text(FORCING_STEP_YEAR - 0.3, 0.97 * y, "ERA5", color="0.4", fontsize=7.5,
                ha="left", va="top")


def draw(years: np.ndarray, shares: dict[str, np.ndarray], diffs: dict[str, np.ndarray],
         names: list[str]) -> plt.Figure:
    fig, (ax_a, ax_b, ax_c) = plt.subplots(3, 1, figsize=PAPER, sharex=True)
    si = names.index("success")

    # ---- (a) success under the three readings
    for key in LEGEND_A:
        ax_a.plot(years, shares[key][:, si], mec=STYLE[key]["color"], label=READINGS[key]["label"],
                  **MARKER, **STYLE[key])
    ax_a.set_ylim(0, SUCCESS_YMAX)
    ax_a.set_ylabel("Season-mean recruitment success (%)")
    ax_a.set_title("(a) Three ice readings", loc="left", pad=3)
    ax_a.legend(loc="lower left", framealpha=1.0, handlelength=3.6)   # long enough to show the dashes
    mark_switch(ax_a, label=True)

    # ---- (b) product and (c) resolution differences per outcome, same axis
    for ax, which, lab in ((ax_b, "product", "b"), (ax_c, "resolution", "c")):
        for layer in OUTCOMES:
            li = names.index(layer)
            ax.plot(years, diffs[which][:, li], color=COLOR[layer], mec=COLOR[layer],
                    label=LABELS[layer], zorder=3, **MARKER)
        ax.axhline(0, color="0.3", lw=0.6, zorder=1)
        ax.set_ylim(-DIFF_YLIM, DIFF_YLIM)
        ax.set_ylabel(f"{DIFF_LABEL[which].split(' (')[0]} (pp)")
        ax.set_title(f"({lab}) {which.capitalize()} difference per outcome", loc="left", pad=3)
        mark_switch(ax, label=False)

    ax_c.set_xlim(years[0] - 0.6, years[-1] + 0.6)
    ax_c.set_xticks(years[years % 5 == 0])
    ax_c.set_xlabel("Spawning year")

    fig.tight_layout(h_pad=1.0)

    # One legend for (b) and (c), one column, standing on the right across
    # the two panels: its top in the empty band at the bottom of (b), the
    # rest in the empty upper half of (c). Outcomes success first, then the
    # constraints in the order they act.
    handles, labels = ax_b.get_legend_handles_labels()
    pos_b, pos_c = ax_b.get_position(), ax_c.get_position()
    fig.legend(handles, labels, loc="upper right",
               bbox_to_anchor=(pos_c.x1 - 0.006, pos_b.y0 + 0.12 * pos_b.height),
               bbox_transform=fig.transFigure, framealpha=1.0)
    return fig


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

def ice_state_check(years: np.ndarray, level: np.ndarray, diff: np.ndarray) -> dict:
    """Fit diff ~ level on the pre-step years, predict the post-step
    difference from the post-step levels, return the residual statistics."""
    pre, post = years < FORCING_STEP_YEAR, years >= FORCING_STEP_YEAR
    slope, icpt = np.polyfit(level[pre], diff[pre], 1)
    r = np.corrcoef(level[pre], diff[pre])[0, 1]
    res_pre = diff[pre] - (slope * level[pre] + icpt)
    res_post = diff[post] - (slope * level[post] + icpt)
    return dict(r=r, predicted=float(np.mean(slope * level[post] + icpt)),
                observed=float(diff[post].mean()), res_mean=float(res_post.mean()),
                res_sd_pre=float(res_pre.std(ddof=1)),
                n_same_sign=int(max((res_post > 0).sum(), (res_post < 0).sum())),
                n_post=int(post.sum()))


def shift_table(years: np.ndarray, shares: dict[str, np.ndarray], diffs: dict[str, np.ndarray],
                names: list[str], which: str, scope: str) -> dict[str, float]:
    """Print the pre/post-2019 shift of one difference per outcome, with
    the ice-state check; return the shifts."""
    a_key, b_key = DIFFERENCES[which]
    diff = diffs[which]
    pre, post = years < FORCING_STEP_YEAR, years >= FORCING_STEP_YEAR
    print(f"\n{DIFF_LABEL[which]}, {scope}: mean (sd) over years, pre-{FORCING_STEP_YEAR} n = {pre.sum()} "
          f"vs {FORCING_STEP_YEAR}-{years[-1]} n = {post.sum()}; shift = post minus pre; "
          f"r between the two readings; ice-state check (residual in pre-{FORCING_STEP_YEAR} sd, "
          f"post-{FORCING_STEP_YEAR} residuals of one sign)")
    print(f"| Outcome | pre | post | shift | state check | r ({READINGS[b_key]['short']}, "
          f"{READINGS[a_key]['short']}) |")
    print("|---|---|---|---|---|---|")
    shifts = {}
    for layer in OUTCOMES:
        li = names.index(layer)
        a, b = diff[pre, li], diff[post, li]
        r = np.corrcoef(shares[a_key][:, li], shares[b_key][:, li])[0, 1]
        c = ice_state_check(years, shares["glorys12"][:, li], diff[:, li])
        shifts[layer] = b.mean() - a.mean()
        print(f"| {SHORT[layer]} | {a.mean():+.2f} ({a.std(ddof=1):.2f}) | {b.mean():+.2f} ({b.std(ddof=1):.2f}) "
              f"| {shifts[layer]:+.2f} pp | {c['res_mean'] / c['res_sd_pre']:+.1f} sd, "
              f"{c['n_same_sign']}/{c['n_post']} | {r:.2f} |")
    return shifts


def report(years: np.ndarray, shares: dict[str, np.ndarray], diffs: dict[str, np.ndarray],
           names: list[str], scope: str = "domain, pp of all releases") -> None:
    si, mi = names.index("success"), names.index("killed_M1")
    keys = list(READINGS)
    pre, post = years < FORCING_STEP_YEAR, years >= FORCING_STEP_YEAR

    print(f"\nSeason-mean success and M1 share (%), {scope.split(',')[0]}, under the three readings "
          f"({' / '.join(READINGS[k]['short'] + ' = ' + READINGS[k]['label'] for k in keys)}); "
          f"rank of the year's success under G and N:")
    rank = {k: np.argsort(np.argsort(-shares[k][:, si])) + 1 for k in ("glorys12", "nsidc")}
    print(f"{'year':>6s} {'success G/G25/N':>20s} {'rank G/N':>9s} {'M1 G/G25/N':>20s}")
    for i, y in enumerate(years):
        s = "/".join(f"{shares[k][i, si]:4.1f}" for k in keys)
        m = "/".join(f"{shares[k][i, mi]:4.1f}" for k in keys)
        print(f"{y:>6d} {s:>20s} {rank['glorys12'][i]:>4d}/{rank['nsidc'][i]:<4d} {m:>20s}")
    for k in keys:
        s = shares[k][:, si]
        print(f"  {READINGS[k]['label']:14s} success mean {s.mean():.2f}% (sd {s.std(ddof=1):.2f}); "
              f"pre-{FORCING_STEP_YEAR} {s[pre].mean():.2f}, {FORCING_STEP_YEAR}- {s[post].mean():.2f}; "
              f"min {s.min():.2f} ({years[np.argmin(s)]}), max {s.max():.2f} ({years[np.argmax(s)]})")

    shifts = {which: shift_table(years, shares, diffs, names, which, scope)
              for which in ("product", "resolution", "total")}

    print(f"\nDecomposition of the total shift at {FORCING_STEP_YEAR} (pp): product + resolution = total; "
          "largest |resolution difference| in any year:")
    for layer in OUTCOMES:
        li = names.index(layer)
        print(f"  {SHORT[layer]:8s} {shifts['product'][layer]:+.2f} {shifts['resolution'][layer]:+.2f} "
              f"= {shifts['total'][layer]:+.2f}   max |res| {np.abs(diffs['resolution'][:, li]).max():.2f}")
    print("  (a shift in the product difference that the ice-state check does not predict, with none "
          "in the resolution difference, is the forcing signature)")

    print(f"\n32-year mean share of each outcome (%) under the three readings, {scope.split(',')[0]}:")
    print(f"{'':10s}" + "".join(f"{READINGS[k]['label']:>15s}" for k in keys) + f"{'N − G':>9s}")
    for layer in OUTCOMES:
        li = names.index(layer)
        v = [shares[k][:, li].mean() for k in keys]
        print(f"{SHORT[layer]:10s}" + "".join(f"{x:15.2f}" for x in v) + f"{v[2] - v[0]:+9.2f}")


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(here / "data"))
    args = ap.parse_args()

    runs = load_readings(Path(args.data))
    shares, years, names = {}, None, None
    for key, ds in runs.items():
        years, shares[key], names = season_mean_shares(ds)
        if not np.allclose(shares[key].sum(axis=1), 100.0):
            raise ValueError(f"{key}: domain season-mean shares do not sum to 100%")
    diffs = differences(shares)

    fig = draw(years, shares, diffs, names)
    for ext in ("pdf", "png"):
        out = here / f"{OUTFILE}.{ext}"
        fig.savefig(out, dpi=300)
        print(f"Wrote {out}")
    plt.close(fig)

    report(years, shares, diffs, names)


if __name__ == "__main__":
    main()
