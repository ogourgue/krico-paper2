# asl — Amundsen Sea Low index (ASLI v3)

Position and strength of the Amundsen Sea Low, the climatological low in the
Pacific sector, found each month as the minimum of ERA5 mean sea-level
pressure within 170–298°E, 80–60°S by the method of Hosking et al. (2016,
*GRL* 43, 367–376), implemented in the BAS `asli` package. Five variables,
one file each: `asl_longitude` (degrees east, 170–298; 298°E = 62°W, so
larger = further east, towards the Peninsula), `asl_latitude` (degrees
north, −80 to −60), `asl_pressure_actual` (hPa at the centre),
`asl_pressure_sector` (hPa, area mean over the sector) and
`asl_pressure_rel` (hPa, actual minus sector mean, hence negative: the
regional anomaly with the hemispheric SAM signal removed). §5 uses the
last and the first. Sign convention, values kept as published: a weaker
low is a less negative, i.e. larger, `asl_pressure_rel`, so §5's "weaker
low: + M1 in 88.3/48.1" is a positive correlation between the published
value and M1; "eastward shift: − M1 at 48.1, + M1 at 88.3" is a negative
and a positive correlation with `asl_longitude` as published. The landing
page words the relative pressure as sector minus actual; the file header
and the numbers say actual minus sector, and the file wins. Source: data
file <https://files.bas.ac.uk/twins/asli/asli_calculation_latest.csv>,
landing page <https://scotthosking.com/asl_index>, code and method
<https://github.com/antarctica/asli> (MIT); the §5 address
`bas.ac.uk/data/absl/` was a 404 on 15 October 2026 and the GitHub README
says the dataset is to move to the UK Polar Data Centre, so the URL may
move again. Monthly, January 1959 onward; July 2026 at the download of
15 October 2026 (product version 3.20240813, `asli` 0.2.8, created
10 October 2026, all read from the file header into `PROVENANCE.md`).
Caveats: the remote file is overwritten monthly with no version in its
name, so the header's id is the version of record; months flagged ERA5T
are provisional and are replaced by ERA5 final data about three months
later, and `fetch.py` logs every download that changes a value; a known
ERA5 defect affects pressures and ASL position for May–October 1996 (file
note [d], ECMWF ERA5 known issue 30), inside the M6 window of spawning
year 1996 and the M1 window of 1997; the detected minimum sits on the
sector boundary in a few months (170.0°E in 1959-08, 1963-04, 1963-05,
1964-08, 1966-01, 1972-01, 1972-09, 1979-01, 1991-02, 1993-01, 1997-02,
1998-03, 2002-11, 2016-04, 2016-07, 2021-04; 60.0°S in 2009-07, 2011-01),
which a composite or lag test should treat as censored positions rather
than as a signal. No licence is stated for the data; cite Hosking et al.
(2016), the `asli` package (doi:10.5281/zenodo.20327186) and ERA5
(doi:10.24381/cds.adbb2d47).
