`aggregated_subarea_nsidc.nc` is produced by `../aggregate_nsidc.py` on
ECMWF from `$KRICO_POST/recruitment/data_nsidc/`, the recruitment
classification rerun with NSIDC G02202 v6 sea ice (krico-post-production,
branch `nsidc-ice`, `run_year_nsidc.sh`). Same schema as
`../../timeseries/data/aggregated_subarea.nc`; the `sic_source` and
`source_data_dir` attributes identify the ice product and input directory.
