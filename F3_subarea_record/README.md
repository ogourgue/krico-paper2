# F3 — Per-subarea record

Interannual record of recruitment success and its constraint composition in
each of the four CCAMLR subareas that carry the recruitment (88.3 Amundsen
Sea, 48.1 Antarctic Peninsula, 48.2 South Orkney Islands, 48.4 South
Sandwich Islands), spawning years 1994–2025, on the NSIDC-ice
classification.

## Scope

- Particles grouped by the subarea of their release position; each
  subarea's rates use its own releases as denominator, so the four panels
  compare in rate although the release counts differ tenfold. 48.6 is split
  at 60°S in the aggregate (not drawn here).
- Spawning year *Y* = releases 15 Nov *Y*−1 to 14 Mar *Y*; Feb 29 cohorts
  excluded (3 840 cohorts); censored particles folded into M6, as in Paper 1
  Figures 2 and 3 and in F2.
- Season mean = mean over the 120 release days of each day's outcome
  fractions.
- Sea ice read by the classification: NOAA/NSIDC G02202 v6 (attribute
  `sic_source` of the aggregate). The GLORYS12-ice version of this figure is
  the Supporting Information sensitivity; the two ice sources are never
  mixed in one aggregate.

## Design

Four panels (a)–(d) in a 2 × 2 layout, 6.5 × 5.9 in, each built as F2's
single panel.

- Stacked bar per spawning year, left axis, 0–100% of the subarea's
  releases. Layers bottom to top, in the order the constraints act, with
  Paper 1's Figure 3 palette: Domain exit (grey, a thin floor so the stack
  sums to 100%); Ice at spawning (M1); Calyptopis starvation (M4);
  Under-developed (M5a); Off-shelf (M5b); No winter ice (M6); Recruitment
  success (green, top).
- Season-mean success as a black line with open markers on the right axis,
  with its 32-year mean dashed. The right axis runs 0–30% in all four
  panels, so that the lines compare across subareas; the green top layer
  shows the same quantity in the composition.
- The end-2018 switch of the GLORYS12 surface forcing is not marked (as in
  F2; shown on the ice-product figure).
- One legend below the panels, read as the stack from the top: success
  line and mean first, then the layers from success down to domain exit.
- Arial 8–9 pt, text kept as text in the PDF (Type 42 fonts).

## Files

- `aggregate.py` — reads the NSIDC-ice cohort files
  (`$KRICO_POST/recruitment/data_nsidc/YYYY_MM_DD.nc`) and the CCAMLR
  shapefile (`../ccamlr-data/`), writes `data/aggregated.nc` and
  `data/cohort_sha256.txt`. A copy of `F2_domain_timeseries/aggregate.py`;
  `--compare` checks the counts against F2's aggregate.
- `data/aggregated.nc` — particle counts per (spawning year, season day,
  subarea, outcome), by release position (`counts_release`) and by fate
  position (`counts_fate`); 48.6 split at 60°S; `total` and `has_data` per
  (year, season day). Attributes: `sic_source`, `source_data_dir`,
  `n_cohort_files`, `shapefile_sha256`, `created`.
- `data/cohort_sha256.txt` — sha256 of the 3 840 cohort files read, in
  `sha256sum -c` format.
- `plot.py` — reads `data/aggregated.nc`, writes `subarea_record.pdf` and
  `.png`; prints the per-subarea reference numbers quoted in the text:
  season-mean success per subarea and year; mean, sd and share of the
  domain's interannual variance for all eight subareas; each outcome's
  interannual sd and correlation with the subarea's success; the
  correlation of success between the four subareas; and the survivor
  partition M5b / (M5b + success) per subarea.

## Provenance

The cohort files are the output of `krico-post-production`
(`run_year_nsidc.sh`): Paper 1's trajectories and filters, with every
sea-ice concentration the classification reads taken from NSIDC G02202 v6
(daily, 25 km, containing-cell sampling, no interpolation, nearest-ocean
redirection off). `aggregate.py` checks that every file carries the same
`sic_source`, that the outcome codes match the names used here, and that
the counts summed over subarea and outcome equal the number of particles
released on every day. The counts are identical to those of
`F2_domain_timeseries/data/aggregated.nc`, produced from the same files.

## Run

```bash
export KRICO_POST=/path/to/krico-post-production   # directory holding recruitment/data_nsidc/
python aggregate.py --compare ../F2_domain_timeseries/data/aggregated.nc   # laptop, reads and hashes ~56 GB once
python plot.py               # no data access needed beyond data/aggregated.nc
```
