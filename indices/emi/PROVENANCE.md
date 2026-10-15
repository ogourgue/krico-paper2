# Provenance: El Nino Modoki Index (indices/emi)

Written by `fetch.py`; do not edit by hand. The download history is
kept in `fetch_log.json`.

- Data file: <https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_EMI.csv>, saved verbatim as `raw/SINTEX_EMI.csv`
- Method page: <https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html>, saved verbatim as `raw/data_download.html`
- Site: <https://www.jamstec.go.jp/virtualearth/general/en/index.html> (Menu > EMI)
- Downloaded (current `raw/` data): 2026-10-15 UTC
- Last checked against the remote: 2026-10-15 UTC
- sha256 data: `f363da8a58ffbcc2bd304b38fcd604444f9bf60c6b4bb4db4304729901160da9`
- sha256 page: `33162e7c5f3372c503f0ac84794f763a2d8126e448e9d9f90e1dd763b45403ce`
- Size: 42282 bytes, 537 observed months
- First month: 1982-01
- Last observed month: 2026-09
- Version note:
  No version number is published. As stated on the JAMSTEC data page on
  15 October 2026: monthly climate indices from 1982 to present based on
  NOAA OISST Ver.2, SST anomalies as deviations from the monthly
  climatology of 1983-2015; EMI defined after Ashok et al. (2007) as
  SSTA(box A) - 0.5 SSTA(box B) - 0.5 SSTA(box C) with A = 165E-140W,
  10S-10N, B = 110-70W, 15S-5N, C = 125-145E, 10S-20N. The former file
  aplinfo/sintexf/DATA/emi.monthly.txt is a stub redirecting to
  VirtualEarth. Observed values carry float noise and are rounded to five
  decimals by tidy.py.
- Licence: None stated; JAMSTEC disclaimer applies. Cite Ashok, K., Behera, S. K., Rao, S. A., Weng, H. & Yamagata, T. (2007), J. Geophys. Res. 112, C11007, doi:10.1029/2006JC003798, and JAMSTEC APL VirtualEarth as the data source.

## Download history

- 2026-10-15: last observed month 2026-09, sha256 `f363da8a58ff…`; initial download
