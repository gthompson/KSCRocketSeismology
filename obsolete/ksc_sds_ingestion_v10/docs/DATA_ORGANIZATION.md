# KSC service-run data organization

A service run is named from its first field day: `YYYYMMDD_service`, e.g. `20260922_service`.

```text
KSC_DATA/
  SDS/                         # one canonical master SDS archive
  database/
  20260922_service/
    service_run.yaml
    00_download/
      Centaur/
      Gem/
        raw/
      SiliconAudio/
      Guralp/
      SmartSolo/
      Pegasus/
    10_conversion/
    20_archive/
    30_qc/
```

## Raw download rules

Preserve instrument output beneath the appropriate `00_download` directory. Do not rename or reorganize individual waveform files.

* **Centaur** — Centaur already records SDS. Put/mount its SDS content under `00_download/Centaur/` when practical, or pass the mounted SD-card path directly to the Centaur ingest. Fast ingest copies non-colliding SDS files byte-for-byte and waveform-merges only collisions/`.part` files into the master `SDS/` archive. It does not create a second service-run SDS archive.
* **Gem** — copy the microSD data under `00_download/Gem/raw/`. GemConvert output will later go under `10_conversion/Gem/mseed/`.
* **SiliconAudio / Gecko** — preserve `data/` and `histogram/` under the station, e.g. `00_download/SiliconAudio/B23/data/MM/DD/HH/YYYY-MM-DD hhmm ss B23.ms` and `.../histogram/`.
* **Guralp** — preserve any recovered native download structure. Continuous acquisition workflow remains to be established from real data.
* **SmartSolo** — data require the SmartSolo Harvester and SoloLite workflow. Preserve the harvested/exported material under `00_download/SmartSolo/`; exact conversion workflow will be implemented from a real harvest.
* **Pegasus** — preserve native download structure when available; adapter is deferred until real data are available.

## Centaur ingest

Centaur ingestion wraps the transactional FLOVOpy SDS archive merger. `fast` mode trusts SDS filenames: files absent from the target are copied without reading MiniSEED, while collisions and `.part` files are read and merged through `EnhancedSDSClient`. `slow` mode reads all MiniSEED and derives canonical SDS destinations from trace headers.

Always run a dry run first for a new card/service run.
