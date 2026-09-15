# SQLite catalog layer

`data/processed/ksc_rockets.sqlite` is the canonical relational catalog for analysis. CSV remains a portable export and pandas remains the normal analysis interface.

Build/update with:

```bash
ksc-rockets build-catalog
ksc-rockets build-db
```

Curated corrections live in `data/curated/event_overrides.csv`; do not silently edit imported raw source tables. Existing `event_id` values are frozen in `data/curated/event_id_registry.csv`, so changing an event time or extraction window does not change identity.

The first schema contains `events`, `channel_epochs`, `measurements`, and `qc_intervals`. StationXML remains authoritative for response metadata; the SQL tables carry event relationships, provenance, measurements, and QC.

`event_time_utc` is the physical event/source time. `window_start` and `window_end` are waveform extraction windows and may change without changing event identity. `time_utc` remains temporarily in the CSV as a backwards-compatible alias only.
