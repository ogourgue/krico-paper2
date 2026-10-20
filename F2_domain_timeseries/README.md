# F2 — Domain time series

Interannual record of recruitment success and its constraint composition over
the whole model domain, spawning years 1994–2025, on the NSIDC-ice
classification.

## Scope

- All releases, all subareas (the domain is the sum over subareas of the
  per-subarea counts in `data/aggregated.nc`).
- Spawning year *Y* = releases 15 Nov *Y*−1 to 14 Mar *Y*; Feb 29 cohorts
  excluded (3 840 cohorts); censored particles folded into M6, as in Paper 1
  Figures 2 and 3.
- Season mean = mean over the 120 release days of each day's outcome fractions.
- Sea ice read by the classification: NOAA/NSIDC G02202 v6 (attribute
  `sic_source` of the aggregate). The GLORYS12-ice version of the same
  figure is the Supporting Information sensitivity; the two ice sources are
  never mixed in one aggregate.

## Design

One panel, 6.5 × 4.875 in.

- Stacked bar per spawning year, left axis, 0–100% of that year's releases.
  Layers bottom to top, in the order the constraints act, with Paper 1's
  Figure 3 palette: Domain exit (`exited_domain`, grey, a model-domain
  limitation kept as a thin floor so the stack sums to 100%); Ice at
  spawning (M1); Calyptopis starvation (M4); Under-developed (M5a);
  Off-shelf (M5b); No winter ice (M6); Recruitment success (green, top).
- Season-mean success as a black line with open markers on the right axis
  (0–8%), with its 32-year mean dashed. The right axis is needed because
  success is 3–7% of releases and would be unreadable on the 0–100% scale;
  the green top layer shows the same quantity in the composition. Black
  rather than green because the line crosses the red bands.
- The end-2018 switch of the GLORYS12 surface forcing (ERA-Interim to
  ERA5) is not marked: with observed ice, only the circulation crosses it;
  the switch is shown on the ice-product figure.
- Legend below the panel, read as the stack from the top: success line and
  mean first, then the layers from success down to domain exit.
- Arial 8–9 pt, text kept as text in the PDF (Type 42 fonts).

## Files

- `aggregate.py` — reads the NSIDC-ice cohort files
  (`$KRICO_POST/recruitment/data_nsidc/YYYY_MM_DD.nc`) and the CCAMLR
  shapefile (`../ccamlr-data/`), writes `data/aggregated.nc` and
  `data/cohort_sha256.txt`.
- `data/aggregated.nc` — particle counts per (spawning year, season day,
  subarea, outcome), by release position (`counts_release`) and by fate
  position (`counts_fate`); 48.6 split at 60°S; `total` and `has_data` per
  (year, season day). Attributes: `sic_source`, `source_data_dir`,
  `n_cohort_files`, `shapefile_sha256`, `created`.
- `data/cohort_sha256.txt` — sha256 of the 3 840 cohort files read, in
  `sha256sum -c` format.
- `plot.py` — reads `data/aggregated.nc`, writes `domain_timeseries.pdf`
  and `.png`; prints the
  per-year shares and the reference numbers quoted in the text (mean, sd,
  min and max years, ranking, 1994–2016 vs 2017–2025 means, each outcome's
  interannual sd and correlation with success).

## Provenance

The cohort files are the output of `krico-post-production`
(`run_year_nsidc.sh`): Paper 1's trajectories and filters, with every
sea-ice concentration the classification reads taken from NSIDC G02202 v6
(daily, 25 km, containing-cell sampling, no interpolation, nearest-ocean
redirection off). `aggregate.py` checks that every file carries the same
`sic_source`, that the outcome codes match the names used here, and that
the counts summed over subarea and outcome equal the number of particles
released on every day. The per-outcome totals equal those of the exploratory
aggregate `explore/ice_source/data/aggregated_subarea_nsidc.nc` produced
from the same files.

## Run

```bash
export KRICO_POST=/path/to/krico-post-production   # directory holding recruitment/data_nsidc/
python aggregate.py          # laptop, reads and hashes ~56 GB once
python plot.py               # no data access needed beyond data/aggregated.nc
```
