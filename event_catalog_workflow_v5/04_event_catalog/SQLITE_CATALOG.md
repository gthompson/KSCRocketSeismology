# SQLite catalog layer

`data/processed/ksc_rockets.sqlite` is the canonical relational catalog for analysis. CSV remains a portable export and pandas remains the normal analysis interface.

Build/update with:

```bash
ksc-rockets build-catalog
ksc-rockets build-db
```

Curated corrections live in `data/curated/event_overrides.csv`; do not silently edit imported raw source tables. Canonical `event_id` values are the reconciled ids written by `ksc-rockets rebuild` and frozen in `data/curated/reconciled_event_ids.csv`, so changing an event time, name, pad or extraction window does not change identity. A new event's id is `ksc-` plus the first 12 hex digits of SHA-1 of `event_type|time_utc|name|pad` from its preferred source record, and is then frozen. The older registry ids in `data/curated/event_id_registry.csv` (used only by the legacy `build-catalog` CSV path, and by the untracked `launch_catalog.csv`) are not canonical; `data/curated/legacy_event_id_map.csv` maps each to its canonical id (1 has none: a Rocket Lab launch from New Zealand; the ICON Pegasus air launch maps to `ksc-c01a108986ae` now that air launches are kept).

The first schema contains `events`, `channel_epochs`, `measurements`, and `qc_intervals`. StationXML remains authoritative for response metadata; the SQL tables carry event relationships, provenance, measurements, and QC.

`event_time_utc` is the physical event/source time. `window_start` and `window_end` are waveform extraction windows and may change without changing event identity. `time_utc` remains temporarily in the CSV as a backwards-compatible alias only.

## Event types

Each type clusters only with its own family during reconciliation (`_type_family` in `event_catalog.py`), so a booster landing eight minutes after liftoff, or a scrub the day before a launch, never merges into the launch.

| event_type | family | what it is | main sources |
|---|---|---|---|
| `orbital_launch` | launch | liftoff from a Cape/KSC pad | LL2, GCAT, workbook |
| `launch_failure` | launch | liftoff, then vehicle lost | LL2, GCAT |
| `pad_explosion` | launch | vehicle destroyed on the pad (AMOS-6, New Glenn 2026-05-29) | GCAT, curated |
| `aborted_launch` | launch | legacy workbook label (SES-9 2016-02-29, Ascent Abort-2); kept for id stability | workbook |
| `suborbital_launch` | launch | GCAT S/A launches from the Cape or just off it: Trident D-5 launches from submarines (site ETR, pad `ETR`, offshore, no coordinates; often date-only) and Army LRHW "Dark Eagle" hypersonic tests at LC-46 (GCAT site SPFLA) | GCAT |
| `air_launch` | launch | Pegasus dropped from the L-1011 after takeoff from the Cape Skid Strip (CYGNSS, ICON); pad `L1011` | GCAT, curated |
| `scrub` | scrub | launch-day scrub with no ignition | LL2 launch `updates`, curated |
| `pad_abort` | scrub | launch attempt with engine ignition then shutdown on the pad; wins over `scrub` if any source reports ignition | curated, LL2 |
| `booster_landing` | own | RTLS landing at LZ-1/LZ-2/LZ-40 (sonic boom) | LL2 (launch + timeline offset) |
| `reentry_sonic_boom` | own | spacecraft return near Florida: X-37B at the SLF, Dragon splashdowns in the Gulf/Atlantic | LL2 `/events/` type 9, curated |
| `aircraft_sonic_boom` | own | supersonic aircraft (SonicBAT F-18s 2017) | workbook, curated |
| `bolide` | own | natural fireball with a reported boom | curated |
| `static_fire` | own | engine firing test on the pad | LL2 `/events/` type 5, workbook, curated |
| `wet_dress_rehearsal` | own | propellant loading rehearsal, no ignition | LL2 `/events/` types 18, 22, curated |
| `ground_test` | own | other LL2 pad tests (cryoproof/tanking, ambient pressure, vehicle testing) | LL2 `/events/` 19, 21, 30 |
| `rollout`, `rollback`, `crawler_move` | ground_move | vehicle or mobile launcher moving to/from a pad by crawler, rail or transporter, with or without a rocket; `event_time_utc` = first motion, `event_end_utc` = arrival, `route` e.g. `VAB->LC39B` | LL2 `/events/` 27, curated |

