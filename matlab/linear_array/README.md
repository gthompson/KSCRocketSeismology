# Huddle linear-array MATLAB analysis

This refactor uses a shared `+rocketseis` package for generic rocket-seismology utilities and a smaller `+huddle` package for project-specific logic.

## Structure

```text
10_import_huddle_data.m
20_analyze_huddle_xcorr.m
30_plot_huddle_results.m
huddle_wrapper.m

+rocketseis/
  latlonToEastNorth.m
  loadMiniSeedWaveforms.m
  computeSlidingXcorr.m
  computeStaLtaDetections.m
  plotArrayMap.m
  plotXcorrTracks.m

+huddle/
  config2018290.m
  collapseAdjacentDelays.m
  estimateAmplitudeRatios.m
  plotAmplitudeRatios.m
```

## Shared functions reused from the Falcon 9 work

Useful shared ideas/functions:

- `latlonToEastNorth` — directly reusable, moved to `+rocketseis`.
- `plotArrayMap` — conceptually reusable, generalized into `+rocketseis/plotArrayMap.m`.
- Sliding-window cross-correlation — generic enough for huddle and future rocket arrays, implemented as `+rocketseis/computeSlidingXcorr.m`.

Not directly useful for the huddle project:

- `measurePeakToPeakAmplitude.m` — useful for impulsive pressure events in Falcon 9, but the huddle script is focused on sliding-window lags and amplitude ratios.
- `plotEvents.m` — useful for segmented infrasound event catalogs, but not central to this continuous huddle-window analysis.

## Workflow

1. `10_import_huddle_data.m` loads MiniSEED data and computes local station coordinates.
2. `20_analyze_huddle_xcorr.m` runs STA/LTA diagnostics, sliding-window xcorr, adjacent-pair delay collapse, and amplitude-ratio calibration.
3. `30_plot_huddle_results.m` plots array geometry, waveform panels, cross-correlation tracks, and amplitude-ratio diagnostics.

## Dependencies

- MATLAB
- GISMO toolbox
- Signal Processing Toolbox
- Optional original station metadata script: `network2batch_20181016.m`

Mapping Toolbox is not required by the refactored coordinate conversion.
