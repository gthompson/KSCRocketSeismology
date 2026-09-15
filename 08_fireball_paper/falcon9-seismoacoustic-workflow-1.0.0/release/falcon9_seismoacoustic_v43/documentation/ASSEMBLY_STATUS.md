# Falcon 9 seismo-acoustic Zenodo release staging report

Generated: 2026-09-15T01:41:39.456352+00:00
Status: **INCOMPLETE**

Files: 720
Payload size: 278.6 MB

## Missing required file rules

- Six-channel 48-hour precursor-screen record: `data/miniseed/*48*h*.mseed; data/miniseed/*48hour*.mseed; data/miniseed/*precursor*.mseed`
- Calibration provenance note: `documentation/calibration_provenance.md; docs/calibration_provenance.md`
- Manual video/event timing picks: `data/outputs/150_align_uslaunchreport_video/**/*.json`

## Outstanding author actions

- **BLOCKER** — Supply the six-channel 48-hour precursor-screen MiniSEED and coverage/visual-review provenance.
- **BLOCKER** — Complete and freeze manual classification of the 93 regional automatic candidates, or preserve manuscript wording that states the review is incomplete.
- **BLOCKER** — Resolve/document the initial and principal physical pulse-to-PGV assignments used by Table 1.
- **OPEN_EVIDENCE** — Complete bracketing-launch calibration comparisons; document sensor-head/serial assignments and limits on over-range response.
- **OPEN_EVIDENCE** — Archive the exact AGU slides/report only if restoring the specific historical no-shock attribution.
- **RELEASE** — Add a calibration-provenance note distinguishing adopted empirical factors, nominal response, recollection, and unresolved cause.
- **RELEASE** — Record licenses/citations for data, Cartopy basemaps, InfraPy, TwistPy, and the source video.
- **PERMISSION** — Confirm whether the source/final USLaunchReport movie and derived audio may be redistributed before enabling video inclusion.
- **RELEASE** — Install the final version-43 TeX/support assets and perform a clean portable rerun and final page proof.
- **RELEASE** — Add Zenodo DOI/version metadata after reservation; do not invent a DOI.

## Deliberately excluded by the minimal profile

- Pickle caches and NPZ search surfaces
- Per-event PDF galleries and diagnostic plots
- Rendered PNG movie-frame caches
- Duplicate/generated audio unless redistribution is authorized
- The source video unless separately licensed and explicitly enabled
