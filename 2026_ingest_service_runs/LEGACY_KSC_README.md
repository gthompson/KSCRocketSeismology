# KSC SDS ingestion v4

Thin KSC orchestration around **`flovopy.sds.merge_sds_archives`**. The merger, SQLite transactions, `.part` canonicalization, identical-file detection, zero-byte `SKIP_EMPTY`, progress, and rollback are maintained in FLOVOpy; **no duplicate merge implementation** lives here.

## Setup

Install the current FLOVOpy checkout (including `merge_sds_archives.py`) into the same Python environment, then from this directory:

```bash
python -m pip install -e .
```

`config/ksc.yaml` defaults to `/Volumes/KSCGTdownld`; change for another machine. The master is `/Volumes/KSCGTdownld/SDS` and retains FLOVOpy's existing `.merge_tracking.sqlite` and `.merge_cache/`.

## Existing SDS archives (any instrument)

Use `merge-sds` for a pre-existing SDS archive, regardless of whether it originated from Centaur, Gem, or a mixture. **No conversion is performed.** This replaces `test_ingest.py` through `test_ingest_04.py`.

```bash
ksc-sds --config config/ksc.yaml merge-sds /Volumes/KSCGTdownld/20260403_service/20_archive --dry-run
ksc-sds --config config/ksc.yaml merge-sds /Volumes/KSCGTdownld/20260613_service/00_download/Centaur
```

The second example is a **real ingest**. Add `--dry-run` for a planning pass, or `--progress-every 100` to reduce output. Real runs modify the master SDS. Use the generic command for historical mixed-instrument archives rather than labeling them Centaur.

## Service-run Centaur SDS

```bash
ksc-sds --config config/ksc.yaml status 20260613_service
ksc-sds --config config/ksc.yaml centaur 20260613_service --dry-run
ksc-sds --config config/ksc.yaml centaur 20260613_service
```

Service-run configurations live under `config/YYYYMMDD_service/service_run.yaml`, but the active loader reads `<project_root>/<run_id>/service_run.yaml`. Use `--source` or `merge-sds` if the service-run file has not been created at the active path. The existing raw `00_download` and conversion directories are not modified by this package.

## Rollback

```bash
ksc-sds --config config/ksc.yaml rollback TRANSACTION_ID
```

Uses FLOVOpy's rollback safety checks. Never delete `.merge_cache/` until the corresponding rollback window is no longer needed.

## Limitations

- `centaur` ingests SDS files, not standalone `.seed` files or recorder-native raw files.
- `merge-sds` handles **already formed SDS**, including mixed instruments; it is not a Gem/Gecko/SmartSolo/Guralp/Pegasus converter.
- Raw instrument conversion adapters remain intentionally deferred; `ingest --instrument ...` reports `not_implemented` for those instruments.
- Empty or missing SDS sources now fail explicitly rather than creating a misleading zero-file successful transaction.
- FLOVOpy's `fast` mode trusts SDS names and only reads colliding files. Use a separate waveform completeness/continuity audit later.

## SiliconAudio minute MiniSEED → staging SDS

SiliconAudio files are already MiniSEED, typically in
`00_download/SiliconAudio/B23/data/MM/DD/HH/*.ms`. Conversion groups them
by UTC day and uses `EnhancedSDSClient.write_stream(mode="merge")` to write
**staging** SDS files at `20_archive/SiliconAudio/SDS/2026/...`.

```bash
ksc-sds --config config/ksc.yaml siliconaudio 20260613_service --station B23 --dry-run
ksc-sds --config config/ksc.yaml siliconaudio 20260613_service --station B23
ksc-sds --config config/ksc.yaml merge-sds /Volumes/KSCGTdownld/20260613_service/20_archive/SiliconAudio/SDS
```

The first command only inventories files; it does not validate their contents.
The second converts to staged SDS. The third merges the staged SDS into the
master archive using FLOVOpy's transactional merger. Raw `*.ss` and histogram
files are intentionally preserved, not converted. A minute read failure causes
its entire day to be withheld by default (`--allow-partial-days` overrides).
The converter uses `write_stream`, the method in the supplied original code;
verify that your installed FLOVOpy exposes this API.

SiliconAudio stations share the staging SDS root `20_archive/SiliconAudio/SDS/` (NSLC station IDs separate files). The `EnhancedSDSClient` provided in FLOVOpy exposes `write_stream()` and `write_trace()`, not `write()`. After staging, merge the SDS root into the master using `ksc-sds merge-sds <service>/20_archive/SiliconAudio/SDS`.


## Gem ingestion (v7)

Gem raw microSD files are decoded by the upstream **gemlog** `gemconvert` CLI;
KSC does not reimplement Gem decoding or GPS clock reconstruction.
Install gemlog separately (`pip install gemlog`) and consult
[gemlog README](https://github.com/ajakef/gemlog/blob/main/README.md).

Prepare a **campaign-specific** working folder with `raw/` containing Gem
`FILE*.NNN` files (serial number is extension). Run `gemconvert` in that
folder. It produces `mseed/` (hourly), `metadata/`, `gps/`, and a log.
Review timing and conversion log; retain all of these as provenance.
Copy or move `mseed/` into:
`<run>/10_conversion/Gem/mseed/` (preserve other outputs under `10_conversion/Gem`).

Then stage SDS (default Gem mapping is the historical mapping supplied by the
KSC project; Gem 363 maps to `1R.UNK..HD1` and **must be resolved** before
final archival):

```bash
ksc-sds --config config/ksc.yaml gem 20260613_service --dry-run
ksc-sds --config config/ksc.yaml gem 20260613_service
```

To override serial assignments, provide `--mapping config/gem_mapping.csv`:

```csv
serial,id
273,1R.B24LT..HDF
287,1R.B24RE..HDF
```

This stages to `<run>/20_archive/Gem/SDS/`; it does **not** merge into the
master. Once reviewed, use:

```bash
ksc-sds --config config/ksc.yaml merge-sds \
  /Volumes/KSCGTdownld/20260613_service/20_archive/Gem/SDS
```

Mapping uses full NSLC IDs and preserves custom HDF/HDI codes; it does not
apply instrument response, deconvolution or filtering. `--dry-run` reads
MiniSEED headers and validates mapping without writing. Unmapped serials fail
by default. Re-running staged writes uses `EnhancedSDSClient.write_stream`
`mode='merge'` and therefore is potentially I/O-intensive; review the
stage before rerunning. Conversion is not atomic across an entire campaign.
