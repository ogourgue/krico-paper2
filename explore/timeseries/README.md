# explore/timeseries — interannual recruitment time series (meeting drafts)

Figures are slide-sized (9.32 × 3.74 in, Google Slides content area), no
panel labels. Paper versions will be new `F*` folders.

| Script | Runs where | Input | Output |
|---|---|---|---|
| `plot_domain.py` | locally | `data/aggregated_domain.nc` (committed; see `data/PROVENANCE.md`) | `timeseries_domain.png` + stdout table |
| `aggregate_subarea.py` | locally | `$KRICO_POST/recruitment/data/*.nc` + `../ccamlr-data/` | `data/aggregated_subarea.nc` (~1 MB; commit once produced) |
| `plot_subarea.py` | locally | `data/aggregated_subarea.nc` | `timeseries_subarea_release.png` (composition) and `success_subarea_release.png` (success rates on one axis); `--by fate` for fate subareas |

Conventions follow krico-paper1: season-day grid (0 = Nov 15, 119 = Mar 14),
Feb 29 excluded, censored folded into M6, F3 palette, 48.6 split at 60°S.

## Aggregation

`aggregate_subarea.py` walks `$KRICO_POST/recruitment/data/` (run locally,
like the paper1 aggregations). Subarea assignment uses a 0.05° lookup raster
of the shapefile. The run ends by printing per-outcome totals, which must
match `aggregated_domain.nc` exactly, and the fraction of release positions
outside any subarea, which must be ~0.

## Status (2 October 2026)

Domain and per-subarea panels done from real data (aggregated_subarea.nc
produced 2 October).
No climate index, no significance, no treatment of the end-2018 forcing step
beyond marking it.
