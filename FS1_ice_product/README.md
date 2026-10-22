# FS1 — The classification under three sea-ice readings

Recruitment success and the fate of the larvae, spawning years 1994–2025,
whole domain, when the classification of the same trajectories reads its
sea-ice concentration from GLORYS12 on its native grid, from GLORYS12 binned
onto the 25 km grid of the observations, and from the NSIDC G02202 v6
observations themselves. The figure shows why the paper's classification
reads observed ice: the difference between the reanalysis and the observed
ice, as the outcomes see it, changes at the end-2018 switch of the GLORYS12
atmospheric forcing (ERA-Interim to ERA5), and the 25 km grid itself
changes nothing.

## Scope

- Same trajectories, filters and constants in the three classifications;
  only the sea-ice concentration read by the filters differs (M1 at
  spawning, the along-trajectory series behind M4, the winter-advance
  detection, censoring). The circulation, and so the on-/off-shelf sorting
  behind M5b, is GLORYS12 in all three.
- Three readings:

  | Reading | Sea ice | Grid and sampling |
  |---|---|---|
  | GLORYS12 | GLORYS12v1 `ileadfra` | 1/12°; interpolated along the trajectory, nearest cell at spawning (Paper 1's classification, dataset v2.0.0) |
  | GLORYS12-25km | GLORYS12v1 `ileadfra`, mean of the 1/12° cells inside each 25 km cell | NSIDC 25 km grid, containing cell, no interpolation |
  | NSIDC | NOAA/NSIDC G02202 v6 `cdr_seaice_conc`, daily | NSIDC 25 km grid, containing cell, no interpolation (the paper's classification) |

- Two differences, in percentage points of the particles released:
  **product** = NSIDC − GLORYS12-25km, the two ice products at equal grid
  and sampling; **resolution** = GLORYS12-25km − GLORYS12, the same ice on
  two grids. Their sum is the total NSIDC − GLORYS12 difference.
- Whole domain: counts summed over release subareas, in % of all releases.
  The same differences per release subarea are FS2.
- Spawning year *Y* = releases 15 Nov *Y*−1 to 14 Mar *Y*; Feb 29 cohorts
  excluded (3 840 cohorts); censored particles folded into M6, as in F2 and
  F3. Season mean = mean over the 120 release days of each day's outcome
  fractions.
- The atmospheric forcing of GLORYS12 switches from ERA-Interim to ERA5 on
  1 January 2019: spawning year 2019 straddles the switch, 2020 onward is
  entirely on ERA5. The switch is marked between 2018 and 2019.

## Design

Three full-width panels, 6.5 × 8.0 in, one spawning-year axis.

- (a) Season-mean recruitment success under the three readings, 0–8 % as
  F2's success axis: NSIDC in black (the paper's record, as the success
  line of F2 and F3), GLORYS12 in grey, GLORYS12-25km in dashed grey drawn
  over the GLORYS12 line it coincides with. Open markers on every year.
- (b) The product difference per outcome and year, ±5 pp around a zero
  line, for recruitment success and the five constraints that act on the
  larvae (M1, M4, M5a, M5b, M6), each in its own colour, kept in FS2;
  domain exit is omitted (its difference is below 0.03 pp).
- (c) The resolution difference per outcome and year on the same axis as
  (b), where it stays within ±0.4 pp.
- The forcing switch as a dotted line on the three panels, the two
  atmospheres named on (a).
- The readings' legend in (a), the paper's record first; one legend for
  the outcomes of (b) and (c), success first then the constraints in the
  order they act, standing on the right across the two panels where both
  are empty.
- Arial 8–9 pt, text kept as text in the PDF (Type 42 fonts).

## Files

- `aggregate.py` — reads the cohort files of one classification
  (`$KRICO_POST/recruitment/data_nsidc/`, `data/` or `data_glorys12_25km/`,
  selected with `--source nsidc|glorys12|glorys12_25km`) and the CCAMLR
  shapefile (`../ccamlr-data/`), writes `data/aggregated_<source>.nc` and
  `data/cohort_sha256_<source>.txt`. F3's aggregation with the source
  flag; `--compare` checks the counts against another aggregate.
- `data/aggregated_<source>.nc` — one per reading: particle counts per
  (spawning year, season day, subarea, outcome), by release position
  (`counts_release`) and by fate position (`counts_fate`); 48.6 split at
  60°S; `total` and `has_data` per (year, season day). Attributes:
  `ice_source`, `sic_source`, `m1_sic_source`, `m1_spawning_offset_days`,
  `source_data_dir`, `n_cohort_files`, `shapefile_sha256`, `created`.
- `data/cohort_sha256_<source>.txt` — sha256 of the 3 840 cohort files
  read for that reading, in `sha256sum -c` format.
- `plot.py` — reads the three aggregates, writes `ice_product.pdf` and
  `.png`; prints the numbers the figure supports: season-mean success and
  M1 share per year under the three readings, with each year's rank; for
  the product, resolution and total differences, per outcome, the mean
  difference before 2019 and from 2019, the shift between them, the
  correlation of the two readings, and the ice-state check; the
  decomposition of each total shift into product and resolution; and the
  32-year mean share of each outcome under the three readings.

The ice-state check asks whether a shift at 2019 is only the ice being
less there: the pre-2019 relation between the difference and the GLORYS12
level of the same outcome is fitted and applied to the post-2019 levels,
and the mean residual of the observed post-2019 difference from that
prediction is given in units of the pre-2019 residual spread, with the
number of post-2019 residuals of one sign. A residual of several spreads,
of one sign in every year, with no shift in the resolution difference, is
a change of the ice product at the switch.

## Provenance

The cohort files are the output of `krico-post-production`: Paper 1's
trajectories and filters, classified once with GLORYS12 sea ice
(`run_year.sh`; the published dataset v2.0.0, 10.5281/zenodo.22548763),
once with GLORYS12 sea ice binned onto the NSIDC 25 km grid
(`preprocess_glorys12_25km.py`, `run_year_glorys12_25km.sh`) and once with
NSIDC G02202 v6 sea ice (`run_year_nsidc.sh`), the two gridded readings
through the same sampler (daily, 25 km, containing cell, no interpolation,
coast and land cells read as below threshold, nearest-ocean redirection
off). `aggregate.py` checks, for every file of a reading, that the
provenance attributes identify that reading and no other (`sic_source`
where the files carry it; `m1_sic_source` and `m1_spawning_offset_days`
in every case; `nsidc_nearest_ocean = 0` for the gridded readings), that
the outcome codes match the names used here, and that the counts summed
over subarea and outcome equal the number of particles released on every
day. The NSIDC counts are identical to those of
`F3_subarea_record/data/aggregated.nc`; `plot.py` checks that the three
aggregates carry the readings they claim and the same releases per day.

## Run

```bash
export KRICO_POST=/path/to/krico-post-production   # directory holding recruitment/data*/
python aggregate.py --source nsidc --compare ../F3_subarea_record/data/aggregated.nc
python aggregate.py --source glorys12
python aggregate.py --source glorys12_25km         # each reads and hashes ~56 GB once
python plot.py                                     # needs only data/aggregated_*.nc
```
