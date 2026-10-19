# Provenance: zonal wave 3 inputs (indices/zw3)

Written by `fetch.py`; do not edit by hand. Machine-readable copy in
`fetch_log.json`. The index itself is computed by `compute.py`, which
appends its own section to this file.

## ERA5

- Dataset: reanalysis-era5-pressure-levels-monthly-means (doi:10.24381/cds.6860a573), Copernicus Climate Data Store
- Request: `raw/era5_request.json` (v at 500 hPa, monthly means, 1979-2026, 40-70S, 1 x 1 degree)
- File: `raw/era5_v500_monthly.nc`, 15198075 bytes, sha256 `1d789cdf59ec2d160e8df74c63ed5ca08c4335d8e2caffef78f4d7930e3c3928`
- Downloaded: 2026-10-19 UTC
- Licence: CC-BY 4.0; cite Hersbach, H. et al. (2020), QJRMS 146, 1999-2049, doi:10.1002/qj.3803, and the dataset DOI

## Goyal et al. (2022) reference series

- Mendeley Data doi:10.17632/382gmc8937.1, listed through the public API, downloaded 2026-10-19 UTC into `raw/mendeley/`
  - `zw3index_Goyaletal2022.csv`: 24831 bytes, sha256 `6d1192401bf8f2b6edca3c4379e5a053bde9cf34d16ec322ba3ef21978e18371`
  - `ZW3index_Goyaletal2022JCLI.nc`: 114707 bytes, sha256 `cfc407f93c5b28c01025bf68813860fb97c375516e5e5a571ee1de835f8df402`
- Licence: CC-BY 4.0; cite Goyal, R., Jucker, M., Sen Gupta, A. & England, M. H. (2022), J. Climate 35, 5137-5149, doi:10.1175/JCLI-D-21-0927.1

## Computed index (compute.py)

- Run: 2026-10-19 UTC on `raw/era5_v500_monthly.nc` (sha256 `1d789cdf59ec…`), 31 x 360 grid, 573 months, 1979-01 to 2026-09
- Climatology and EOF period: 1979-2020; variance fraction of EOF1-4: 21.1%, 16.6%, 11.6%, 10.9%
- Sign alignment: {"status": "aligned to reference", "months": 518, "swapped": false, "sign_pc1": -1, "sign_pc2": -1, "r_pc1": 0.9998, "r_pc2": 0.9994, "r_magnitude": 0.9991, "reference_file": "ZW3index_Goyaletal2022JCLI.nc"}
- Output: zw3_magnitude_monthly.csv, zw3_phase_monthly.csv, zw3_pc1_monthly.csv, zw3_pc2_monthly.csv
