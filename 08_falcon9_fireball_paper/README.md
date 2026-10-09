# Streamlined Falcon 9 paper workflow

This directory is a paper-focused replacement notebook sequence built from the preserved 2026 workflow. The archived repository remains the historical record; this sequence intentionally removes exploratory/redundant notebooks.

## Timing policy

The four key opening events now use three explicitly separate timing concepts:

1. **BCHH receiver arrivals**: direct reviewed DD2/DD3 pressure picks in `data/metadata/bchh_named_event_pressure_arrival_picks.csv`.
2. **Independent relative source timing**: frame intervals measured only within the same Pad 39A SpaceX remote camera, in `data/metadata/pad39a_video_event_frames.csv`. The camera is not assumed synchronized to BCHH.
3. **Legacy/model-derived source-time coordinate**: `SOURCE_EVENT_TIMES` remains available for old source-reduced plots and broad chronology, but is explicitly identified as derived by reducing BCHH arrivals at 351 m/s. It must not be used as independent evidence for propagation speed.

## Production sequence

| # | Notebook | Role |
|---|---|---|
| 000 | `000_correct_bchh_instrument_response.ipynb` | response correction and calibrated waveform product |
| 010 | `010_prepare_analysis_inputs.ipynb` | canonical stream, geometry, baseline removal, arrival-pick validation |
| 020 | `020_analyze_ksc_weather.ipynb` | atmosphere and effective acoustic speed |
| 030 | `030_reconcile_manual_event_catalogues.ipynb` | final 153-event catalogue |
| 040 | `040_validate_event_catalogue_with_array_processing.ipynb` | independent Bartlett catalogue validation |
| 050 | `050_prepare_event_waveform_products.ipynb` | final-event waveform products |
| 060 | `060_analyze_planar_array_propagation.ipynb` | refined local array propagation |
| 070 | `070_measure_event_amplitudes_and_acoustic_seismic_coupling.ipynb` | pressure, PGV and coupling |
| 080 | `080_analyze_named_events_and_timing.ipynb` | four named events, direct arrival picks, same-camera video timing, weak-shock timing test |
| 090 | `090_estimate_acoustic_energetics.ipynb` | passband-limited acoustic energetics |
| 100 | `100_analyze_seismic_polarization.ipynb` | BCHH polarization diagnostics |
| 110 | `110_search_for_direct_seismic_waves.ipynb` | focused direct-seismic search |
| 120 | `120_analyze_regional_detectability.ipynb` | regional non-detection analysis |
| 130 | `130_generate_supplement_event_table.ipynb` | supplementary 153-event table |
| 140 | `140_generate_publication_figures.ipynb` | figures from authoritative products, including differential-timing figure |
| 150 | `150_assemble_zenodo_release.ipynb` | release assembly |

## Removed from production sequence

Standalone calibration review, waveform-gallery review, baseline-correction validation, finite-distance range inversion, USLaunchReport absolute alignment, synchronized movie rendering, manual-picking utility, and old video-waveform figure notebooks are intentionally not production dependencies. Their useful conclusions are either folded into the retained notebooks or superseded by the Pad 39A same-camera timing analysis.

## Key current Pad 39A observations

- reference event: `13:07:12.03`, second 60-fps member;
- principal: `13:07:15.21` second through `13:07:15.23` second (visual onset bracket);
- payload impact: `13:07:24.18`, second;
- payload explosion: `13:07:25.06`, first.

The earlier `13:07:24.15` second payload candidate is retained in the metadata table as an excluded audit candidate.
