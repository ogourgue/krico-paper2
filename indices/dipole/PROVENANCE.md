# Provenance: Antarctic Dipole sector series (indices/dipole)

Written by `compute.py`; do not edit by hand. Machine-readable copy in
`compute_log.json`.

- Source product: G02202 v06r00, doi:10.7265/b18j-z797
- Input: 385 monthly stacks `nsidc_ice_YYYY_MM.nc` under `/scratch/cvan/KRICO/Pre/NSIDC`
  (nsidc_ice_1993_10.nc to nsidc_ice_2025_10.nc), produced by `krico-post-production/recruitment/scripts/preprocess_nsidc.py`; stack title: NOAA/NSIDC CDR of Passive Microwave Sea Ice Concentration v6, southern hemisphere, daily, stacked by month for KRICO
- Ancillary grid file: `ancillary/G02202-ancillary-pss25-v06r00.nc`
- Computed: 2026-10-17T06:05Z
- Days: 11719, 1993-10-01 to 2025-10-31
- Days with a sector below 50% valid cells (value left empty): none
- Sectors (ocean cells, ocean area in 1e6 km2):
  - pacific: -130.0 to -60.0 E, 13775 cells, 7.985
  - weddell: -60.0 to -20.0 E, 13522 cells, 7.5391
- Output: `raw/daily_sectors.csv` (daily sea-ice area and extent per sector, 1e6 km2) and `raw/sectors.json`
- sha256 of inputs: in `compute_log.json`
- Licence: G02202 is in the public domain (NOAA/NSIDC); cite Meier, W. N. et al., NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration, Version 6, doi:10.7265/b18j-z797, and Yuan, X. & Martinson, D. G. (2000), J. Climate 13, 1697-1717, for the Dipole.
