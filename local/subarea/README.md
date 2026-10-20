# subarea — ERA5 wind, temperature, stress and SST over the spawning bands and the fixed boxes

The tier-2 variables from the atmosphere, one monthly `year,month,value`
file per variable and region, fourteen files: `v10_band_<sub>_monthly.csv`
and `t2m_band_<sub>_monthly.csv` for `<sub>` in 883, 481, 482, 484, the
northward 10 m wind and the 2 m temperature over the spawning band of each
recruiting subarea, i.e. the mean over the band's release cells weighted
by the number of particles each cell releases, every cell taking the value
of the nearest ERA5 ocean grid point; `u10_south_orkney_monthly.csv`
and `v10_south_orkney_monthly.csv`, the eastward and northward 10 m wind
over the South Orkney Plateau box of Young et al. (2024), 60–62.5°S,
41–48°W, the box they correlate with local recruitment and retention
(stronger westerlies, positive `u10`, and northerlies, negative `v10`,
reduce both); `u10_nw_weddell_monthly.csv` and
`v10_nw_weddell_monthly.csv`, the same over their northwest Weddell Sea
box, 59.5–65°S, 39–55°W, which they correlate with regional recruitment
from upstream (stronger westerlies and northerlies increase it, with
averaging times of 3–6 months); `curl_weddell_gyre_monthly.csv`, the
wind-stress curl ∂τy/∂x − ∂τx/∂y over the Weddell Gyre box of Auckland
et al. (2024), 62–70°S, 60°W–0°, central differences on the 1° grid, in
units of 10⁻⁷ N m⁻³, negative = cyclonic (clockwise) in the Southern
Hemisphere, the sense that spins the gyre up and, after 5–13 months,
accelerates the export past the South Orkneys (Meijers et al. 2016, who
integrate the curl over the gyre but state no corners);
`sst_north_edge_monthly.csv`, sea surface temperature over 55–60°S,
20–35°W, the water the ice advances into in this sector, where the
September edge reaches 57–58°S, the regional form of the circumpolar
45–55°S band of Kusahara and Tatebe (2025). Box means are over ocean grid points (sea
surface temperature defined in every month, which includes ice-covered
ocean) weighted by cos(latitude), box edges inclusive. The spawning
bands are the committed table `raw/spawning_cells.csv`: the release cells
of the simulation, which are deterministic apart from a jitter within the
cell — a GLORYS12 cell with bathymetry between 1000 and 2000 m whose
centre lies in CCAMLR areas 48.1–48.6 or 88.3 releases
max(1, round(cell area in km²)) particles, jittered uniformly within the
cell, those jittered outside 76–41°S, 114°W–39°E discarded — rebuilt by
`compute.py --cells` from `$KRICO_GLORYS12/glorys12_bathymetry.nc` and the
CCAMLR shapefile in `../../ccamlr-data/` with a point-in-polygon test
written here, each cell labelled with its subarea and with the fraction
of its jitter box inside the filter window, so that the weights are
reproducible without any cohort file and the series without the 76 MB
bathymetry. All are computed by
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
which `compute.py` opens by that pattern, floors to the month and merges. Caveats: the three wind and curl boxes take
their corners from the papers named, the SST box is a regional
adaptation (Kusahara's own band lies north of South Georgia, far from the
ice here), and the eastward-stress box of the design, 60–65°S, 20–50°W,
is not computed because Meijers et al. (2016) define no such box and the
curl and the northwest Weddell wind carry that mechanism with published
corners; at 1° a box is 24–550 points and the bands sit on 20–110 points,
so neighbouring series are not independent; a release cell near the coast can have a land point as its
nearest grid point and is then moved to the nearest ocean point (counts
and the largest displacement are in `PROVENANCE.md`); the cell table is
recomputed in double precision where the simulation used single, so a
cell's particle count can differ by one at a rounding tie, immaterial for
weights; the shapefile is CCAMLR v0.6.3, the simulation read an earlier
copy of the same areas; the field files (about 33 MB) are not committed, because the CDS is a versioned, DOI'd
source anyone can re-download, and the sha256 in `PROVENANCE.md` and
`fetch_log.json` is the check (`fetch.py --check`; a re-fetch also logs
month by month which values moved); 1° is adequate for the boxes and the
spawning bands, the Orcadas station point is fetched separately at 0.25°
in `../orcadas_fill/`; ERA5 SST is set to the freezing point under sea
ice and is an interpolated product (HadISST2 before 2007, OSTIA after),
so `compute.py` reports the largest share of the SST box at the freezing
floor and the month it occurs (the box must stay north of the edge in
Mar–Jun to mean what Kusahara 2025 means);
ERA5 is homogeneous across the end-2018 GLORYS12 forcing switch, which is
the point of using it. Licence: CC-BY 4.0 for ERA5, cite Hersbach et al. (2020,
*QJRMS* 146, 1999–2049, doi:10.1002/qj.3803) and the dataset DOI; cite
CCAMLR for the statistical areas. Box sources: Young, Thorpe, Renner &
Murphy (2024, *J. Mar. Syst.* 241, 103920, doi:10.1016/j.jmarsys.2023.103920);
Auckland et al. (2024, *JGR Oceans*, doi:10.1029/2024JC021089); Meijers
et al. (2016, *JGR Oceans* 121, 7530–7546, doi:10.1002/2016JC011757);
Kusahara & Tatebe (2025, *GRL* 52, e2025GL115256, doi:10.1029/2025GL115256).
