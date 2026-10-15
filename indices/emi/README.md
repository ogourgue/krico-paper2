# emi — El Niño Modoki Index (JAMSTEC)

The Central-Pacific flavour of ENSO, after Ashok et al. (2007, *JGR* 112,
C11007): EMI = SSTA(A) − 0.5·SSTA(B) − 0.5·SSTA(C), where A is the
central box 165°E–140°W, 10°S–10°N, B the eastern box 110–70°W,
15°S–5°N, and C the western box 125–145°E, 10°S–20°N, each an area-mean
sea-surface-temperature anomaly in °C. Subtracting the two flanks cancels
basin-wide warming and classic eastern-Pacific El Niño, leaving the
warm-centre, cool-ends pattern. Sign convention, values kept as
published: positive = warm centre with cool flanks, a Central-Pacific
(Modoki) event; negative = the reverse. §5 uses it for one test only:
whether the Amundsen response is Central-Pacific (Wilson et al. 2016),
so the expectation is the same sign as Niño 3.4 for M1 in 88.3, i.e.
positive, and EMI is expected to outperform Niño 3.4 there and nowhere
else. Source: JAMSTEC Application Laboratory, APL VirtualEarth
<https://www.jamstec.go.jp/virtualearth/general/en/index.html> (Menu >
EMI), served from
<https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_EMI.csv>, a
graph file whose `Obs` column is the observed index and whose other
columns are the SINTEX-F2 seasonal forecast; method stated at
<https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html>:
NOAA OISST v2, anomalies relative to 1983–2015. Monthly from January
1982; September 2026 at the download of 15 October 2026. Caveats: the
file is overwritten monthly and the address is not linked anywhere
visible, only inferred from the site's pattern and confirmed by download,
so a move would show as a fetch failure rather than a stale copy;
JAMSTEC rejects the default Python user agent, so `fetch.py` sends a
browser-like one; observed values carry binary float noise and are
rounded to five decimals by `tidy.py`, the source's own precision; the
series sits on a different SST product and base period from the CPC
Niño 3.4 it is compared against in 88.3 (OISST v2, fixed 1983–2015 base,
versus ERSSTv6 with centred bases), so the two are not interchangeable
in level, only compared as predictors; the former address
`aplinfo/sintexf/DATA/emi.monthly.txt`, cited in the literature, is now
a stub pointing to VirtualEarth; the HadISST-based monthly EMI from 1870
that JAMSTEC once offered is no longer linked. No licence stated; cite
Ashok et al. (2007) and JAMSTEC APL VirtualEarth. If the 88.3 result
turns on this index, the same three boxes can be recomputed from the
ERSST field used by CPC, putting EMI and Niño 3.4 on one product.
