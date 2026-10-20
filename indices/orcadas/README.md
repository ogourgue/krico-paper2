# orcadas — monthly mean surface air temperature at Orcadas (SCAR READER)

The thermometer where M6 is decided: monthly mean near-surface air
temperature, in °C, at Base Orcadas (WMO 88968, Laurie Island, South
Orkney Islands, 60.7°S 44.7°W, 6 m), inside subarea 48.2 and on the path
of the winter ice advancing out of the Weddell Sea towards South Sandwich
(48.4); Murphy et al. (2014, *JGR Oceans* 119) found that May–July
temperature there, not wind, controls the northern Weddell winter ice.
Observed since 1903, the longest Antarctic record. Sign convention,
values as published: °C, warmer is larger. §5 expects the May–July mean
strongly negative with M6 at 48.4 and 48.2 (warm early winter, ice edge
held south, no winter ice for the island larvae), the largest |r| in the
set. Three files, schema year,month,value: `orcadas_monthly.csv`, the
temperature as published, empty where the table prints none (no gap
filling); `orcadas_obs_pct_monthly.csv`, the percentage of the four
daily synoptic reports (00, 06, 12, 18 UTC) behind each mean, empty for
the pre-1956 CLIMAT means; `orcadas_origin_monthly.csv`, the cell colour
READER uses for data origin (black, full record from Argentina's
national service; green, preliminary GTS; blue, CLIMAT monthly mean
only; red, below 90% of reports), written only if the HTML carries the
colour as an attribute `tidy.py` can read. Source: SCAR READER station
table <https://legacy.bas.ac.uk/met/READER/surface/Orcadas.All.temperature.html>
(colour key and 90% rule at <https://legacy.bas.ac.uk/met/READER/data.html>);
the HTML table is kept rather than the text download because the text
version drops every cell below 90%. April 1903 onward; September 2026
at the download of 16 October 2026 (the table's own production date is
in `PROVENANCE.md`; August 2026 was revised from −11.2 to −10.7 between
the table of 1 September and that download).
Completeness verdict (May–July, 2005–2025, checked 15 October 2026):
clean at 99–100% for 2005–2019 and 2024–2025; below READER's 90% rule
for seven months in four winters, 2020-05 (47%), 2021-05/06/07
(70–73%), 2022-06 (81%), 2023-06/07 (85–86%); 2002-03 to 2003-12 sit at
a uniform 75%, one of the four daily reports missing throughout, a
sampling change rather than gaps. Decision: the station is the index of
record because it is an observation independent of any reanalysis; the
analysis applies the 90% rule from the percentage file and fills the
seven 2020–2023 months, all in the 2017–2025 test period, with ERA5 2 m
temperature at the station, after checking that ERA5 and the station
agree in the clean years; that fill is done in `local/orcadas_fill/`,
not here. Caveats: READER is revised as operators supply full records,
so values and percentages can change between fetches, which `fetch.py`
logs month by month; the table carries a production date but
no version; the observing point has moved within the station over the
century. Licence: Open Government Licence v3.0; cite Turner et al.
(2004, *J. Climate* 17, 2890–2898) and the READER DOI on the data page.
