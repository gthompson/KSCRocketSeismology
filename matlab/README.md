# Falcon 9 Fireball MATLAB

This repository contains MATLAB software used to analyze the seismic and
infrasound recordings of the **1 September 2016 Falcon 9 static-fire
explosion** at Launch Complex 40, Kennedy Space Center. The original
monolithic workflow has been refactored into a modular, reproducible
pipeline with reusable package functions.

## Repository structure

Core workflow:

-   `10_import_data.m` -- import waveform data from an Antelope/CSS
    database or MATLAB cache, define array geometry and environmental
    parameters, and create/update the Level-1 cache.
-   `20_process_events.m` -- detect and group impulsive infrasound
    arrivals, compute travel times, cross-correlate array channels,
    build `master_event`, beamform the array, measure amplitudes and
    energies, and write event tables.
-   `30_make_figures.m` -- regenerate all manuscript figures, including
    waveform panels, the Beach House array map, travel-time corrected
    event plots, and beamforming diagnostics.
-   `40_make_synchronized_video.m` *(optional)* -- create synchronized
    videos showing rocket footage together with scrolling seismic and
    infrasound data for presentations, validation, and outreach.

`falcon9fireball_wrapper.m` executes the workflow. By default it runs
stages 10--30; stage 40 can be enabled with a configuration flag.

## MATLAB packages

### `+falcon9`

Core analysis functions including beamforming, event segmentation,
plotting, travel-time prediction, master-event construction,
peak-to-peak amplitude measurement, event-table export, array-map
plotting, and configuration.

### `+physics`

General atmospheric utilities such as temperature conversion and
speed-of-sound calculations.

### `+infrasound`

Generic infrasound processing utilities, including acoustic energy
calculations.

### `+video`

Reusable functions for synchronizing one or more videos with seismic and
infrasound waveforms.

### `demos`

Presentation material, including the beamforming animation used for
conference talks.

## Workflow summary

1.  Import or load waveform data.
2.  Compute geometry, weather corrections, and predicted travel times.
3.  Detect and group impulsive infrasound arrivals.
4.  Segment waveform windows.
5.  Cross-correlate array channels.
6.  Build a representative `master_event`.
7.  Estimate apparent velocity and back-azimuth by beamforming.
8.  Measure amplitudes, pressures, and acoustic energy.
9.  Export event tables.
10. Regenerate figures.
11. Optionally render synchronized video products.

## External software

Required: - MATLAB - GISMO toolbox - Signal Processing Toolbox

Required when importing directly from raw data: - Antelope MATLAB
interface

Optional: - Mapping Toolbox (only if GISMO helper functions requiring it
are used; most coordinate conversions have been refactored to avoid this
dependency) - VideoReader/VideoWriter support (for stage 40)

## Main derived products

-   `explosion2.mat` -- cached waveform and processed analysis
    workspace.
-   `master_event` -- representative inter-sensor lag model derived from
    the infrasound event catalog.
-   `eventlist.csv` -- measured event parameters.
-   Publication figures.
-   Optional synchronized presentation videos.

## Notes

The original exploratory scripts have been consolidated into reusable
package functions where practical. Legacy scripts are retained only for
historical reference.
