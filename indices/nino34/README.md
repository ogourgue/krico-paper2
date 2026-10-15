# nino34 — Niño 3.4, ONI and their relative versions (NOAA CPC)

ENSO measured by sea-surface temperature in the Niño 3.4 box of the
central equatorial Pacific (5°N–5°S, 170–120°W), from NOAA's ERSSTv6
analysis, in °C. Four files, one variable each. `nino34_monthly.csv`:
monthly SST anomaly in the box relative to a 30-year climatology centred
on the date and updated every 5 years, the monthly input to the ONI.
`oni_monthly.csv`: the Oceanic Niño Index, the 3-month running mean of
the same, NOAA's historical yardstick (El Niño at ≥ +0.5 °C, La Niña at
≤ −0.5 °C for five overlapping seasons). `nino34_rel_monthly.csv` and
`roni_monthly.csv`: the relative versions, the box anomaly minus the
tropical-mean (20°N–20°S) SST anomaly of the same month, rescaled to the
variance of Niño 3.4, against a fixed 1991–2020 base; CPC's official
monitoring index since NWS Public Information Statement 26-05, because
it removes the warming trend by construction. Seasonal rows (ONI, RONI)
are placed on the centre month of the season (DJF → January, …, NDJ →
December); the source's season year is already that of the centre month.
Sign convention, values kept as published: positive = warm, El Niño;
negative = cold, La Niña. §5 expects, for loss fractions, SON–DJF mean
positive with M1 in 88.3 and 48.1, and at lag 6 negative with M6 at 48.4;
ONI is the index of record for those statements (the literature the
paper compares itself to uses it), RONI the sensitivity check; a result
that holds under both is stated once in the methods. Source: NOAA
Climate Prediction Center indices page
<https://www.cpc.ncep.noaa.gov/data/indices/index.shtml>, files
`detrend.nino34.ascii.txt`, `oni.ascii.txt`, `Rnino34.ascii.txt`,
`RONI.ascii.txt`; ONI table and notes at
<https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/>,
RONI at <https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/>.
Monthly from December 1949 (one month early, to feed DJF 1950),
seasonal from DJF 1950; September 2026 and JAS 2026 at the download of
15 October 2026. Caveats: the files carry no version string and the
SST product is stated only on the index page, which `fetch.py` saves to
`raw/index.shtml`; CPC moved from ERSSTv5 to ERSSTv6 in 2026, which
shifts values by up to about 0.1 °C relative to the series in the
pre-2026 literature (v5 tables remain online); the most recent two
months are provisional and revised when the ERSSTv6 high-frequency
filter settles, and `fetch.py` logs every download that changes a value;
the §5 reference to "NOAA PSL climate-indices list" is dropped, because
PSL's "Niño 3.4 (ERSSTv5)" CSV is labelled OISST in its own header and
its 1950s values do not match CPC's. No licence is stated (US Government
work); cite CPC and Huang et al. (2025, *J. Climate*) for ERSSTv6.
