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
