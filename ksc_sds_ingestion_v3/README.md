# KSC SDS ingestion v3

This revision uses `YYYYMMDD_service/00_download/...` service-run directories and one canonical project-level `SDS/` archive. There is no duplicate service-run SDS archive.

Centaur ingestion is implemented first and is a thin wrapper around the new transactional FLOVOpy SDS merger. Other acquisition adapters are intentionally deferred until their real workflows/data are available.

## Example

```bash
ksc-sds --config config/ksc.yaml new-run 2026-09-22 --end-date 2026-09-24
ksc-sds --config config/ksc.yaml centaur 20260922_service --dry-run --mode fast
ksc-sds --config config/ksc.yaml centaur 20260922_service --mode fast
```

If you do not want to copy a large Centaur SDS from the SD card into `00_download/Centaur`, point directly at the mounted card:

```bash
ksc-sds --config config/ksc.yaml centaur 20260922_service \
  --source /Volumes/CENTAUR_CARD/2026 --dry-run
```

Then rerun without `--dry-run` after reviewing the plan.
