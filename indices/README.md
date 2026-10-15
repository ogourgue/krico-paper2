# indices/

Climate-index series for Paper 2 (`Paper 2/methodology.md` §5 and §7;
P2-D08, P2-D09). Data, not exploration: this folder sits beside
`ccamlr-data/`. One self-contained subfolder per index, each with

- `fetch.py` (or `compute.py` for derived indices): downloads the source
  files verbatim into `raw/`, computes sha256, writes `PROVENANCE.md`;
  idempotent; `--check` compares the remote with `raw/` and writes nothing;
- `tidy.py`: `raw/` → `<index>_monthly.csv`, one file per variable;
- `README.md`: definition, sign convention, source, period, caveats.

No shared code across subfolders and no imports from elsewhere in the
repository, so each folder runs on its own. Window files and the joined
year × subarea tables live with the analysis that uses them, not here.
Pruning before release (P2-D09): folders never run against the outcomes
are deleted; folders behind a negative result in the text stay.

## Indices

Build order: sam, asl, nino34, emi, orcadas, dipole, zw3. Rows are added
as folders are built; "used in paper" is filled in from the window file.

| Index | Folder | Variables | Source | Period | Used in paper |
|---|---|---|---|---|---|
| Marshall SAM | `sam/` | `sam_monthly.csv` | G. Marshall, BAS (station-based, Marshall 2003), <https://legacy.bas.ac.uk/met/gjma/sam.html> | 1957-01 – present (2026-09 on 15 Oct 2026) | tbd |
| Amundsen Sea Low (ASLI v3) | `asl/` | `asl_pressure_rel_monthly.csv`, `asl_longitude_monthly.csv`, `asl_latitude_monthly.csv`, `asl_pressure_actual_monthly.csv`, `asl_pressure_sector_monthly.csv` | BAS `asli` package on ERA5 (Hosking et al. 2016), <https://files.bas.ac.uk/twins/asli/asli_calculation_latest.csv> | 1959-01 – present (2026-07 on 15 Oct 2026) | tbd |
| Niño 3.4 / ONI (+ relative) | `nino34/` | `nino34_monthly.csv`, `oni_monthly.csv`, `nino34_rel_monthly.csv`, `roni_monthly.csv` | NOAA CPC, ERSSTv6, <https://www.cpc.ncep.noaa.gov/data/indices/index.shtml> | monthly 1949-12 –, seasonal 1950-01 – present (2026-09 / 2026-08 on 15 Oct 2026) | tbd |
| El Niño Modoki Index | `emi/` | `emi_monthly.csv` | JAMSTEC APL VirtualEarth (OISST v2, 1983–2015 base; Ashok et al. 2007), <https://www.jamstec.go.jp/virtualearth/general/en/index.html> | 1982-01 – present (2026-09 on 15 Oct 2026) | tbd |

## Common schema

`year,month,value`: calendar year and month as integers, one row per
month, values as published by the source, with the source's own sign and
precision, no re-normalisation, no gap filling, no seasonal averaging. An
index with several variables gets one file per variable
(e.g. `asl_pressure_rel_monthly.csv`, `asl_longitude_monthly.csv`).

## Sign conventions

Each index keeps the sign its source defines; the positive phase is
stated in the folder's `README.md` and summarised here:

| Index | Positive phase means |
|---|---|
| Marshall SAM | higher pressure at 40°S relative to 65°S: stronger, poleward-shifted westerlies |
| ASL relative central pressure | actual minus sector-mean pressure, hPa, always negative; a larger (less negative) value is a weaker low |
| ASL longitude | degrees east, 170–298 (= 190°W–62°W); a larger value is a low further east, towards the Peninsula |
| Niño 3.4, ONI, relative Niño 3.4, RONI | °C anomaly in the Niño 3.4 box; positive = warm, El Niño; seasonal values sit on the centre month of the 3-month season |
| EMI | °C, central box minus half of each flank; positive = warm centre with cool ends, a Central-Pacific (Modoki) event |

Expected correlations (§5) are written for the **loss fractions** M1, M6
and M5b and flip sign for success. The averaging window follows the
outcome, not the cohort: Oct–Jan for M1 (October–December of the year
before the spawning year, January of the spawning year), Mar–Jul for M6,
the 200-day drift for M5b; lags tested 0, 3 and 6 months, no others.
Monthly resolution is kept in these files; windows are applied in the
analysis folder, after the expected signs are committed in the window
file.
