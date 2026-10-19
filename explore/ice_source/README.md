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
| `aggregate_nsidc.py` | locally | `$KRICO_POST/recruitment/data_nsidc/*.nc` + `../../ccamlr-data/` | `data/aggregated_subarea_nsidc.nc` (~1 MB, force-added) |
| `aggregate_glorys12_25km.py` | locally | `$KRICO_POST/recruitment/data_glorys12_25km/*.nc` + `../../ccamlr-data/` | `data/aggregated_subarea_glorys12_25km.nc` (same) |
| `plot_ice_source.py` | locally | `../timeseries/data/aggregated_subarea.nc` + the two above | `timeseries_ice_source.png`: (a) success under the three ice readings; (b) product difference (solid) and resolution difference (dashed) per outcome. Stdout: per-year table and shift tables for product, resolution and total, with the ice-state check; `--subarea CODE` for one release subarea |
| `plot_ice_source_subarea.py` | locally | same | `timeseries_ice_source_subarea.png`: the product difference per release subarea (88.3, 48.1, 48.2, 48.4, 48.5, 48.6S), rates per subarea release; `--difference resolution\|total` for the others (suffixed file); stdout tables per subarea |

`aggregate_nsidc.py` is a copy of `../timeseries/aggregate_subarea.py` with
the input directory and output name changed (and the shapefile default fixed
to the repo root), so the folder is self-contained; `aggregate_glorys12_25km.py`
is a copy of it for the third source. If the timeseries aggregation changes,
re-copy.

## Three ice readings

| Reading | Classification | Ice | Grid, sampling |
|---|---|---|---|
| GLORYS12 | `recruitment/data/` (production, Paper 1) | GLORYS12 `ileadfra` | 1/12°, Parcels interpolation along the track, nearest cell at spawning |
| GLORYS12-25km | `recruitment/data_glorys12_25km/` | GLORYS12 `ileadfra`, mean of the ORCA12 cells inside each 25 km cell, NSIDC land/coast/lake as fill | NSIDC 25 km grid, containing cell |
| NSIDC | `recruitment/data_nsidc/` (Paper 2) | NOAA/NSIDC G02202 v6 `cdr_seaice_conc` | NSIDC 25 km grid, containing cell |

Differences: **product** = NSIDC − GLORYS12-25km (same grid and sampling, only
the ice values differ); **resolution** = GLORYS12-25km − GLORYS12 (same ice,
grid and sampling differ); **total** = NSIDC − GLORYS12 = product + resolution.

## Reading the figure

(a) Season-mean success per spawning year under the three ice readings, one
axis. (b) Per year and outcome (success, M1, M5b, M6), in percentage points
of particles released: solid, the product difference; dashed, the resolution
difference; 2019 marked.

The level of each difference is a gap of construction and is not the point.
The forcing signature is a step at 2019 in the product difference with none
in the resolution difference (the grids do not change in 2019). The stdout
tables give the pre- and post-2019 mean of each difference per outcome with
its spread; the Welch t on 25 vs 7 years is indicative only.

One confound is checked before a step is called: the product gap depends on
how much ice there is, and the post-2018 years are low-ice years. The
ice-state check fits the pre-2019 difference against the GLORYS12 level of
the same outcome and predicts the post-2019 difference from the post-2019
levels; a shift the prediction does not account for, with residuals of one
sign, is the forcing signature.

The per-subarea figure repeats the product difference for six release
subareas, as rates per subarea release: the four recruiting ones, and 48.5
and 48.6S where M1 is large and a flip of its difference shows most clearly.

Conventions follow `../timeseries/plot_domain.py`: season mean over the 120
release days, Feb 29 excluded, censored folded into M6, F3 palette, slide
size.

## Status (19 October 2026)

NSIDC classification aggregated and read (14 October): the total difference
in M1 flips sign at 2019, +3.7 pp domain-wide, in the coastal subareas; M5b
flat; Paper 2 runs on NSIDC ice (`Paper 2/methodology.md` P2-D07). Third
classification (GLORYS12 on 25 km) run 15 October; scripts updated for the
three-way decomposition, aggregate and figures to be regenerated.
