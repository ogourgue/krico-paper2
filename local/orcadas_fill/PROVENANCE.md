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

## Computed fill (compute.py)

- Run: 2026-10-20 UTC on `raw/era5_orcadas_monthly.nc` (`e56efd897e59…`) and `orcadas_monthly.csv` (`6cb77eae7789…`), `orcadas_obs_pct_monthly.csv` (`1032ce8b12bf…`)
- ERA5 at the station: bilinear between [-60.75, -44.75] and [-60.5, -44.5], weights [0.64, 0.16, 0.16, 0.04]; nearest point [-60.75, -44.75], land fraction 0.01
- Clean months (1993-2025, >= 90% of reports): n = 347, r = 0.988, station minus ERA5 = +0.03 degC on average, RMSE 0.82 raw and 0.51 after the per-month offset (nearest point instead of bilinear: r = 0.988, RMSE after offset 0.51)
- Offset per calendar month (station minus ERA5, degC; n): 01: +0.70 (31), 02: +0.56 (29), 03: +0.36 (31), 04: -0.15 (29), 05: -0.44 (29), 06: -0.87 (28), 07: -1.06 (29), 08: -0.65 (28), 09: -0.27 (29), 10: +0.47 (29), 11: +0.88 (28), 12: +0.76 (27)
- Fills (station value at its percentage -> ERA5 + offset): 2020-05: -8.1 at 47% -> -6.6; 2021-05: -1.4 at 71% -> -1.8; 2021-06: -5.9 at 70% -> -5.5; 2021-07: -8.8 at 73% -> -8.1; 2022-06: -4.8 at 81% -> -4.5; 2023-06: -5.1 at 85% -> -4.7; 2023-07: -8.4 at 86% -> -8.7
- Other 2020-2025 months below the rule, not filled: 2020-12 (89%), 2021-04 (70%), 2021-08 (73%), 2021-09 (72%), 2021-10 (67%), 2021-11 (74%), 2021-12 (70%), 2022-01 (73%), 2022-02 (74%), 2022-08 (80%), 2022-09 (84%), 2022-10 (65%), 2022-11 (87%), 2022-12 (86%), 2023-02 (85%), 2023-04 (87%), 2023-08 (81%), 2024-12 (89%)
- Output: orcadas_filled_monthly.csv, orcadas_filled_flag_monthly.csv, era5_t2m_orcadas_monthly.csv
