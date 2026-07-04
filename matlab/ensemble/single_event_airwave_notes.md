# Single-event airwave workflow

`rocket_airwave_event_analysis.m` is not part of the ensemble refactor proper. It is a single-event analysis workflow and overlaps strongly with the later Falcon 9 fireball refactor.

Its useful pieces are already represented in shared/project code elsewhere:

- speed of sound and wind-corrected travel times,
- array coordinate conversion,
- array map plotting,
- arrival association,
- event waveform segmentation,
- amplitude measurements,
- cross-correlation and beamforming,
- acoustic energy and CSV export,
- particle-motion diagnostics.

For the ensemble project, the relevant concepts are handled by:

- `10_preprocess_rocketmaster.m`
- `20_analyze_ensemble.m`
- `30_plot_ensemble_results.m`

The original script is preserved in `archive_originals/rocket_airwave_event_analysis_original.m`.
