# Falcon 9 workflow output conventions

All workflow products are written beneath one root:

```text
${FALCON9_OUTPUT_DIR}
```

If `FALCON9_OUTPUT_DIR` is unset, the default is:

```text
${FALCON9_DATA_DIR}/outputs
```

Each notebook owns one immediate subdirectory beginning with its three-digit
workflow number, for example:

```text
outputs/
├── 000_correct_bchh_instrument_response/
├── 010_prepare_analysis_inputs/
├── 020_analyze_ksc_weather/
⋮
└── 170_generate_publication_figures/
```

CSV, JSON, MiniSEED, Pickle, XML, PDF, audio, and video products are kept
inside the numbered directory belonging to their producing notebook. Products
therefore do not require a duplicate numeric prefix in their filenames.

Scientific and diagnostic figures are written only as PDF. The PNG files under
`160_generate_synchronized_phase1_video/frames_*` are an intentional exception:
they are intermediate raster frames required by FFmpeg and are not standalone
scientific figure products.

The common root and every numbered directory are defined centrally in
`modules/project_config.py`. Set `FALCON9_OUTPUT_DIR` before starting Jupyter if
a different output location is required.
