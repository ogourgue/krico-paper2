# orcadas_fill — the Orcadas temperature series with its seven weak 2020–2023 months filled from ERA5

The station series of `../../indices/orcadas/` is the
index of record for the thermometer where M6 is decided (Murphy et al.
2014), but seven May–July means in 2020–2023 (2020-05, 2021-05/06/07,
2022-06, 2023-06/07) rest on fewer than 90% of the four daily reports,
READER's threshold, and all fall in the test period. This folder fills
them from ERA5 2 m temperature at the station: `compute.py` interpolates
the ERA5 field to 60.7°S 44.7°W, compares it with the station in every
month of 1993–2025 where the percentage of reports is at least 90 (which
also excludes 2002–2003 at 75%), learns the offset between model and
thermometer for each calendar month, and writes
`orcadas_filled_monthly.csv`, the station series in °C with exactly those
seven values replaced by ERA5 minus the offset of their calendar month,
`orcadas_filled_flag_monthly.csv` (0 station, 1 filled) and
`era5_t2m_orcadas_monthly.csv`, the ERA5 point series as served (K);
the station files are read by path and never written. Inputs from
`fetch.py` into `raw/`: ERA5 monthly means (Hersbach et al. 2020) of
`t2m` (K) and the land-sea mask `lsm` (0–1, constant in time) over
60–62°S, 43–46°W, 1993-01 to 2025-12, on the native 0.25° grid (9 × 13
points, under 1 MB), fetched from the Climate Data Store
(doi:10.24381/cds.f17050d7) through `cdsapi` with the request committed
as `raw/era5_request.json`; `fetch.py` records the hash, the structure,
the `expver` check (0001 throughout) and the land fraction of the four
points around the station, and `fetch.py --check` compares a re-fetch
with the log. Sign convention: °C as the station publishes, warmer is
larger; the ERA5 file keeps Kelvin. Caveats: the field file is not
committed (versioned, DOI'd, re-downloadable; the request and sha256 are
the record); a 0.25° ERA5 cell at the South Orkneys is a mix of sea and
ice-covered island, so the offset is expected to be seasonal and is
learned per calendar month rather than assumed constant, and the
nearest-point alternative is reported beside the bilinear one in
`PROVENANCE.md` so the choice can be judged; the offsets, correlation
and residual error of the clean-year comparison are in `PROVENANCE.md`
and `compute_log.json`, and so are the seven replaced values next to the
weak station values they replace; the fill is a model value and is
flagged as such, so any result that hinges on one of the seven months
must be checked against the flag; months of 2020–2025 below the 90% rule
outside the seven are listed by `compute.py` but left as published,
because the design uses May–July only; the station file in
`../../indices/orcadas/` is revised by READER as operators supply full
records, so a re-fetch there changes the inputs here and `compute.py
--check` will say so. Licence: CC-BY 4.0
for ERA5, cite Hersbach et al. (2020, *QJRMS* 146, 1999–2049,
doi:10.1002/qj.3803) and the dataset DOI; the station series is Open
Government Licence v3.0, cite Turner et al. (2004, *J. Climate* 17,
2890–2898).
