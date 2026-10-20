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
Pruning before release: folders never run against the outcomes are
deleted; folders behind a negative result in the text stay.

## Groups

Build order: subarea, orcadas_fill, ice_timing, weddell_export. Rows are
added as folders are built; each folder fetches its own inputs.

| Group | Folder | Variables | Source | Period |
|---|---|---|---|---|
| Subarea and box series from ERA5 | `subarea/` | fetch stage: `raw/era5_sector_monthly*.nc` (`u10`, `v10`, `t2m`, `sst`, `metss`, `mntss`, monthly, 1° × 1°, 115°W–40°E, 40°S–pole); monthly files added with `compute.py` | ERA5 monthly averaged data on single levels, Copernicus Climate Data Store, doi:10.24381/cds.f17050d7, request in `subarea/raw/era5_request.json` | 1993-01 – 2025-12 |

## Conventions

- Reduced tables use the `indices/` schema, `year,month,value`, one file
  per variable and region, calendar months, no seasonal averaging, no gap
  filling (the one exception, the Orcadas fill, is a separate file that
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
  NSIDC days as day of year.
- Gridded ERA5 fields are not committed (versioned, DOI'd, re-downloadable
  source); the request file, sha256 and fetch log are the record. Small
  reduced tables and the station-scale series are committed.
