# ice_timing — sea-ice retreat and advance day over the spawning bands (NSIDC)

The observed timing of the ice at the release positions, per recruiting
subarea and spawning year: the **retreat day**, when the slope opens in
the spring before the cohort is released, and the **advance day**, when
winter ice returns in the autumn after it; sixteen annual files, schema
`year,value`, `retreat_<sub>_annual.csv` and `advance_<sub>_annual.csv`
with the day, and `retreat_<sub>_share_annual.csv` and
`advance_<sub>_share_annual.csv` with the share of the subarea's weight
on which the event occurred, `<sub>` in 883, 481, 482, 484. Definition
(Stammerjohn et al. 2008 as applied in KRICO paper 1): a cell is iced
when its concentration is above 15%, a run is five or more consecutive
iced days; in ice year Y (15 February Y to 14 February Y+1) the advance
is the first day of the first run on or after 1 April (the cutoff of the
particle classification, so that lingering previous-winter ice is not
read as an advance; cells already in a run on 1 April get 1 April, and
their weight share is in `PROVENANCE.md`), and the retreat is the day
after the last day of the last run, undefined when the cell never ices
or is still iced on 14 February. Spawning year Y (releases 15 November
Y−1 to 14 March Y, spawning 24 days earlier) takes the retreat of ice
year Y−1 and the advance of ice year Y. Days are day-of-year on a
365-day calendar counted from 1 January of the year the ice year starts
and continuing past 365 (29 February counts in the daily record but is
dropped from the label, so 1 March is always 60; a retreat on 10 January
of the following year is 375, so that a subarea whose cells open on
either side of New Year averages sensibly). Cells are the NSIDC 25 km cells that contain the release cells
of the simulation (`../subarea/raw/spawning_cells.csv`, read by path),
found by projecting each release cell centre with the polar
stereographic projection of the grid (checked against the ancillary
latitude/longitude to better than a metre) and keeping ocean cells; each
cell is weighted by the number of particles a cohort starts in it, and
the subarea value is the weighted mean over cells that have the event,
weights renormalised, the dropped share in the companion file. Values
are not anomalies and no year is filled. Source: NOAA/NSIDC Climate
Data Record of Passive Microwave Sea Ice Concentration v6 (G02202,
doi:10.7265/b18j-z797; Meier et al.), daily, as stacked by month for
KRICO under `$KRICO_NSIDC` on ECMWF, 1993-02-01 to 2026-02-28 without a
missing day, so ice years 1993–2025 are complete and spawning years
1994–2025 have both ends; `compute.py` runs there and leaves
`raw/cells.csv` and `raw/cell_timing.csv` (one row per cell, subarea and
ice year, committed as the reduced table), with the sha256 of every
stack in `compute_log.json`; `tidy.py` aggregates on the laptop. Caveats:
the 25 km cell is coarser than the release band in places (a cell can
straddle slope and shelf), and the advance it sees is the advance over
the release position, not along the trajectory that the per-particle
classification follows, so the two agree only where larvae stay near
their origin; fill days in the CDR are interpolated linearly in time and
counted per cell and year; the 1 April cutoff can label an early-March
re-freeze in 88.3 as 1 April, which the `ice_on_apr1` column and the
share in `PROVENANCE.md` make visible; a subarea whose band is partly
ice-free all winter (48.4 in warm years) has a retreat and an advance on
only part of its weight, which the share files carry and the analysis
must read with the value. Licence: public domain (NOAA/NSIDC); cite
Meier, W. N. et al., NOAA/NSIDC Climate Data Record of Passive Microwave
Sea Ice Concentration, Version 6, and Stammerjohn, S. E. et al. (2008,
*JGR* 113, C03S90, doi:10.1029/2007JC004269).
