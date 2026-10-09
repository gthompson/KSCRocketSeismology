# Falcon 9 release 1.0.0 data manifest

The workflow reads machine-specific locations from repository/local_config.toml.
project_config defines INPUT_DIR = PAPER_DIR/inputs, OUTPUT_DIR = PAPER_DIR/outputs,
and RELEASE_DIR = PAPER_DIR/release. MINISEED_DIR is INPUT_DIR/miniseed;
RAW_MSEED is the configured accident-window file.

## Archive layout

- repository/: modules, notebooks, environment.yml, LICENSE, CITATION.cff,
  DATA_MANIFEST.md and local_config.example.toml.
- paper/inputs/miniseed/bchh_raw_event_window.mseed: raw accident-window observations.
- paper/inputs/metadata/: original StationXML, CSS calibration, weather workbook,
  launchpad/camera coordinates, reviewed BCHH arrival picks and UCS-3 event frames.
- paper/inputs/legacy_export/: source catalogues and manual picks.
- paper/outputs/: selected compact products and figures from numbered notebooks;
  regional waveform and response caches are included when enabled in Notebook 150.
- manuscript/: explicitly selected TeX and bibliography, journal support files,
  generated event table and available local manuscript figures.
- documentation/: inventory, missing-file report and review reminders.
- SHA256SUMS: checksums for the assembled files and reports.

## Scope and exclusions

The 48-hour/precursor waveform record and the SDS archive are deliberately excluded.
The deposit does not reproduce the extended precursor search. The accident-window
MiniSEED remains required. Source videos, private local_config.toml, object caches,
frame galleries and proprietary software are excluded. Video-dependent steps need
separately obtained footage; missing video-sync products do not prevent assembly.

## Reuse

Create repository/local_config.toml from its template and set external_paths.paper_dir
to ../paper. Rerun upstream notebooks to replace machine-specific absolute paths.
The saved figures and tables are provided as results; this package has not yet been
certified by a clean end-to-end rerun. Update manuscript figure search paths on a
new machine. environment.yml is a dependency specification, not a tested lockfile;
the Infrapy and TwistPy Git dependencies remain unpinned.

## Attribution and rights

LICENSE applies to the software and associated documentation. It does not assign
new rights to third-party waveforms, metadata, maps, videos or journal assets.
Retain original network and asset attribution. Regional FDSN observations are
included by default by the current assembler; verify applicable redistribution
terms before uploading. No permission for source-video redistribution is assumed.
The release DOI and associated publication citation should be added when assigned.
