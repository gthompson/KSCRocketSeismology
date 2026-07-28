# Falcon 9 Fireball Python workflow

## Setup

1. Edit `config/project.yml`.
2. Ensure the project-specific metadata and raw waveform paths exist.
3. Install dependencies, including `pyyaml`, `obspy`, `pandas`, `numpy`,
   `matplotlib`, `pyproj`, and the packages required by individual notebooks.
4. Run notebooks in numerical order.

Every notebook writes to its own numerically coded namespace under `outputs/`.
Existing outputs are protected from accidental overwrite unless
`outputs.overwrite_existing` is set to `true` in the YAML file.

See `docs/REFACTOR_REPORT.md` for known limitations and the missing modules
that still require their original source implementations.
