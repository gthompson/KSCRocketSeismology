# Falcon 9 notebook light-refactor report

## Implemented

- Added `config/project.yml` as the central path, product, timing, and output configuration.
- Added a YAML-backed `project_config.py` module with notebook-specific output namespaces.
- Each notebook now has a standard bootstrap cell and writes to its own numerically coded output directory.
- Canonical product filenames are prefixed with the producer notebook code where they are declared explicitly.
- Added an upstream-product registry in the YAML configuration.
- Removed the three hard-coded project-root paths in Notebooks 08–10.
- Moved repeated general helpers into `workflow_io.py`.
- Added compatible `bchh_io.py`, `geometry_products.py`, and `plotting.py` modules for imports already used by the notebooks.
- Notebook 12 now imports shared scaling, stream-ordering, and time-array helpers instead of redefining them.
- Cleared notebook execution counts and outputs and validated all notebook JSON structures.

## Output isolation

Each notebook writes beneath:

```text
outputs/<notebook-code>_<notebook-slug>/
    data/
    figures/
    logs/
```

This prevents a downstream notebook from modifying or overwriting an upstream notebook's products.

## Important limitations

- **weather_analysis_fixed.py:** Required by Notebook 03 but not supplied. It contains project-specific weather parsing and aggregation logic and was not recreated because the source implementation was not available.
- **event_measurements.py:** Required by Notebook 11 but not supplied. It contains scientific pressure measurement logic and was not recreated without the original implementation.

The refactor is intentionally light: scientific algorithms were not rewritten or silently inferred.
The two missing project-specific modules must be supplied or reconstructed from their original source before every notebook can execute end to end.

## Recommended next pass

1. Run Notebooks 01–12 in order using a fresh output directory.
2. Correct any product-registry paths that differ from the actual emitted filenames.
3. Supply `weather_analysis_fixed.py` and `event_measurements.py`.
4. Move the planar and finite-distance array-search functions from Notebooks 08–09 into tested modules.
5. Add a small automated smoke test that imports every module and opens every configured upstream product.

## Notebook namespaces

- `01_correct_bchh_instrument_response_refactored.ipynb` → `outputs/01_correct_bchh_instrument_response_refactored/`
- `02_prepare_analysis_inputs.ipynb` → `outputs/02_prepare_analysis_inputs/`
- `03_analyze_ksc_weather.ipynb` → `outputs/03_analyze_ksc_weather/`
- `04_reconcile_manual_event_catalogs.ipynb` → `outputs/04_reconcile_manual_event_catalogs/`
- `05_reconstruct_and_review_event_catalogue.ipynb` → `outputs/05_reconstruct_and_review_event_catalogue/`
- `06_validate_infrasound_baseline_correction.ipynb` → `outputs/06_validate_infrasound_baseline_correction/`
- `07_build_candidate_airwave_catalogue.ipynb` → `outputs/07_build_candidate_airwave_catalogue/`
- `08_planar_array_analysis.ipynb` → `outputs/08_planar_array_analysis/`
- `09_finite_distance_array_analysis.ipynb` → `outputs/09_finite_distance_array_analysis/`
- `10_measure_event_amplitudes_and_acoustic_seismic_coupling.ipynb` → `outputs/10_measure_event_amplitudes_and_acoustic_seismic_coupling/`
- `11_measure_key_events.ipynb` → `outputs/11_measure_key_events/`
- `12_generate_paper_figures_augmented_standalone.ipynb` → `outputs/12_generate_paper_figures_augmented_standalone/`
- `S01_validate_infrabsu_response.ipynb` → `outputs/S01_validate_infrabsu_response/`
- `S02_optimize_infrasound_highpass_filter.ipynb` → `outputs/S02_optimize_infrasound_highpass_filter/`
