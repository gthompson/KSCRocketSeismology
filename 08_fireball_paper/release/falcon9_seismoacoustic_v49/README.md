# Near-field seismo-acoustic analysis of the 2016 Falcon 9 AMOS-6 failure

Version 1.0.0

This archive contains the reproducible Python/Jupyter workflow used to analyze
the seismic and infrasound observations of the 1 September 2016 Falcon 9
AMOS-6 static-fire failure at Space Launch Complex 40, Cape Canaveral.

The notebooks reconstruct and validate the impulsive-event catalogue, estimate
source direction and apparent acoustic velocity, measure acoustic and seismic
amplitudes, evaluate acoustic-to-ground coupling, estimate acoustic energetics,
analyze seismic polarization, align public video and camera audio, and generate
the manuscript figures.

## Release contents

- `notebooks/`: clean, output-free notebooks in execution order.
- `modules/`: shared configuration and project-specific processing helpers.
- `environment.yml`: portable software-environment specification.
- `OUTPUT_CONVENTIONS.md`: ownership and naming rules for derived products.
- `DATA_MANIFEST.md`: required inputs and their expected locations.
- `CITATION.cff`: software citation metadata.
- `LICENSE`: MIT license for the code and notebook source.

The notebooks in this software archive intentionally have embedded outputs
removed. Final derived tables and publication figures should be distributed as
separate files in the associated archival record, rather than duplicated inside
notebook JSON.

## Workflow order

| Number | Notebook | Purpose |
|---:|---|---|
| 000 | `correct_bchh_instrument_response` | Correct instrument responses and calibrate pressure |
| 010 | `prepare_analysis_inputs` | Build canonical waveform and configuration inputs |
| 020 | `analyze_ksc_weather` | Estimate meteorological effective sound speed |
| 030 | `reconcile_manual_event_catalogues` | Reconcile manual picks and construct the event catalogue |
| 040 | `validate_event_catalogue_with_array_processing` | Validate events with continuous Bartlett processing |
| 050 | `review_event_catalogue_waveforms` | Audit retained and excluded event waveforms |
| 060 | `validate_infrasound_baseline_correction` | Test the pressure baseline correction |
| 070 | `prepare_event_waveform_products` | Generate fixed six-channel event segments |
| 080 | `analyze_planar_array_propagation` | Estimate planar back azimuth and apparent velocity |
| 090 | `analyze_finite_distance_propagation` | Test finite-distance wavefront effects |
| 100 | `measure_event_amplitudes_and_acoustic_seismic_coupling` | Measure amplitudes, spectra, and coupling |
| 110 | `measure_named_events` | Measure manually reviewed named events |
| 120 | `estimate_acoustic_energetics` | Estimate sound exposure, acoustic energy, and yield scenarios |
| 130 | `analyze_seismic_polarization` | Rotate ground motion and calculate polarization attributes |
| 140 | `search_for_direct_seismic_waves` | Search for seismic motion preceding the airwave |
| 150 | `align_uslaunchreport_video` | Interactively align public video with the geophysical chronology |
| 160 | `generate_synchronized_phase1_video` | Render the synchronized Phase-I video |
| 170 | `generate_publication_figures` | Generate manuscript and supplementary figures |

Run the notebooks in numerical order unless a notebook explicitly documents an
optional branch. Each notebook writes only beneath its numbered output
directory, as described in `OUTPUT_CONVENTIONS.md`.

## Installation

Create the core environment with:

```bash
conda env create -f environment.yml
conda activate falcon9-seismoacoustics
```

InfraPy and TwistPy are specialized dependencies. The environment file records
their public source repositories. For exact long-term reproduction, replace
the branch references with the commit identifiers used for the final
manuscript run.

FFmpeg is required only for the video notebooks.

## External paths

The workflow contains no machine-specific absolute paths. External locations
are controlled by environment variables:

```bash
export FALCON9_DATA_DIR=/path/to/falcon9_data
export FALCON9_OUTPUT_DIR=/path/to/falcon9_outputs
export FALCON9_SDS_DIR=/path/to/SDS_KSC
export FALCON9_MINISEED_DIR=/path/to/event_miniseed
export FALCON9_USLAUNCHREPORT_VIDEO_FILE=/path/to/source_video.mov
```

Only `FALCON9_DATA_DIR` is generally required when the source-data archive is
unpacked into the layout described by `DATA_MANIFEST.md`. Output defaults to
`$FALCON9_DATA_DIR/outputs`.

## Data and video

The source data are not embedded in this software directory. If distributed in
the same Zenodo record, unpack the accompanying source-data archive and point
`FALCON9_DATA_DIR` to its root. Keeping software and data as separate files in
one record allows the software to be mirrored on GitHub without storing large
waveform files there.

The USLaunchReport source video is not redistributed. Copyright remains with
USLaunchReport.com/Michael Wagner. Obtain an authorized local copy and set
`FALCON9_USLAUNCHREPORT_VIDEO_FILE`. The archival research products may include
frame references, synchronization metadata, and processing code without
including the copyrighted movie.

## Citation

Before publication of the archival record, reserve its DOI and add it to the
manuscript and release metadata. Citation metadata are provided in
`CITATION.cff`.

## Licensing

Code and notebook source are released under the MIT License. Data, third-party
software, public-network waveforms, and video remain subject to their own
licenses and terms; see `DATA_MANIFEST.md`.
