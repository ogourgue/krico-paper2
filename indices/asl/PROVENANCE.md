# Provenance: Amundsen Sea Low index (indices/asl)

Written by `fetch.py`; do not edit by hand. The download history is
kept in `fetch_log.json`.

- Data file: <https://files.bas.ac.uk/twins/asli/asli_calculation_latest.csv>, saved verbatim as `raw/asli_calculation_latest.csv`
- Landing page: <https://scotthosking.com/asl_index>, saved verbatim as `raw/asl_index.html`
- Code: <https://github.com/antarctica/asli>
- Downloaded (current `raw/` data): 2026-10-15 UTC
- Last checked against the remote: 2026-10-15 UTC
- sha256 data: `c30f16bc2fd011f0db503808eb59128a2a4f2430b00f4e8e302ecf02925488c5`
- sha256 page: `8691949378b5c5fa0f71dfbb03a5bdbae93c4edfd91981a4f32b65d490a81958`
- Size: 48502 bytes, 811 months
- First month: 1959-01
- Last month: 2026-07
- File header, as read:
  - id: asli_3.20240813_20261010
  - product_version: 3.20240813
  - source: asli 0.2.8
  - date_created: 20261010
  - time_coverage_start: 1959-01-01
  - time_coverage_end: 2026-07-01
- ERA5T (provisional) months: none
- Version note:
  ASLI version 3 (Hosking et al. 2016 method, Python package `asli`,
  ERA5 monthly mean sea level pressure, sector 170-298 E, 80-60 S); the
  exact product version, package version and creation date are read from
  the file header and listed above. The file's own notes: relative central
  pressure is actual minus sector-mean pressure; data_source is ERA5
  (final) or ERA5T (initial release, provisional); a known ERA5 issue
  affects pressure values and ASL location for May-October 1996 (ECMWF
  ERA5 known issue 30). The remote file is overwritten monthly; the former
  BAS page bas.ac.uk/data/absl/ is gone (404 on 15 October 2026) and the
  GitHub README says the dataset is to move to the UK Polar Data Centre.
- Licence: No licence stated for the data file; the asli code is MIT. Cite Hosking, J. S., Orr, A., Bracegirdle, T. J. & Turner, J. (2016), GRL 43, 367-376, doi:10.1002/2015GL067143; the asli package (Wyld, Zwagerman & Hosking, doi:10.5281/zenodo.20327186); and ERA5 (doi:10.24381/cds.adbb2d47).

## Download history

- 2026-10-15: asli_3.20240813_20261010, last month 2026-07, sha256 `c30f16bc2fd0…`; initial download
