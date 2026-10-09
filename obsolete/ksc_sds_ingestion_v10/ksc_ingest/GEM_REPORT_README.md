# Gem conversion reports (v10)

The original Python Gem serial-to-SEED mapping from v9 is preserved verbatim in
`config/gem_mapping_artemis2_example.csv` (22 rows, including `363,1R.UNK..HD1`).
`station_info.txt` is **not** used to override the mapping. `UNK` is retained as
unresolved provenance, not silently replaced with a guessed site.

Run from the package root after `pip install -e .`:

```bash
ksc-sds gem-report \
  /Volumes/KSCGTdownld/20260310_service/10_gemconvert \
  /Volumes/KSCGTdownld/20260310_service/30_qc/gem_deployment_inventory.csv \
  --daily-csv /Volumes/KSCGTdownld/20260310_service/30_qc/gem_daily_availability.csv \
  --mapping config/gem_mapping_artemis2_example.csv
```

Two CSV outputs:

* **Deployment inventory**: one row per Gem serial and SEED ID; first and last
  waveform time, sampling rate(s), unique waveform files and bytes, samples,
  union-based coverage, gaps, GPS fix counts/median location and range, and
  available battery, temperature, FIFO, overrun and GPS-on telemetry.
* **Daily availability**: one row per Gem serial / SEED ID / UTC day, including
  time window, observed seconds, missing seconds, completeness percentage,
  internal gaps, continuous segments and sampling rate(s).

Without deployment bounds, inventory coverage is first-to-last-observed-sample,
and daily coverage uses this same observed span (including partial first/last
UTC days). This **cannot detect outages before the first or after the last
sample**. For uptime relative to intended deployment dates, supply:

```bash
  --deployment-start 2026-03-10T00:00:00Z \
  --deployment-end 2026-04-03T00:00:00Z
```

These optional bounds apply to all Gem IDs in this invocation; use separate
invocations for different deployment intervals. End times are exclusive.
Duplicate/overlapping waveform intervals are unioned for coverage (not double
counted). File bytes and sample counts reflect input files, including duplicates.
GPS fixes may include installation/recovery movement: coordinate medians are
not surveyed positions. MiniSEED is scanned header-only, but GPS/telemetry
logs are read in full. Inspect `read_errors` in the command's JSON summary.
