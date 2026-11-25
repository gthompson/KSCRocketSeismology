# Detected event times

`detected_times.csv` holds event times measured on our own waveforms, one row per `event_id`
(the canonical reconciled ids in `data/processed/ksc_rockets.sqlite`). It is written by the
waveform-detection pilot, not by hand; rows are replaced when an event is reprocessed. It is
not shipped empty here: the pilot branch adds it. Columns the loader needs are below; others
(`offset_from_catalog_s`, `mad_s`, `n_stations`, `n_channels`, `run_id`) are kept as written.

| column | meaning |
|---|---|
| `event_id` | canonical event id (required) |
| `detected_time_utc` | ISO 8601 UTC **source-time** estimate: onset minus the travel time from the pad/source to the station (required) |
| `detected_time_method` | short label, e.g. `stalta_strongest_onset_minus_r_over_343ms_pressure` (required) |
| `notes` | optional |

Load into the database without a rebuild:

```bash
ksc-rockets load-times                       # data/curated/known_times.csv + this file
ksc-rockets load-times --detected other.csv  # another detection run
```

`ksc-rockets rebuild` / `reconcile-events` also read this file (`--detected-times` for another).
How the detected time competes with known and source times is described in
`04_event_catalog/SQLITE_CATALOG.md`.
