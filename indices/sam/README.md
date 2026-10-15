# sam — Marshall SAM index

Station-based Southern Annular Mode index of Marshall (2003, *J. Climate*
16, 4134–4143): the difference between the normalised zonal-mean sea-level
pressure at 40°S and at 65°S, each from six stations, normalised with
1971–2000 monthly means and standard deviations, so values are
dimensionless and lie within about ±8. Positive means higher pressure at
40°S relative to 65°S, i.e. stronger and poleward-shifted westerlies; the
value is used with this sign, unchanged. Expected signs in §5 are stated
for loss fractions: Oct–Jan mean negative with M1 in 88.3 and 48.1;
MAM–JJA mean positive with M6 at 48.4; drift-window mean open in sign for
M5b at 48.2 (Young et al. 2024 vs Freer et al. 2025). Source: Gareth
Marshall, British Antarctic Survey, landing page
<https://legacy.bas.ac.uk/met/gjma/sam.html>, ASCII file
<http://www.nerc-bas.ac.uk/public/icd/gjma/newsam.1957.2007.txt> (the
filename is historical; the file runs to the present). Monthly, January
1957 onward; September 2026 at the download of 15 October 2026. Chosen
over the NOAA CPC AAO because it is observation-based and therefore
homogeneous across the ERA-Interim → ERA5 switch at end-2018 (P2-D08).
Caveats: values appear about two weeks after the month ends and the
recent months are provisional, revised when late station reports arrive
(on 15 October 2026 the page announced revised Feb–May 2026 values and
ECMWF-interpolated station months in 2025–26); the quality flags for such
months are colour-coded on the HTML page only, which `fetch.py` therefore
saves to `raw/sam.html` beside the ASCII file; station changes (Puerto
Montt for Valdivia, Hobart Airport West from August 2022) are listed in
`PROVENANCE.md`. `fetch.py` logs every download that changes a value,
with the months that moved; the paper's tables use the values frozen at
the date in `PROVENANCE.md`. `fetch.py --check` reports whether the
remote has changed without writing. Also available at the same location,
not fetched: the 40°S and 65°S zonal-mean MSLP series and seasonal means.
