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
| `F1_timeseries` | Figure 1 — interannual recruitment time series, domain and per subarea | domain panels done; per-subarea awaiting ECMWF run |

`ccamlr-data/` holds the CCAMLR statistical-area shapefile (EPSG:4326),
copied from krico-paper1 so this repo is self-contained.

## Reproducing

Each `F*` folder reads committed `data/*.nc` with `plot*.py` scripts and
needs no HPC access; the `aggregate*.py` scripts that produce those files
run on ECMWF against `$KRICO_POST/recruitment/data/`. Per-folder READMEs
give the details.

## License

GPL-3.0, as the other KRICO repositories.
