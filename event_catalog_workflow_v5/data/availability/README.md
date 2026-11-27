# Waveform availability per catalog event (built 2026-11-23)

* `event_waveform_availability.csv`: one row per event in `data/processed/ksc_rockets.sqlite`; the
  stations (`NET.STA`) and channels with an SDS day file for every UTC day touched by event ±600 s.
  Day files are only listed, not opened (a file covering part of the day counts).
* `sds_coverage_gaps.csv`: runs of days 2016-01-01 to 2026-11-22 with no day file in either archive.

Archives used (`ksc-rockets availability`):

| events | SDS root |
|---|---|
| 2016-01-01 to 2022-12-31 | `/Volumes/classdata/remastered/SDS_KSC` (1R, AM, XA) |
| 2026-01-01 to 2026-12-31 | `/Volumes/KSCGTdownld/SDS` (1R, DG; master SDS of the 2026 service runs) |

## Gaps (≥ 2 weeks) and what else was searched

Searched before calling these gaps: `/Volumes/classdata/remastered/SDS_KSC/unmatched`,
`/Volumes/classdata/remastered/BUD_KSC` (same days as SDS_KSC, 2016-2022 only),
`/Volumes/haldata/KSC` (= `/Volumes/classdata/KSC`: `beforePASSCAL/CONTINUOUS`, `duringPASSCAL`,
`launch_events`, `2026*_service/20_archive/SDS`), `/Volumes/classdata/sort`, and a name search for
`*2023*`/`*2024*`/`*2025*` under those trees plus `/Volumes/classdata/{incoming,smartsolo,rover_data_repo}`
(the 2016–2026 `/Volumes/KSCGTdownld/SDS` tree holds only 2026). `sort/tachyon_backup/work/KSC_ensemble`
has 213 event folders for 2023–2025 launches, all empty.

| first day | last day | days | other data found |
|---|---|---|---|
| 2016-01-01 | 2016-02-23 | 54 | before the network. `unmatched/2016`: JPK1, JPK2 on 2016-02-05 (GPS IIF-12 launch); BCHH, CARL1 2016-02-20..23. `beforePASSCAL/CONTINUOUS`: FL network raw files 2016-036, 051-054 |
| 2016-03-06 | 2016-03-21 | 16 | none |
| 2016-04-10 | 2016-05-16 | 37 | none |
| 2016-06-25 | 2016-08-13 | 50 | `beforePASSCAL/CONTINUOUS` Antelope databases `dbusf20160625`..`dbusf20160726` (wfdisc) — not in the SDS archive |
| 2016-09-09 | 2017-08-17 | 343 | `beforePASSCAL/CONTINUOUS` 2017-023..030; `unmatched/2017`: AM.R37BE 2017-01-25, 1R.SON1 2017-05-08 |
| 2018-02-08 | 2018-02-28 | 21 | none |
| 2018-03-07 | 2018-08-09 | 156 | none |
| 2021-08-06 | 2021-10-15 | 71 | none |
| 2021-10-17 | 2022-03-23 | 158 | none |
| **2022-12-03** | **2026-01-06** | **1131** | **No KSC archive at all for 2023, 2024, 2025** (318 catalog events). Only `/Volumes/classdata/sort/huddle_at_usf`: FL.S37A1 (HH?, HDF, LH?, LDF) 2023-10-21..2024-11-29 and 2025-01-23..27, XX.C166 (HH?, LH?) 2025-01-27..2025-08-04, plus three Centaur event SEED files 2025-07-29. The folder name says these were recorded in a huddle test at USF, not at KSC — to be confirmed |
| 2026-09-23 | 2026-11-22 | 61 | after the last service download (2026-09-22); data presumably still in the field |

Shorter gaps are in `sds_coverage_gaps.csv`.
