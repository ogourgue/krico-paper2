# Provenance: ERA5 monthly surface fields over the sector (local/subarea)

Written by `fetch.py`; do not edit by hand. Machine-readable copy in
`fetch_log.json`.

## Source

- Dataset: reanalysis-era5-single-levels-monthly-means (doi:10.24381/cds.f17050d7), ERA5 monthly averaged data on
  single levels, Copernicus Climate Data Store
- Request: `raw/era5_request.json`, monthly means of u10, v10, t2m, sst, metss, mntss,
  1993-01 to 2025-12, 115W to 40E, 40S to 90S, 1.0 x 1.0 degree (regridded by the CDS from the native 0.25)
- Licence: CC-BY 4.0; cite Hersbach, H. et al. (2020), QJRMS 146, 1999-2049,
  doi:10.1002/qj.3803, and the dataset DOI

## Last download

- Date: 2026-10-20 UTC, cdsapi ?
- File: `raw/era5_sector_monthly_stream-moda_stepType-avgua.nc` (CDS member `data_stream-moda_stepType-avgua.nc`), 22156391 bytes, sha256 `722d27ec39c26329453f30f94763c7e635b6732d2447ae9180e136e8cb03ebf1`
- File: `raw/era5_sector_monthly_stream-moda_stepType-avgad.nc` (CDS member `data_stream-moda_stepType-avgad.nc`), 11236388 bytes, sha256 `71bdb9c98099c11967772af115eb9fb600093340b70f4918112e33668dad7c3a`
- Structure: dims {'valid_time': 396, 'latitude': 51, 'longitude': 156}, 396 months 1993-01 to 2025-12; variables u10 [m s**-1], v10 [m s**-1], t2m [K], sst [K], metss [N m**-2] (served as avg_iews), mntss [N m**-2] (served as avg_inss)
- Sign check: mean eastward stress over ocean 50-60S = +0.159 N m-2 (positive = eastward push on the surface)
- Previous download: identical values in every month

The field files are not committed; a run of `fetch.py` reproduces them and
`fetch.py --check` compares the result with the hashes above.

