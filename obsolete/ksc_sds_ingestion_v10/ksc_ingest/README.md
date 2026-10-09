# FLOVOpy ingestion migration (from KSC SDS Ingestion v10)

This directory is an **overlay** for an existing FLOVOpy checkout, **not** a standalone Python distribution. Copy the `flovopy/ingest/` directory into your FLOVOpy package, alongside `flovopy/sds/` and `flovopy/enhanced/`.

The library modules are the v10 implementation with import/path/name changes only. KSC mappings, service configs, original notebooks, and recovery scripts are preserved separately under `examples/ksc/`. **No KSC network, station, Gem mapping or disk paths are embedded in the library.**

## CLI

Register `flovopy-ingest = "flovopy.ingest.cli:main"` under `[project.scripts]` in your existing FLOVOpy `pyproject.toml`, then reinstall editable. Alternatively use `python -m flovopy.ingest.cli`.

Generic direct-path commands:

```bash
python -m flovopy.ingest.cli stage-gem /data/gem/mseed /data/staged/SDS --mapping /project/gem_mapping.csv --dry-run
python -m flovopy.ingest.cli stage-siliconaudio /data/station/data /data/staged/SDS --year 2026 --dry-run
python -m flovopy.ingest.cli gem-report /data/gemconvert /data/qc/inventory.csv --mapping /project/gem_mapping.csv --daily-csv /data/qc/daily.csv
```

The original `new-run`, `ingest`, `centaur`, `siliconaudio`, `gem`, `merge-sds`, `rollback`, and `status` project-oriented commands remain available with `--config /path/to/project.yaml`. For example:

```bash
python -m flovopy.ingest.cli --config /path/to/project.yaml merge-sds /data/staged/SDS --dry-run
```

The project-run folder convention is retained as an **optional workflow**, not a KSC requirement. The legacy KSC example configs retain their original local paths and must be reviewed before use.

## Dependencies

Existing FLOVOpy provides `EnhancedSDSClient` and `flovopy.sds.merge_sds_archives`. Ingestion also requires `PyYAML`, `obspy`; `gemlog` is needed only for Gem raw conversion/GPS routines, and `pandas` for relevant reporting functions. Add optional extras to FLOVOpy's packaging as appropriate.

## Limitations

This is a minimal migration, not a redesign. Existing v10 converter/report behavior is unchanged, including limitations of deployment-date coverage and the requirement for explicit Gem mapping. No end-to-end field-data test has been performed.
