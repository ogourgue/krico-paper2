# Provenance: ERA5 2 m temperature around Orcadas (local/orcadas_fill)

Written by `fetch.py`; do not edit by hand. Machine-readable copy in
`fetch_log.json`.

## Source

- Dataset: reanalysis-era5-single-levels-monthly-means (doi:10.24381/cds.f17050d7), ERA5 monthly averaged data on
  single levels, Copernicus Climate Data Store
- Request: `raw/era5_request.json`, monthly means of t2m, lsm,
  1993-01 to 2025-12, 46W to 43W, 60S to 62S, native 0.25 degree
- Licence: CC-BY 4.0; cite Hersbach, H. et al. (2020), QJRMS 146, 1999-2049,
  doi:10.1002/qj.3803, and the dataset DOI

## Last download

- Date: 2026-10-20 UTC, cdsapi ?
- File: `raw/era5_orcadas_monthly.nc`, 134437 bytes, sha256 `e56efd897e590f25520efb4d2318d493af4c9bc465fafbac1bad38ba6cce29e6`
- Structure: dims {'valid_time': 396, 'latitude': 9, 'longitude': 13}, 396 months 1993-01 to 2025-12; variables t2m [K], lsm [(0 - 1)]
- Land fraction around the station: {"-60.75,-44.75": 0.005654692649841309, "-60.75,-44.50": 0.015411972999572754, "-60.50,-44.75": 0.005413174629211426, "-60.50,-44.50": 0.0025734901428222656}
- Previous download: none

The field files are not committed; a run of `fetch.py` reproduces them and
`fetch.py --check` compares the result with the hashes above.

