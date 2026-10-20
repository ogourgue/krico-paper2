# Provenance: sea-ice retreat and advance day on the release cells (local/ice_timing)

Written by `compute.py`; do not edit by hand. Machine-readable copy in
`compute_log.json`.

## Source

- NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration,
  G02202 v6 (doi:10.7265/b18j-z797), southern hemisphere, daily, 25 km polar
  stereographic grid (EPSG:3412), as stacked by month for KRICO
- Archive used: 1993-02-01 to 2026-02-28, 397 monthly stacks; sha256 of every stack and of the ancillary file in `compute_log.json`
- Release cells: `../subarea/raw/spawning_cells.csv` (sha256 `6c4f0e01f954…`)
- Licence: G02202 is in the public domain (NOAA/NSIDC); cite Meier, W. N. et al.,
  NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration,
  Version 6, and the DOI

## Computed table (compute.py)

- Run: 2026-10-20 UTC
- Cells: 35303 release cells placed on 2269 (cell, subarea) pairs (48.1: 242, 48.2: 356, 48.3: 316, 48.4: 146, 48.5: 270, 48.6: 746, 88.3: 193); projection check 0.000 m, placement check 17625 m; release cells beyond the grid's northern edge dropped: 345 (48.6: 345, 11917 particles, northernmost -50.00565); release cells on non-ocean NSIDC cells dropped: 263 carrying 2160 particles (48.5: 1060, 48.6: 1070, 88.3: 30); total weight kept 531730
- Ice years: 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026 (incomplete, archive ends 2026-02-28)
- Rule: ice when concentration > 15%, runs of >= 5 days; advance from 1 April; retreat = day after the last run; day-of-year on a 365-day calendar counted from 1 January of the ice year, past 365 for January-February of the next year
- Per subarea (weight share with an advance, with a retreat; weighted mean advance and retreat day; interpolated days): 48.1: 0.95, 0.84, 145, 296, 0; 48.2: 0.98, 0.97, 151, 328, 0; 48.3: 0.01, 0.01, 250, 265, 0; 48.4: 0.91, 0.91, 175, 326, 0; 48.5: 1.00, 0.10, 91, 387, 0; 48.6: 0.60, 0.47, 123, 357, 0; 88.3: 0.99, 0.58, 108, 369, 0
- Output: raw/cells.csv, raw/cell_timing.csv

