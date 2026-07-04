# Rocket launch ensemble MATLAB analysis

This refactor consolidates the legacy ensemble scripts:

- `preprocess_rocketmaster.m`
- `load_all_rocket_events2.m`
- `ensemble_analysis.m`
- `rocket_airwave_event_analysis.m`

into a numbered, reusable workflow.

## Main workflow

```text
10_preprocess_rocketmaster.m
20_analyze_ensemble.m
30_plot_ensemble_results.m
```

Use:

```matlab
rocketensemble_wrapper
```

to run all three stages.

## Algorithm

### 10 — Preprocess `rocketmaster`

1. Configure the Antelope/CSS `rocketmaster2` database.
2. Load arrivals into a GISMO `Arrival` object.
3. Add short waveform snippets to each arrival.
4. Compute arrival waveform metrics.
5. Associate arrivals into launch-scale `Catalog` events.
6. Add event-scale BCHH waveform windows.
7. Add waveform metrics to event waveform sets.
8. Save `rocketmaster.mat`.
9. Optionally write a derived Antelope database.

### 20 — Analyze ensemble

1. Load the cached `Catalog`.
2. Compute scalar event-level metrics.
3. Extract representative infrasound and seismic channels, one per launch/day.
4. Save `rocket_ensemble_metrics.mat`.

### 30 — Plot results

1. Make per-event waveform plots.
2. Make infrasound and seismic spectrograms.
3. Write infrasound and seismic audio files.
4. Plot crude Doppler/trajectory proxy diagnostics.
5. Plot smoothed event envelopes.
6. Plot ensemble-level summary metrics.
7. Plot representative infrasound/seismic waveform panels.
8. Optionally call `gismo_ext.plotAverageFrequency` for frequency-track summaries.

## Package

Reusable functions are in:

```text
+rocketensemble/
```

Important functions include:

- `config.m`
- `loadArrivals.m`
- `addArrivalWaveforms.m`
- `addArrivalMetrics.m`
- `associateArrivals.m`
- `addEventWaveforms.m`
- `addEventWaveformMetrics.m`
- `computeEnsembleMetrics.m`
- `makeEventDiagnostics.m`
- `computeEventSpectralMetrics.m`
- `plotTrajectoryProxy.m`
- `extractRepresentativeWaveforms.m`
- `plotEnsembleSummary.m`

## Dependencies

Required:

- MATLAB
- GISMO
- Antelope MATLAB interface
- Signal Processing Toolbox
- `+gismo_ext/plotAverageFrequency.m` for the optional average-frequency summary

Expected GISMO/Antelope-era functions/classes include:

- `datasource`
- `Arrival`
- `Catalog`
- `ChannelTag`
- `waveform`
- `plot_panels`
- `spectralobject`
- `spectrogram`
- `waveform2sound`
- `addmetrics`
- `clean`, `fillgaps`, `detrend`

## Notes

`rocket_airwave_event_analysis.m` is a single-event workflow, not an ensemble workflow. It is archived here for provenance, but most of its useful science logic has already been folded into the Falcon 9 fireball refactor and shared rocket-seismology utilities.

The refactor keeps the original exploratory products — seismograms, spectrograms, WAV files, Doppler/trajectory proxies, and envelopes — but separates preprocessing, metric extraction, and plotting.
