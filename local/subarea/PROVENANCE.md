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

## Computed series (compute.py)

- Run: 2026-10-20 UTC
- Spawning cells: `raw/spawning_cells.csv`, 35303 GLORYS12 cells with 1000-2000 m depth in areas 48.1, 48.2, 48.3, 48.4, 48.5, 48.6, 88.3, 546199 particles per release day (545807 after the domain filter); from `glorys12_bathymetry.nc` (sha256 `75fd8a5eef6a…`) and `CCAMLR_ASD_EPSG4326.shp` (sha256 `e468d4952d0f…`); per area 48.1: 2681 cells / 49193 particles, 48.2: 3903 cells / 81670 particles, 48.3: 2900 cells / 93606 particles, 48.4: 1459 cells / 34586 particles, 48.5: 11674 cells / 99357 particles, 48.6: 9414 cells / 155651 particles, 88.3: 3272 cells / 32136 particles
- ERA5 input: `raw/era5_sector_monthly_stream-moda_stepType-avgad.nc` (`71bdb9c98099…`), `raw/era5_sector_monthly_stream-moda_stepType-avgua.nc` (`722d27ec39c2…`); 396 months 1993-01 to 2025-12; 5027 ocean grid points
- Bands (cells, total weight, ERA5 points used, cells whose nearest point was land, max distance km): 883: 3272, 32136, 74, 7, 59; 481: 2681, 49193, 64, 86, 67; 482: 3903, 81670, 77, 0, 62; 484: 1459, 34586, 33, 0, 62
- Boxes: south_orkney: [-62.5, -60.0, -48.0, -41.0] (24 ocean points); nw_weddell: [-65.0, -59.5, -55.0, -39.0] (102 ocean points); weddell_gyre: [-70.0, -62.0, -60.0, 0.0] (542 ocean points); north_edge: [-60.0, -55.0, -35.0, -20.0] (96 ocean points)
- Weddell Gyre curl mean -1.29 x 1e-7 N m-3 (negative = cyclonic in the Southern Hemisphere)
- SST box ice check: at most 74% of its points at the freezing floor (2014-09); within Mar-Jun at most 36% (2016-06)
- Output: v10_band_883_monthly.csv, t2m_band_883_monthly.csv, v10_band_481_monthly.csv, t2m_band_481_monthly.csv, v10_band_482_monthly.csv, t2m_band_482_monthly.csv, v10_band_484_monthly.csv, t2m_band_484_monthly.csv, u10_south_orkney_monthly.csv, v10_south_orkney_monthly.csv, u10_nw_weddell_monthly.csv, v10_nw_weddell_monthly.csv, curl_weddell_gyre_monthly.csv, sst_north_edge_monthly.csv
