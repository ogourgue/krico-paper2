# zw3 — zonal wave 3 magnitude and phase (Goyal et al. 2022), computed from ERA5

The three-crest meander of the Southern Hemisphere westerlies, measured
as Goyal, Jucker, Sen Gupta & England (2022, *J. Climate* 35, 5137–5149)
define it: monthly anomalies of ERA5 500 hPa meridional wind over
40–70°S (relative to the 1979–2020 monthly climatology), the two leading
√cos-latitude-weighted EOFs of those anomalies over 1979–2020, their
principal components scaled to unit variance, and from them the
**magnitude** √(PC1² + PC2²), dimensionless, and the **phase**
atan2(PC2, PC1) in degrees from −180 to 180, which says where the three
ridges sit (a full cycle of phase moves the pattern by 120° of
longitude). Months after 2020 are projected onto the same EOFs with the
same scaling, so the index is defined identically across 1979–2025. Four
files, schema year,month,value: `zw3_magnitude_monthly.csv`,
`zw3_phase_monthly.csv`, `zw3_pc1_monthly.csv`, `zw3_pc2_monthly.csv`.
Sign convention: the EOF signs are arbitrary and are set to match the
published series over 1979–2020 (correlations in `PROVENANCE.md`,
expected above 0.95); only if no reference file is present does
`compute.py` fall back to a geometric rule stated in its docstring.
§5's use is phase composites only, no linear correlation with magnitude:
a large wave with its cold flank over the Weddell–Peninsula sector is
the opposite of a large wave with its warm flank there, so months are
grouped by phase and the ice outcomes compared across groups; the index
is ranked last and is dropped if the composites show nothing. Source:
ERA5 monthly means on pressure levels (Copernicus Climate Data Store,
doi:10.24381/cds.6860a573; Hersbach et al. 2020), v at 500 hPa, 1979 to
the last complete month, 40–70°S, regridded by the CDS to 1° × 1°, request
committed as `raw/era5_request.json` and fetched by `fetch.py` through
the `cdsapi` package (free CDS account, API key in `~/.cdsapirc`, licence
accepted once); the published 1979–2020 series from Mendeley Data
doi:10.17632/382gmc8937.1 is downloaded to `raw/mendeley/` for the
overlap check; the authors' notebook
<https://github.com/rishavgoyal55/NEW-ZONAL-WAVE-3-INDEX> is the method
of record and `compute.py` reproduces it with a plain SVD. Period
1979-01 to the last ERA5 month at the fetch date; the paper uses
1993–2025. Caveats: the published series is not maintained as data
(SCAR AntClimNow replots it to the present but serves only figures), so
the extension past 2020 is ours; the authors' grid is not stated, and 1°
is adequate for a three-crest wave, with the overlap correlations as the
check; the ERA5 file is the one `raw/` item too large to read by eye
(about 25 MB) and is committed because ERA5 is CC-BY 4.0; the index is
built on ERA5 throughout and is therefore homogeneous across the
end-2018 GLORYS12 forcing switch, which is the point of using it. Licence:
CC-BY 4.0 for ERA5 and for the Mendeley files; cite Goyal et al. (2022)
and Hersbach et al. (2020).
