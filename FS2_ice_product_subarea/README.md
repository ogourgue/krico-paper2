# FS2 — The ice-product difference per release subarea

The product difference of FS1 for the larvae released in each of the eight
CCAMLR subareas of the domain, spawning years 1994–2025: the difference, per outcome, between the
share of the subarea's larvae under NSIDC G02202 v6 sea ice and under
GLORYS12 sea ice binned onto the same 25 km grid. The figure shows where the
change at the end-2018 switch of the GLORYS12 atmospheric forcing lives: in
the share of larvae under compact ice at spawning (M1), largest in the
Amundsen Sea and the two Weddell subareas.

## Scope

- The three classifications and the two differences are FS1's (see its
  README); here only the product difference, NSIDC − GLORYS12-25km, is
  drawn, in percentage points of the subarea's own releases, so that the
  panels compare as rates although the release counts differ tenfold. They
  do not sum to FS1's domain panel, which is the release-weighted sum.
- The eight subareas by release position, 48.6 split at 60°S as in F3:
  the four that carry the recruitment (88.3 Amundsen Sea, 48.1 Antarctic
  Peninsula, 48.2 South Orkney Islands, 48.4 South Sandwich Islands), the
  two where ice at spawning removes a large share of the larvae (48.5
  Weddell Sea, 48.6S), where a change of that share shows most clearly, and
  the two the winter ice edge never reaches (48.3 South Georgia, 48.6N),
  where the ice product changes nothing.
- Spawning year *Y* = releases 15 Nov *Y*−1 to 14 Mar *Y*; Feb 29 cohorts
  excluded (3 840 cohorts); censored particles folded into M6; season mean
  over the 120 release days, as in F2, F3 and FS1.
- The forcing switch is marked between spawning years 2018 and 2019, as in
  FS1.

## Design

Eight panels (a)–(h) in a 4 × 2 layout, 6.5 × 8.0 in, in the order of the
subarea codes, one spawning-year axis and one difference axis, −25 to
+20 pp, shared by the eight panels so that the steps at 2019 compare across
subareas; 48.6S sets the floor.

- One line per outcome, recruitment success and the five constraints that
  act on the larvae (M1, M4, M5a, M5b, M6), in FS1's colours with small open
  markers on every year; a zero line; the forcing switch dotted.
- Panel labels as left-aligned titles, subarea code and name, as F3.
- One legend below the panels, success first then the constraints in the
  order they act.
- Arial 8–9 pt, text kept as text in the PDF (Type 42 fonts).

## Files

- `aggregate.py` — a copy of `FS1_ice_product/aggregate.py`, kept so the
  folder runs alone; `--source nsidc|glorys12|glorys12_25km` selects the
  classification, `--compare` checks the counts against FS1's aggregate of
  the same reading.
- `data/aggregated_<source>.nc`, `data/cohort_sha256_<source>.txt` — one
  per reading, the schema of FS1's: particle counts per (spawning year,
  season day, subarea, outcome), by release position and by fate position,
  48.6 split at 60°S, with the sha256 of the 3 840 cohort files read.
- `plot.py` — reads the three aggregates, writes `ice_product_subarea.pdf`
  and `.png`; prints, per subarea, the season-mean success and M1 share
  per year under the three readings, the shift tables of FS1 (product,
  resolution and total differences per outcome, with the ice-state check)
  and the decomposition of each total shift; then, across subareas, the
  total shift at 2019 per outcome with its ice-state check and the product
  shift, the 32-year mean resolution difference, and the largest
  single-year product difference per outcome.

## Provenance

As FS1: the three classifications of `krico-post-production` on Paper 1's
trajectories, read through `aggregate.py` with the same provenance checks
(the attributes of every cohort file identify one reading and no other;
outcome codes; counts summed over subarea and outcome equal the releases of
every day). The counts are identical to those of
`FS1_ice_product/data/aggregated_<source>.nc` for each reading; `plot.py`
checks that the three aggregates carry the readings they claim and the
same releases per day.

## Run

```bash
export KRICO_POST=/path/to/krico-post-production   # directory holding recruitment/data*/
python aggregate.py --source nsidc         --compare ../FS1_ice_product/data/aggregated_nsidc.nc
python aggregate.py --source glorys12      --compare ../FS1_ice_product/data/aggregated_glorys12.nc
python aggregate.py --source glorys12_25km --compare ../FS1_ice_product/data/aggregated_glorys12_25km.nc
python plot.py                                     # needs only data/aggregated_*.nc
```
