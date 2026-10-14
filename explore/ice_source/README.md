# explore/ice_source — does the end-2018 forcing change in GLORYS12 show in the outcomes?

GLORYS12 is driven by ERA-Interim to 31 December 2018 and by ERA5 after.
The spawning year 2019 straddles the switch; the 2022-2024 highs and the real
post-2016 ice decline are all on the ERA5 side. To separate the two, the
recruitment classification is rerun on the same trajectories with every
sea-ice concentration it reads (M1 at spawning, and the along-trajectory
series behind M4, the advance detection and censoring) taken from the NSIDC
G02202 v6 record instead of GLORYS12 ice. The circulation, and so M5b's
on-/off-shelf sorting, is GLORYS12 in both runs: this tests the ice side of
the switch only.

Pipeline: krico-post-production, branch `nsidc-ice` (`run_year_nsidc.sh`;
sampler in `krico_recruitment/nsidc_ice.py`; four-cohort validation in
`scripts/validate_nsidc.csv`: r = 0.97-0.98 along trajectories, M1 within
4 points, coast cells 0.4% of positions).

| Script | Runs where | Input | Output |
|---|---|---|---|
| `aggregate_nsidc.py` | ECMWF | `$KRICO_POST/recruitment/data_nsidc/*.nc` + `../ccamlr-data/` | `data/aggregated_subarea_nsidc.nc` (~1 MB; commit once produced) |
| `plot_ice_source.py` | locally | `../timeseries/data/aggregated_subarea.nc` + `data/aggregated_subarea_nsidc.nc` | `timeseries_ice_source.png` + stdout table with the ice-state check; `--subarea CODE` for one release subarea |
| `plot_ice_source_subarea.py` | locally | same | `timeseries_ice_source_subarea.png`: panel (b) per release subarea (88.3, 48.1, 48.2, 48.4, 48.5, 48.6S), rates per subarea release; stdout table per subarea |

`aggregate_nsidc.py` is a copy of `../timeseries/aggregate_subarea.py` with
the input directory and output name changed, so the folder is
self-contained; if the timeseries aggregation changes, re-copy.

## Reading the figure

(a) Season-mean success per spawning year under both ice readings, one axis.
(b) NSIDC minus GLORYS12, percentage points of particles released, per year,
for success, M1, M5b and M6, with 2019 marked.

The level of each difference in (b) is the product gap (25 km observed cells
against 4 km reanalysis cells, the 80% M1 threshold on a coarser field) and
is not the point. A step at 2019 is the forcing signature; a flat line
through 2019 means the post-2018 signal is in the observed ice too. The
stdout table gives the pre- and post-2019 mean difference per outcome with
its spread; the Welch t on 25 vs 7 years is indicative only.

One confound is checked before a step is called: the product gap depends on
how much ice there is, and the post-2018 years are low-ice years. The
ice-state check fits the pre-2019 difference against the GLORYS12 level of
the same outcome and predicts the post-2019 difference from the post-2019
levels; a shift the prediction does not account for, with residuals of one
sign, is the forcing signature.

The per-subarea figure repeats panel (b) for six release subareas, as rates
per subarea release: the four recruiting ones, and 48.5 and 48.6S where M1
is large and a flip of its difference shows most clearly.

Conventions follow `../timeseries/plot_domain.py`: season mean over the 120
release days, Feb 29 excluded, censored folded into M6, F3 palette, slide
size.

## Status (13 October 2026)

Scripts written and tested on a perturbed copy of the GLORYS12 aggregation
(layout only). `data/aggregated_subarea_nsidc.nc` not yet produced; the
NSIDC classification is running on ECMWF.
