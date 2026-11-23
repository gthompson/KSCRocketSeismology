# General KSC/Cape event catalog workflow

The database is intentionally broader than a launch list. Supported research event types are:

- `orbital_launch`
- `launch_failure`
- `pad_explosion`
- `static_fire`
- `aborted_launch`
- `booster_landing`
- `aircraft_sonic_boom`

`events.event_time_utc` is the project's adjudicated/preferred time. Competing source times are retained in `event_time_sources`; they are not overwritten. `window_start/window_end` remain waveform-analysis windows and must not be used as source times.

## Hand-curated workbook + LL2 reconciliation

```bash
ksc-rockets build-catalog
ksc-rockets build-db
ksc-rockets reconcile-events --excel /path/to/All_KSC_Rocket_Launches.xlsx --fetch-ll2
```

This writes `data/processed/event_reconciliation.csv` and `event_time_sources.csv` and inserts source provenance into SQLite. Review `time_conflict` and `time_spread_s` before promoting/replacing existing event times. The default is deliberately non-destructive.

LL2 is an automated source, not unquestioned truth: retain its `net_precision`, status, source ID and source URL. The public LL2 service is rate-limited, so cache the reconciliation outputs rather than querying on every analysis run.

## Add waveform-derived events manually

```bash
ksc-rockets add-event aircraft_sonic_boom 2017-08-22T18:34:12.4Z "SonicBAT F-18 boom 01" --pad SLF --source waveform_review --notes "Picked on BCHH pressure array"
```

This appends to `data/curated/manual_events.csv`. The assigned `event_id` is persistent. Rebuilding/reconciling should ingest these curated events rather than regenerating their IDs.

For an experiment day whose individual event times are not yet picked (e.g. SonicBAT), keep the day-level record only as a placeholder/context record and add each waveform-picked sonic boom as its own event.

## Source philosophy

1. Preserve every source observation.
2. Match events without requiring exact timestamp agreement.
3. Prefer manually verified/second-precision times for the project preferred time.
4. Flag disagreements rather than silently resolving them.
5. Keep event identity independent of later changes to waveform extraction windows.

## Scheduled times are not physical events

Some launch databases retain the planned T-0 for a mission that never launched. LL2's AMOS-6 entry is an example: its 2016-09-03 07:00 UTC NET is the planned launch time, whereas the physical pad explosion occurred during static-fire preparations on 2016-09-01. The reconciler now marks explicit LL2 `Failure before launch` NET values as `scheduled_launch_time`. They can attach to a matching physical event as provenance, but they do not create waveform events and do not contribute to `time_spread_s` or `source_count`.

Use `event_time_sources.time_role` to distinguish `actual_event_time` from `scheduled_launch_time`.
