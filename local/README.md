# local/

Local physical variables for Paper 2, the second tier of the index
analysis: between a large-scale climate index (`../indices/`) and a
recruitment outcome sits the local wind, temperature, stress or ice
timing over the subarea through which the index is supposed to act. An
index that correlates with an outcome but not with the local variable it
acts through is suspect; a local variable should correlate with the
outcome better than any index. Data, not exploration: this folder sits
beside `indices/` and `ccamlr-data/`. One self-contained subfolder per
variable group, each with

- `fetch.py` (for downloads) or `compute.py` (for derived quantities):
  writes the raw inputs or the reduced table into `raw/`, computes
  sha256, writes `PROVENANCE.md` and a machine-readable `fetch_log.json`;
  idempotent; `--check` compares what is in `raw/` with the last logged
  download and writes nothing. A `compute.py` runs where the gridded
  input lives (ECMWF for the NSIDC daily files) and leaves in `raw/` the
  small table `tidy.py` needs;
- `compute.py` or `tidy.py`: `raw/` → one monthly CSV per variable and
  region;
- `README.md`: definition, sign convention, source, period, caveats.

No shared code across subfolders and no imports from elsewhere in the
repository, so each folder runs on its own. Window files and the joined
year × subarea tables live with the analysis that uses them, not here.

## Groups

Each folder fetches its own inputs.

| Group | Folder | Variables | Source | Period |
|---|---|---|---|---|
| Subarea and box series from ERA5 | `subarea/` | `v10_band_<sub>`, `t2m_band_<sub>` (sub = 883, 481, 482, 484; weighted over the release cells of `raw/spawning_cells.csv`), `u10_south_orkney`, `v10_south_orkney` (60–62.5°S, 41–48°W, Young 2024), `u10_nw_weddell`, `v10_nw_weddell` (59.5–65°S, 39–55°W, Young 2024), `curl_weddell_gyre` (62–70°S, 60°W–0°, Auckland 2024, 10⁻⁷ N m⁻³), `sst_north_edge` (55–60°S, 20–35°W, after Kusahara 2025) | ERA5 monthly averaged data on single levels, Copernicus Climate Data Store, doi:10.24381/cds.f17050d7, request in `subarea/raw/era5_request.json`; GLORYS12 bathymetry and the CCAMLR shapefile for the cells | 1993-01 – 2025-12 |
| Orcadas fill | `orcadas_fill/` | `orcadas_filled` (station series, °C, seven 2020–2023 May–Jul months replaced by ERA5 plus a per-calendar-month offset learned in clean years), `orcadas_filled_flag` (0 station, 1 fill), `era5_t2m_orcadas` (ERA5 at the station, K) | ERA5 monthly averaged data on single levels, Copernicus Climate Data Store, doi:10.24381/cds.f17050d7, request in `orcadas_fill/raw/era5_request.json`, native 0.25°; station series and report percentages from `indices/orcadas/` | station 1903-04 – 2026-09, ERA5 1993-01 – 2025-12 |
| Ice timing | `ice_timing/` | `retreat_<sub>`, `advance_<sub>` (day-of-year, 365-day calendar) and `retreat_<sub>_share`, `advance_<sub>_share` (weight share with the event), sub = 883, 481, 482, 484; annual, one row per spawning year; Stammerjohn 15%/5-day with the 1 April cutoff of the classification; per-cell table in `ice_timing/raw/` | NOAA/NSIDC G02202 v6 daily, doi:10.7265/b18j-z797, stacked under `$KRICO_NSIDC` on ECMWF (`compute.py` there, `tidy.py` on the laptop) | spawning years 1994 – 2025 |

## Conventions

- Reduced tables use the `indices/` schema, `year,month,value`, one file
  per variable and region, calendar months, no seasonal averaging, no gap
  filling; the ice-timing series are annual by nature and use `year,value`
  with the spawning year (the one exception, the Orcadas fill, is a separate file that
  says so in its name and leaves the station file untouched). Windows
  (Oct–Jan for M1, Mar–Jul for M6, the 200-day drift for M5b) are applied
  in the analysis folder, after the expected signs are committed there.
- Regions are the four recruiting subareas, 88.3, 48.1, 48.2 and 48.4,
  taken over their spawning band (the 1000–2000 m release zone of the
  simulation, assigned to subareas with the CCAMLR shapefile in
  `../ccamlr-data/`), and fixed boxes named in each folder's README with
  their corners.
- Values keep the source's units and sign: ERA5 temperatures in K, wind
  in m s⁻¹ positive eastward (u) and northward (v), stress in N m⁻² as
  the stress exerted on the surface (positive eastward/northward push),
  wind-stress curl in 10⁻⁷ N m⁻³ with negative = cyclonic in the Southern
  Hemisphere, NSIDC days as day of year. A northerly wind is therefore a
  negative v; expected signs are written down in the analysis folder, not
  flipped here.
- Gridded ERA5 fields are not committed (versioned, DOI'd, re-downloadable
  source); the request file, sha256 and fetch log are the record. Small
  reduced tables and the station-scale series are committed.
