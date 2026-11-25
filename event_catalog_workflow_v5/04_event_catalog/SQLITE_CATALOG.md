# SQLite catalog layer

`data/processed/ksc_rockets.sqlite` is the canonical relational catalog for analysis. CSV remains a portable export and pandas remains the normal analysis interface.

Build/update with:

```bash
ksc-rockets build-catalog
ksc-rockets build-db
```

Curated corrections live in `data/curated/event_overrides.csv`; do not silently edit imported raw source tables. Canonical `event_id` values are the reconciled ids written by `ksc-rockets rebuild` and frozen in `data/curated/reconciled_event_ids.csv`, so changing an event time, name, pad or extraction window does not change identity. A new event's id is `ksc-` plus the first 12 hex digits of SHA-1 of `event_type|time_utc|name|pad` from its preferred source record, and is then frozen. The older registry ids in `data/curated/event_id_registry.csv` (used only by the legacy `build-catalog` CSV path, and by the untracked `launch_catalog.csv`) are not canonical; `data/curated/legacy_event_id_map.csv` maps each to its canonical id (2 have none: a Rocket Lab launch from New Zealand and the ICON Pegasus air launch, which the rebuild excludes).

The first schema contains `events`, `channel_epochs`, `measurements`, and `qc_intervals`. StationXML remains authoritative for response metadata; the SQL tables carry event relationships, provenance, measurements, and QC.

`event_time_utc` is the physical event/source time. `window_start` and `window_end` are waveform extraction windows and may change without changing event identity. `time_utc` remains temporarily in the CSV as a backwards-compatible alias only.
