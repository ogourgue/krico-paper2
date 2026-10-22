"""
FS2 plot: the product difference of FS1 per release subarea, spawning years
1994-2025.

Reads data/aggregated_glorys12.nc, data/aggregated_glorys12_25km.nc and
data/aggregated_nsidc.nc (the three aggregates of FS1, produced by this
folder's copy of its aggregate.py) and draws, for the larvae released in
each of the eight subareas (48.6 split at 60S), the difference per spawning year
and outcome (success, M1, M4, M5a, M5b, M6) between the share under NSIDC
ice and under GLORYS12-25km ice, in percentage points of the subarea's own
releases. The eight panels share one axis so that the steps compare across
subareas. The end-2018 switch of the GLORYS12 atmospheric forcing
(ERA-Interim to ERA5) is marked between spawning years 2018 and 2019.

Per-subarea shares use the subarea's own releases as denominator, so the
panels compare as rates and do not sum to FS1's domain panel. Season mean =
mean over the 120 release days of the per-day fraction (Feb 29 excluded
upstream); censored particles are folded into M6, as in Paper 1.

Writes ice_product_subarea.pdf and .png at 6.5 x 8.0 in (4 x 2 panels) and
prints the numbers the figure supports: per subarea, the season-mean
success and M1 share per year under the three readings, and the shift
tables of FS1 (product, resolution and total differences per outcome with
the ice-state check) and the decomposition; then a summary of the M1 shift
across subareas and the 32-year mean resolution difference per subarea and
outcome.

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

PAPER = (6.5, 8.0)               # letter text width; 4 x 2 panels within one page plus the legend
OUTFILE = "ice_product_subarea"

# The three readings, with the sic_source each aggregate must carry
# (written by aggregate.py).
READINGS = {
    "glorys12":      dict(label="GLORYS12",       short="G",   sic_prefix="GLORYS12"),
    "glorys12_25km": dict(label="GLORYS12-25km",  short="G25", sic_prefix="GLORYS12v1 ice binned onto the NSIDC"),
    "nsidc":         dict(label="NSIDC",          short="N",   sic_prefix="NSIDC G02202 v6"),
}
MARKER = dict(marker="o", ms=3.0, mfc="white", mew=1.0)   # FS1's markers, smaller for the 1.5 in panels
# The three differences, name -> (minuend, subtrahend).
DIFFERENCES = {
    "product":    ("nsidc", "glorys12_25km"),        # same grid and sampling, only the ice values differ
    "resolution": ("glorys12_25km", "glorys12"),     # same ice, grid and sampling differ
    "total":      ("nsidc", "glorys12"),
}
DIFF_LABEL = {"product": "NSIDC − GLORYS12-25km (product)",
              "resolution": "GLORYS12-25km − GLORYS12 (resolution)",
              "total": "NSIDC − GLORYS12 (total)"}
DRAWN = "product"

# Outcomes drawn, success first then the constraints in the order they act,
# in the matplotlib colour cycle as FS1. Domain exit is not drawn; censored
# is folded into M6.
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

# Panels: the eight subareas in the order of the aggregate (48.6 split at 60S).
PANELS = ["88.3", "48.1", "48.2", "48.3", "48.4", "48.5", "48.6N", "48.6S"]
NAMES = {"88.3": "Amundsen Sea", "48.1": "Antarctic Peninsula", "48.2": "South Orkney Islands",
         "48.3": "South Georgia", "48.4": "South Sandwich Islands", "48.5": "Weddell Sea",
         "48.6N": "Bouvet N", "48.6S": "Bouvet S"}
PANEL_LABELS = "abcdefgh"

FORCING_STEP_YEAR = 2019         # first spawning year on ERA5 (2019 straddles the switch)
DIFF_YLIM = (-25.0, 20.0)        # pp, shared by the eight panels; 48.6S sets the floor
DEGENERATE = 0.01                # pp: below this pre-2019 spread, no relation is fitted


# ---------------------------------------------------------------------------
# Data (as FS1)
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

def draw(years: np.ndarray, per_subarea: dict[str, dict[str, np.ndarray]], names: list[str]
         ) -> plt.Figure:
    fig, axes = plt.subplots(4, 2, figsize=PAPER, sharex=True, sharey=True)
    for ax, code, lab in zip(axes.ravel(), PANELS, PANEL_LABELS):
        diff = per_subarea[code][DRAWN]
        for layer in OUTCOMES:
            li = names.index(layer)
            ax.plot(years, diff[:, li], color=COLOR[layer], mec=COLOR[layer],
                    label=LABELS[layer], zorder=3, **MARKER)
        ax.axhline(0, color="0.3", lw=0.6, zorder=1)
        ax.axvline(FORCING_STEP_YEAR - 0.5, color="0.4", ls=":", lw=0.9, zorder=1)
        ax.set_title(f"({lab}) {code}  {NAMES[code]}", loc="left", pad=3)
    axes[0, 0].set_ylim(*DIFF_YLIM)
    axes[0, 0].set_xlim(years[0] - 0.6, years[-1] + 0.6)
    axes[0, 0].set_xticks(years[years % 5 == 0])
    for ax in axes[:, 0]:
        ax.set_ylabel("Product difference (pp)")
    for ax in axes[-1, :]:
        ax.set_xlabel("Spawning year")

    # One legend below: the outcomes, success first then the constraints
    # in the order they act.
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0),
               framealpha=1.0)
    fig.tight_layout(rect=(0, 0.065, 1, 1), h_pad=1.0, w_pad=0.8)
    return fig


# ---------------------------------------------------------------------------
# Numbers (the shift tables as FS1, per subarea)
# ---------------------------------------------------------------------------

def ice_state_check(years: np.ndarray, level: np.ndarray, diff: np.ndarray) -> dict:
    """Fit diff ~ level on the pre-step years, predict the post-step
    difference from the post-step levels, return the residual statistics."""
    pre, post = years < FORCING_STEP_YEAR, years >= FORCING_STEP_YEAR
    if level[pre].std(ddof=1) < DEGENERATE or diff[pre].std(ddof=1) < DEGENERATE:
        # Outcome absent or constant in the subarea (M1, M4, M5a in 48.3): nothing to fit.
        return dict(r=np.nan, predicted=np.nan, observed=float(diff[post].mean()),
                    res_mean=np.nan, res_sd_pre=np.nan, n_same_sign=0, n_post=int(post.sum()))
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
                names: list[str], which: str, scope: str) -> dict[str, tuple[float, float]]:
    """Print the pre/post-2019 shift of one difference per outcome, with
    the ice-state check; return (shift, state check in sd) per outcome."""
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
    out = {}
    for layer in OUTCOMES:
        li = names.index(layer)
        a, b = diff[pre, li], diff[post, li]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.corrcoef(shares[a_key][:, li], shares[b_key][:, li])[0, 1]
        c = ice_state_check(years, shares["glorys12"][:, li], diff[:, li])
        sd = c["res_mean"] / c["res_sd_pre"] if np.isfinite(c["res_sd_pre"]) else np.nan
        out[layer] = (b.mean() - a.mean(), sd)
        check = f"{sd:+.1f} sd, {c['n_same_sign']}/{c['n_post']}" if np.isfinite(sd) else "n/a"
        r_txt = f"{r:.2f}" if np.isfinite(r) else "n/a"
        print(f"| {SHORT[layer]} | {a.mean():+.2f} ({a.std(ddof=1):.2f}) | {b.mean():+.2f} ({b.std(ddof=1):.2f}) "
              f"| {out[layer][0]:+.2f} pp | {check} | {r_txt} |")
    return out


def report(years: np.ndarray, shares_by: dict[str, dict[str, np.ndarray]],
           diffs_by: dict[str, dict[str, np.ndarray]], names: list[str]) -> None:
    si, mi = names.index("success"), names.index("killed_M1")
    keys = list(READINGS)
    pre, post = years < FORCING_STEP_YEAR, years >= FORCING_STEP_YEAR
    summary = {}

    for code in PANELS:
        shares, diffs = shares_by[code], diffs_by[code]
        scope = f"released in {code}, pp of the subarea's own releases"
        print(f"\n{'=' * 78}\nSubarea {code} ({NAMES[code]})")
        print(f"Season-mean success and M1 share (%) under the three readings "
              f"({' / '.join(READINGS[k]['short'] + ' = ' + READINGS[k]['label'] for k in keys)}):")
        print(f"{'year':>6s} {'success G/G25/N':>20s} {'M1 G/G25/N':>20s}")
        for i, y in enumerate(years):
            s = "/".join(f"{shares[k][i, si]:4.1f}" for k in keys)
            m = "/".join(f"{shares[k][i, mi]:4.1f}" for k in keys)
            print(f"{y:>6d} {s:>20s} {m:>20s}")
        for k in keys:
            s, m = shares[k][:, si], shares[k][:, mi]
            print(f"  {READINGS[k]['label']:14s} success mean {s.mean():.1f}% (pre-{FORCING_STEP_YEAR} "
                  f"{s[pre].mean():.1f}, {FORCING_STEP_YEAR}- {s[post].mean():.1f}); "
                  f"M1 mean {m.mean():.1f}% ({m[pre].mean():.1f}, {m[post].mean():.1f})")
        tables = {which: shift_table(years, shares, diffs, names, which, scope)
                  for which in ("product", "resolution", "total")}
        summary[code] = tables
        print(f"\nDecomposition of the total shift at {FORCING_STEP_YEAR} in {code} (pp): "
              "product + resolution = total; largest |resolution difference| in any year:")
        for layer in OUTCOMES:
            li = names.index(layer)
            print(f"  {SHORT[layer]:8s} {tables['product'][layer][0]:+.2f} {tables['resolution'][layer][0]:+.2f} "
                  f"= {tables['total'][layer][0]:+.2f}   max |res| {np.abs(diffs['resolution'][:, li]).max():.2f}")

    print(f"\n{'=' * 78}\nSummary across subareas: total shift at {FORCING_STEP_YEAR}, NSIDC − GLORYS12, "
          "pp of the subarea's releases (ice-state check in pre-2019 residual sd); "
          "product shift in brackets:")
    print("| Outcome | " + " | ".join(PANELS) + " |")
    print("|---|" + "---|" * len(PANELS))
    for layer in OUTCOMES:
        cells = [f"{summary[c]['total'][layer][0]:+.1f} "
                 + (f"({summary[c]['total'][layer][1]:+.1f} sd) " if np.isfinite(summary[c]['total'][layer][1])
                    else "(n/a) ")
                 + f"[{summary[c]['product'][layer][0]:+.1f}]" for c in PANELS]
        print(f"| {SHORT[layer]} | " + " | ".join(cells) + " |")
    order = sorted(PANELS, key=lambda c: -summary[c]["total"]["killed_M1"][0])
    print("M1 shift, largest first: " + ", ".join(
        f"{c} {summary[c]['total']['killed_M1'][0]:+.1f}"
        + (f" ({summary[c]['total']['killed_M1'][1]:.1f} sd)"
           if np.isfinite(summary[c]['total']['killed_M1'][1]) else "")
        for c in order))

    print("\n32-year mean resolution difference, GLORYS12-25km − GLORYS12, pp of the subarea's releases:")
    print("| Outcome | " + " | ".join(PANELS) + " |")
    print("|---|" + "---|" * len(PANELS))
    for layer in OUTCOMES:
        li = names.index(layer)
        print(f"| {SHORT[layer]} | " + " | ".join(f"{diffs_by[c]['resolution'][:, li].mean():+.2f}"
                                                  for c in PANELS) + " |")

    print("\nLargest single-year |product difference| per subarea and outcome (pp):")
    print("| Outcome | " + " | ".join(PANELS) + " |")
    print("|---|" + "---|" * len(PANELS))
    for layer in OUTCOMES:
        li = names.index(layer)
        print(f"| {SHORT[layer]} | " + " | ".join(f"{np.abs(diffs_by[c]['product'][:, li]).max():.1f}"
                                                  for c in PANELS) + " |")


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(here / "data"))
    args = ap.parse_args()

    runs = load_readings(Path(args.data))
    shares_by, diffs_by, years, names = {}, {}, None, None
    for code in PANELS:
        shares = {}
        for key, ds in runs.items():
            years, shares[key], names = season_mean_shares(ds, code)
            if not np.allclose(shares[key].sum(axis=1), 100.0):
                raise ValueError(f"{key}, {code}: season-mean shares do not sum to 100%")
        shares_by[code] = shares
        diffs_by[code] = differences(shares)

    fig = draw(years, diffs_by, names)
    for ext in ("pdf", "png"):
        out = here / f"{OUTFILE}.{ext}"
        fig.savefig(out, dpi=300)
        print(f"Wrote {out}")
    plt.close(fig)

    report(years, shares_by, diffs_by, names)


if __name__ == "__main__":
    main()
