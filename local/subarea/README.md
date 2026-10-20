# subarea — ERA5 wind, temperature, stress and SST over the spawning bands and the fixed boxes

*Fetch stage; the paragraph below is completed when `compute.py` and its
monthly files are added.* The tier-2 variables from the atmosphere, one
monthly `year,month,value` file per variable and region: meridional 10 m
wind and 2 m temperature over the spawning band of each recruiting
subarea (88.3, 48.1, 48.2, 48.4); zonal surface stress over the northern
Weddell Sea, 60–65°S, 20–50°W; westerly and northerly 10 m wind over the
South Orkney plateau; wind-stress curl over the Weddell Gyre; sea surface
temperature north of the ice edge, 55–60°S, 20–35°W. All are computed by
`compute.py` from the gridded inputs that `fetch.py` downloads into
`raw/`: ERA5 monthly means (Hersbach et al. 2020) of six surface fields
over 115°W–40°E, 40°S to the pole, 1993-01 to 2025-12, on a 1° × 1° grid
regridded by the Climate Data Store from the native 0.25°: `u10` and
`v10`, the eastward and northward 10 m wind (m s⁻¹); `t2m`, the 2 m air
temperature (K); `sst`, the sea surface temperature (K); `metss` and
`mntss`, the mean eastward and northward turbulent surface stress
(N m⁻²), i.e. the time-mean push of the air on the surface, requested in
the `mean_*` form rather than the accumulated `ewss`/`nsss` (N m⁻² s per
day in the monthly dataset) so that no de-accumulation is needed. Sign
conventions, as ERA5 defines them: u and `metss` positive eastward, v and
`mntss` positive northward; the stress is the stress exerted on the
surface, so the westerly belt shows positive `metss` (`fetch.py` checks
this over the ocean at 50–60°S after every download). Values are kept as
served: Kelvin, float32, latitude descending in the file (readers sort
it), coordinates `valid_time`, `latitude`, `longitude`, with the scalar
`number` and the per-month `expver` (0001 = final ERA5; 0005 would be the
preliminary ERA5T, which the 1993–2025 period does not contain); the CDS
converter names the stresses `avg_iews` and `avg_inss` (time averages
of `iews`/`inss`, ECMWF's short names for the instantaneous eastward and
northward turbulent surface stress; earlier files used `metss`/`mntss`),
and `fetch.py` and `compute.py` accept both and call them `metss`/`mntss`. Source:
ERA5 monthly averaged data on single levels (Copernicus Climate Data
Store, doi:10.24381/cds.f17050d7), request committed as
`raw/era5_request.json` and fetched by `fetch.py` through the `cdsapi`
package (free CDS account, API key in `~/.cdsapirc`, licence accepted
once); the CDS returns the six fields as a zip of two NetCDF files,
`stream-moda_stepType-avgua` (monthly means of analyses: `u10`, `v10`,
`t2m`, `sst`) and `stream-moda_stepType-avgad` (monthly means of
forecast rates: the stresses), stamped at different hours of the same
month, and `fetch.py` unpacks them into `raw/era5_sector_monthly_*.nc`,
which `compute.py` opens by that pattern, floors to the month and merges. Caveats: the field files
(about 45 MB) are not committed, because the CDS is a versioned, DOI'd
source anyone can re-download, and the sha256 in `PROVENANCE.md` and
`fetch_log.json` is the check (`fetch.py --check`; a re-fetch also logs
month by month which values moved); 1° is adequate for the boxes and the
spawning bands, the Orcadas station point is fetched separately at 0.25°
in `../orcadas_fill/`; ERA5 SST is set to the freezing point under sea
ice and is an interpolated product (HadISST2 before 2007, OSTIA after),
so the SST box must be checked against the ice edge in the months used;
ERA5 is homogeneous across the end-2018 GLORYS12 forcing switch, which is
the point of using it. Licence: CC-BY 4.0; cite Hersbach et al. (2020,
*QJRMS* 146, 1999–2049, doi:10.1002/qj.3803) and the dataset DOI.