LL2 scrub rows come from the dated notes in each launch's `updates` (2020 onward): one row per launch and UTC day, timed when LL2 posted the note (precision `hour`; it lags the scrub call). Earlier scrubs and ignition aborts are hand-curated.

## Time fields

`event_time_utc` is the best estimate of the physical event time. The inputs that compete for it are kept in their own columns:

| column | meaning | filled by |
|---|---|---|
| `consensus_time_utc`, `consensus_time_source`, `consensus_time_precision` | time chosen from the source records (largest group of distinct sources agreeing within 5 s) | reconciliation |
| `window_start_utc`, `window_end_utc` | launch window (hours long, or start = end when instantaneous). Not the waveform extraction window, which stays in `window_start`/`window_end` | LL2, `manual_events.csv` |
| `event_end_utc`, `route` | end of an extended event (rollout arrival at the pad) and its route | LL2 event duration, `manual_events.csv` |
| `known_time_utc`, `known_time_source` | confirmed time from another source: webcast clock, NASA release, our own picks | `data/curated/known_times.csv` |
| `detected_time_utc`, `detected_time_method` | time measured on our waveforms (STA/LTA, ...). Must be a source-time estimate (onset minus travel time from the source), not a station arrival | `data/curated/detected_times.csv` (waveform pilot) |

**Which time wins** (`event_time_basis` records the winner, and `event_time_source`/`event_time_precision` follow it):

1. `known` — `known_time_utc` if set;
2. `consensus` — if the source consensus is precise to the second (LL2/GCAT liftoff times): an STA/LTA onset still carries travel-time and picking error;
3. `detected` — `detected_time_utc` if set (rollouts, scrubs, static fires, landings and the many events with only a date, an hour or a window);
4. `consensus` — otherwise.

The rule is in `kscrockets.event_times.resolve_event_times`. Both CSVs are keyed by `event_id`, one row per event (duplicates and unknown ids are errors). Load them without a rebuild:

```bash
ksc-rockets load-times                                # known_times.csv + curated/detected_times.csv
ksc-rockets load-times --detected path/to/run.csv     # another detection run
```

`rebuild` and `reconcile-events` read the same files (`--detected-times` for another). Removing a row and reloading restores the source time. Event ids never depend on any time field.

## Hand-curated events

`data/curated/manual_events.csv` holds events no external catalog lists, each with a `source_url`. Columns: `event_id` (assign once with `stable_event_id`, never change), `event_type`, `event_time_utc`, `event_time_source`, `event_time_quality`, `event_time_precision`, `time_definition`, `name`, `mission`, `vehicle`, `pad`, `provider`, `source`, `notes`, `source_url`, `window_start_utc`, `window_end_utc`, `event_end_utc`, `route`. A curated row merges with an LL2/GCAT record of the same family within 12 h when the names agree; otherwise it is its own event.

## LL2 snapshot

`ksc-rockets fetch-ll2 [--wait]` keeps every raw LL2 page (gzip JSON) in `data/raw/external/ll2_raw/` and never requests a page it already has, so a fetch stopped by the 15-requests-per-hour limit resumes where it stopped (`--wait` sits the limit out). `ksc-rockets fetch-ll2 --from-raw` rebuilds `ll2_events.csv` offline from those pages. Air launches are now kept by default (`--exclude-air-launches` drops them).

## Completeness check

`ksc-rockets completeness` (also run by `rebuild`) writes `data/availability/catalog_completeness.csv`, with one row per month from 2016-02 to the current month. Each row gives catalog launches (orbital, failure, air, suborbital, pad explosion, legacy aborted_launch), GCAT launches (sites CC, KSC, SPFLA, ETR), LL2 launches, and counts of every other event type. It also names every launch that one source has and the catalog or another source lacks, plus an `explanation` for each month where the counts differ or nothing happened. GCAT is the independent reference: every GCAT Cape/KSC record since 2016 is in the catalog. Waveform availability never filters the catalog; events with no recordings stay in.

GCAT site codes: `CC` Cape Canaveral SFS, `KSC`, `SPFLA` (Space Florida's LC-46: ORS-5, Orion AA-2, Astra, LRHW), `ETR` (Eastern Test Range, Trident off the Cape). The filter used to keep only CC and KSC, which missed 30 SPFLA/ETR launches since 2016.
