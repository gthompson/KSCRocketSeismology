
## Gem ingestion (v8)

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

### Running gemconvert and GPS QC

The raw decoding step can be launched with `ksc-sds gem-convert WORKSPACE`;
`WORKSPACE/raw/` must contain the original `FILE*.NNN` data. This executes
upstream `gemconvert` in that working directory. As upstream documentation
notes, repeating conversion overwrites its hourly MiniSEED, while GPS/metadata
get conversion-number suffixes and the logfile is appended. Keep the raw,
metadata, GPS, and log directories for reproducibility.

To produce a station-coordinate QC CSV from GPS logs:

```bash
ksc-sds gem-gps /path/to/workspace/gps \
    /path/to/20260613_service/30_qc/gem_gps_coordinates.csv \
    --mapping /path/to/campaign_gem_mapping.csv
```

This uses `gemlog.summarize_gps` and therefore requires `gemlog` installed
in the executing environment. The reported GPS statistics are **not** a
survey-grade array geometry. Reconcile coordinate estimates against deployment
notes before generating StationXML or doing beamforming. The supplied legacy
Gem 363 assignment `1R.UNK..HD1` is intentionally rejected by strict staging
if that serial appears: resolve the station identity before ingestion.

**Important:** The supplied mapping is an Artemis-2-era mapping, not a
permanent hardware identity table. Serial-to-SEED assignments can change
between deployments. Always use a campaign-specific CSV for a new deployment.
The SDS stage stores raw Gem MiniSEED counts; deconvolution to pressure is
an analysis operation and requires gain/response metadata.
