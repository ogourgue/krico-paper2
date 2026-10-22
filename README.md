# KRICO: Paper 2

Figures and analysis for KRICO Paper 2: interannual variability of Antarctic
krill larval recruitment potential, 1994–2025, from the same Lagrangian
hindcast as Paper 1. Working title and framing to be settled after the
October 2026 meeting with the climate co-authors.

Author: Olivier Gourgue (RBINS)

Related repositories:

* __[krico-templates](https://github.com/ogourgue/krico-templates)__ — Simulation templates (Parcels + GLORYS12v1)
* __[krico-post-production](https://github.com/ogourgue/krico-post-production)__ — Post-processing and recruitment classification pipeline
* __[krico-paper1](https://github.com/ogourgue/krico-paper1)__ — Paper 1 figures (phenology and sea-ice mortality mechanism)

## Folder naming

Same scheme as krico-paper1, plus one folder for work in progress:

- `F*` — main-text figures.
- `FS*` — Supporting Information figures.
- `S*` — supporting analyses that produce no figure.
- `explore/` — analyses that have not yet earned a prefix. A folder moves out
  of `explore/` only once a figure or statement in the manuscript depends on
  it; what never does is pruned or moved to `krico-private-notes` before the
  Zenodo release.

| Folder | Manuscript item | Status |
|---|---|---|
| `F1_domain_map` | Figure 1 — map: (a) Paper 1's Fig. 1; (b) index regions | not started, built last |
| `F2_domain_timeseries` | Figure 2 — domain time series, success and composition, NSIDC ice | done |
| `F3_subarea_record` | Figure 3 — per-subarea record, four recruiting subareas, success and composition, NSIDC ice | done |
| `FS1_ice_product` | Figure S1 — the classification under three ice readings (GLORYS12, GLORYS12 on the 25 km grid, NSIDC): domain success, product and resolution differences per outcome | done |
| `FS2_ice_product_subarea` | Figure S2 — the product difference per outcome in each of the eight release subareas | done |

`ccamlr-data/` holds the CCAMLR statistical-area shapefile (EPSG:4326),
copied from krico-paper1 so this repo is self-contained.

## Reproducing

Each `F*` and `FS*` folder reads its committed `data/*.nc` with `plot.py`
and needs nothing else; the `aggregate.py` in the same folder produces those
files from the cohort files of the recruitment classification
(`$KRICO_POST/recruitment/`, the output of krico-post-production), and
records the sha256 of every file it read. Per-folder READMEs give the
details.

## License

GPL-3.0, as the other KRICO repositories.
