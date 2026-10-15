# Provenance: NOAA CPC ENSO indices (indices/nino34)

Written by `fetch.py`; do not edit by hand. The download history is
kept in `fetch_log.json`.

- Index page: <https://www.cpc.ncep.noaa.gov/data/indices/index.shtml>, saved verbatim as `raw/index.shtml`
- ONI page: <https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/>
- RONI page: <https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/>
- Downloaded (current `raw/` data): 2026-10-15 UTC
- Last checked against the remote: 2026-10-15 UTC
- sha256 page: `65a2d533a4d615ea05447184118c1c91856a95d1797e3d64ef227a211a4e7045`
- Data files:
  - `detrend.nino34.ascii.txt` <https://www.cpc.ncep.noaa.gov/data/indices/detrend.nino34.ascii.txt>: 30459 bytes, 922 rows, 1949-12 to 2026-09, sha256 `3690a7883ef3e2a4d22fa5193e7294617de0fdf46b3398a56df11db74467a8e9`
  - `Rnino34.ascii.txt` <https://www.cpc.ncep.noaa.gov/data/indices/Rnino34.ascii.txt>: 14768 bytes, 922 rows, 1949-12 to 2026-09, sha256 `a3a03f128f6d340199998c7b4dd0d6023d237008daf3e93e6e4a776f9a78a9db`
  - `oni.ascii.txt` <https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt>: 23025 bytes, 920 rows, 1950-01 to 2026-08, sha256 `5d6fa3a2f857d916550d39c2c686e94cb942430195c82518e6a5d0f5ffbd0665`
  - `RONI.ascii.txt` <https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt>: 14736 bytes, 920 rows, 1950-01 to 2026-08, sha256 `24d79a53c8c30aaf32200c08447291655fc1d693f11165793ba6d3aa378d98ff`
- Version note:
  As labelled on the CPC indices page on 15 October 2026: Niño 3.4
  (detrend.nino34) and the ONI are computed from ERSSTv6 with centered
  30-year base periods updated every 5 years; the relative Niño 3.4
  (Rnino34) and the RONI from ERSSTv6 with the 1991-2020 base period, the
  Niño 3.4 anomaly minus the tropical-mean (20N-20S) SST anomaly, rescaled
  to the variance of Niño 3.4. CPC moved these files from ERSSTv5 to
  ERSSTv6 in 2026 (the ONI table moved to oni/v6/, v5 kept for reference)
  and, per NWS Public Information Statement 26-05, now uses the RONI for
  official ENSO monitoring while continuing to update the ONI. The most
  recent two months are provisional (high-frequency filter on ERSSTv6).
- Licence: US Government work, no licence stated. Cite NOAA Climate Prediction Center (the indices page and the ONI/RONI pages) and Huang et al. for ERSSTv6; CPC's page cites Huang et al. (2025, J. Climate, Parts 1 and 2).

## Download history

- 2026-10-15: detrend.nino34.ascii.txt initial download, ends 2026-09; Rnino34.ascii.txt initial download, ends 2026-09; oni.ascii.txt initial download, ends 2026-08; RONI.ascii.txt initial download, ends 2026-08
