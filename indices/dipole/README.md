# dipole — Antarctic Dipole, computed from the NSIDC sea-ice CDR

The ENSO-driven see-saw of Antarctic sea ice between the Pacific and
Atlantic sides (Yuan & Martinson 2000, *J. Climate* 13, 1697–1717), built
here as §5 defines it: the sea-ice area anomaly in a Bellingshausen–
Amundsen sector (130°W–60°W, beside 88.3) minus the sea-ice area anomaly
in a Weddell sector (60°W–20°W, upstream of 48.2 and 48.4), in 10⁶ km².
Sea-ice area is Σ concentration × cell area over the sector's ocean
cells, computed daily from the NOAA/NSIDC G02202 v6 Climate Data Record
of passive-microwave sea-ice concentration (25 km polar stereographic
grid) and averaged by month; cell areas follow the projection's scale
factor (625 km² at 70°S, 664 at the pole, 518 at 50°S); anomalies are
departures from the 1994–2024 monthly climatology, the complete calendar
years in the holding. Six files, schema year,month,value:
`dipole_monthly.csv`, the index; `dipole_extent_monthly.csv`, the same
built on extent (cells ≥ 15%), closer to Yuan & Martinson's ice-edge
construction; and the four raw sector series `dipole_sia_pacific`,
`dipole_sia_weddell`, `dipole_sie_pacific`, `dipole_sie_weddell`, kept so
the base period can be changed in `tidy.py` without ECMWF. Sign
convention: positive = more ice on the Pacific side than on the Weddell
side, relative to climatology; §5 expects + M1 at 88.3 and − M6 at 48.4,
near-tautological because the index is sea ice, and states the real
test as the Dipole against Niño 3.4 at lags 0–3 months, where the
literature gives r of 0.4–0.5. Source: the daily G02202 v6 southern-
hemisphere files held on ECMWF under `$KRICO_NSIDC`, stacked by month
by `krico-post-production` (`preprocess_nsidc.py`), with the NSIDC
ancillary grid file for latitude, longitude and the ocean mask;
`compute.py --nsidc-dir $KRICO_NSIDC` runs there and writes
`raw/daily_sectors.csv` (one row per day, both sectors, area and extent,
valid-cell counts) and `raw/sectors.json`; `tidy.py` runs on the laptop.
October 1993 to October 2025, 385 months, the KRICO holding. Caveats: a
day with fewer than half of a sector's cells valid is left empty and a
month with fewer than 20 such days is left empty, both listed by the
scripts; the sector bounds are the methodology's, not Yuan & Martinson's
narrower boxes, and the Weddell sector includes the Peninsula's east
coast from 60°W; the CDR's ice concentration is itself the field the
paper's M1 and M6 are read from, so correlations with those outcomes
measure consistency, not cause; this index is the one §5 keeps for the
88.3–48.4 anticorrelation and the one P2-D10 says could change the
journal choice if it delivers. Licence: G02202 is in the public domain;
cite Meier et al., doi:10.7265/b18j-z797, and Yuan & Martinson (2000).
