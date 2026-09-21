# Data manifest

The workflow expects external inputs beneath `FALCON9_DATA_DIR`, with optional
overrides defined in `modules/project_config.py`. This document describes the
logical layout; the final data deposit should add file sizes and SHA-256
checksums for every distributed source-data archive.

## Expected layout

```text
FALCON9_DATA_DIR/
├── metadata/
│   ├── KSC.xml
│   ├── sitedb.calibration
│   └── launchpads_cameras.kml
├── legacy_export/
│   ├── manual_arrival_picks.csv
│   ├── legacy_infrasound_event_catalogue.csv
│   └── legacy_catalog_157_events.csv
├── event_miniseed/
├── SDS/
└── outputs/
```

The precise source files used by Notebook 000 and the SDS time span required
by later notebooks should be listed here after the final data bundle is
assembled. Do not include machine-specific paths.

## Recommended Zenodo packaging

Upload the following as separate files within one archival record when their
combined size and licensing permit:

1. `falcon9-seismoacoustic-workflow-1.0.0.zip` -- software and notebooks.
2. `falcon9-source-data-1.0.0.zip` -- waveform and metadata inputs.
3. `falcon9-derived-products-1.0.0.zip` -- final CSV/JSON/XML products and PDF figures.

This provides one DOI while allowing the software archive alone to be mirrored
on GitHub.

## Rights and exclusions

- Confirm that BCHH waveform data, field calibration products, manual picks,
  and site metadata may be released openly before including them.
- IU.DWPF data should normally be retrieved through FDSN services and cited
  under the IU network citation rather than redistributed unnecessarily.
- Do not redistribute the USLaunchReport video without separate authorization;
  distribute only synchronization metadata, checksums, and processing code.
- Do not include confidential reports, credentials, personal correspondence,
  or proprietary Antelope software.
- Third-party software retains its original license.
