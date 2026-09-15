# KSC Rocket Seismology — unified catalog / website / ensemble stack

This tree consolidates the former `04_event_catalog`, `05_website`, and `07_ensemble_paper` workflows around one canonical launch catalog.

## Architecture

`data/raw/merged_launches.csv` → **canonical catalog** (`data/processed/launch_catalog.csv`) → two consumers:

1. **Static event-catalog website** (`outputs/website/`) — no ObsPy or FLOVOpy required.
2. **Ensemble-paper analysis** (`outputs/ensemble/`) — reproducible tables and figures for the 2016–2022 launch population.

Waveform/physical-metric generation remains a separate scientific-processing layer. Existing FLOVOpy/ObsPy experiments are retained under `legacy/04_event_catalog`; their output index can be joined to the canonical catalog without making the website dependent on waveform-processing software.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
ksc-rockets build-all
python -m http.server 8000 -d outputs/website
```

Then open `http://localhost:8000`.

## Commands

```bash
ksc-rockets build-catalog
ksc-rockets build-website
ksc-rockets analyze
ksc-rockets validate
ksc-rockets build-all
```

All paths and the 2016–2022 analysis interval are controlled from `config/default.toml`; there are no hard-coded `/raid`, `/shares`, Dropbox, or `/var/www` paths in the new stack.

## What changed

- One stable `event_id` per launch.
- One normalized schema for launch time, vehicle, pad, provider and SpaceX landing metadata.
- Website generated from the canonical catalog, with search/filtering and per-event pages.
- Ensemble tables/plots generated from exactly the same catalog used by the website.
- Physical metrics linked by launch designator/event metadata rather than duplicated into web-specific CSVs.
- Machine-specific deployment is removed from scientific code. Deployment can now simply copy `outputs/website/` to the web server.
- Original notebooks/scripts are retained in `legacy/` for provenance and gradual migration.

## Next scientific migration

The large notebooks in the old catalog directory contain valuable processing logic (SDS extraction, response removal, RSAM/detection, PAP/PGV/PGA/PGD, spectra). They should be migrated incrementally into testable package functions, not copied wholesale into the web layer. The canonical catalog is deliberately ready for those products: use `event_id` as the permanent key and treat waveform/metric files as derived artifacts.


## External event-source cache

Launch Library 2 is treated as an occasional external snapshot, not a live dependency of every catalog rebuild.

```bash
ksc-rockets fetch-ll2
# Progress is printed page-by-page, including retries, counts, filtering, and cache writes.
ksc-rockets reconcile-events --excel data/raw/All_KSC_Rocket_Launches.xlsx
```

`fetch-ll2` writes `data/raw/external/ll2_events.csv`. Normal `reconcile-events` automatically uses that cache when present. If LL2 returns HTTP 429 or a network error during a refresh, an existing cache is retained rather than discarded. Use `--no-ll2-cache` for a manual-only reconciliation. `--fetch-ll2` remains as a convenience but is no longer the recommended normal workflow.

## External event-time caches

External catalogs are snapshots, not live dependencies of normal analysis. Refresh them occasionally, then reconcile offline:

```bash
ksc-rockets fetch-ll2
ksc-rockets fetch-gcat
ksc-rockets reconcile-events --excel data/raw/All_KSC_Rocket_Launches.xlsx
```

GCAT ingestion uses the official designation lists for orbital launches (O), orbital launch failures (F), and pad explosions (E). GCAT `Launch_Date` is retained with the source definition **UTC first motion**. The raw source classification and source ID are preserved in `event_time_sources.csv`; reconciliation does not silently overwrite competing times.

## Version 5 reproducible catalog workflow

Version 5 makes the reconciled event catalog the final database product and adds explicit cleaning/rebuilding commands.

### Normal rebuild (recommended)

Uses the cached LL2 and GCAT snapshots, so it is fast and reproducible/offline:

```bash
pip install -e .
ksc-rockets info
ksc-rockets rebuild
```

`rebuild` removes generated catalog/database/reconciliation products, preserves raw and curated inputs and external caches, rebuilds the 195-row hand-maintained baseline, reconciles Excel + LL2 + GCAT, and then rebuilds SQLite from the reconciled events and source-time provenance.

### Full refresh rebuild (slower)

```bash
ksc-rockets rebuild --refresh-external
```

This also deletes and refetches LL2 and GCAT before reconciliation. LL2 is paginated/rate-limited and can take substantially longer. Existing caches are otherwise deliberately preserved.

### Cleaning only

```bash
ksc-rockets clean
```

removes generated `data/processed` products and configured website/ensemble outputs but preserves `data/raw`, `data/curated`, and `data/raw/external` caches.

```bash
ksc-rockets clean --caches
```

also removes the external LL2/GCAT cache directory. A subsequent `rebuild` then requires either restoring caches or using `rebuild --refresh-external`.

### Reconciliation behavior

* GCAT is date-subset before matching; the full historical cache is not sent through the matcher.
* A new record is compared with every member of a candidate cluster, not only the first/manual member. This lets LL2 and GCAT agree even when a hand-entered time is badly wrong (e.g. Demo-2).
* Preferred event time is chosen by independent-source consensus. Manual values remain provenance and are not silently overwritten.
* Cape-origin runway/air launches (e.g. Pegasus) are excluded from the pad-launch population by default. Use `--include-air-launches` to retain them.
* Scheduled launch times such as the AMOS-6 planned T-0 remain provenance and do not create physical waveform events.
