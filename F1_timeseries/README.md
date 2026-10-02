# F1_timeseries — interannual recruitment time series (Figure 1, draft)

| Script | Runs where | Input | Output |
|---|---|---|---|
| `plot_domain.py` | locally | `data/aggregated_domain.nc` (committed; see `data/PROVENANCE.md`) | `timeseries_domain.png` + stdout table |
| `aggregate_subarea.py` | ECMWF | `$KRICO_POST/recruitment/data/*.nc` + `../ccamlr-data/` | `data/aggregated_subarea.nc` (~1 MB; commit once produced) |
| `plot_subarea.py` | locally | `data/aggregated_subarea.nc` | `timeseries_subarea_release.png` (`--by fate` for fate subareas) |

Conventions follow krico-paper1: season-day grid (0 = Nov 15, 119 = Mar 14),
Feb 29 excluded, censored folded into M6, F3 palette, 48.6 split at 60°S.

## ECMWF run

```bash
export KRICO_POST=/scratch/cvan/KRICO/Post/Production
cd F1_timeseries
python aggregate_subarea.py --limit 5     # smoke test
sbatch run_aggregate.sh                   # full walk; same wall time as paper1 F3 aggregate.py
```

Subarea assignment uses a 0.05° lookup raster of the shapefile (0.1 s per
cohort on top of the file read). The run ends by printing per-outcome totals,
which must match `aggregated_domain.nc` exactly, and the fraction of release
positions outside any subarea, which must be ~0.

## Status (2 October 2026)

Domain panels done from real data. Per-subarea panels await the ECMWF run.
No climate index, no significance, no treatment of the end-2018 forcing step
beyond marking it.
