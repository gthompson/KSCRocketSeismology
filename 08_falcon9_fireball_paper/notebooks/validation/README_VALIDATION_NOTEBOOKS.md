# Falcon 9 paper validation notebooks

These notebooks are deliberately outside the production notebook sequence. They preserve reproducible support for secondary manuscript statements without making the main paper pipeline depend on exploratory or diagnostic analyses.

## V005_validate_bchh_relative_calibration.ipynb

Cross-checks DD1/DD2/DD3 relative raw-count amplitudes using JCSAT-16, AFSPC-6, AMOS-6 and OSIRIS-REx. Intended to support statements about relative calibration stability around September 2016. It does not establish absolute calibration.

## V055_validate_waveform_morphology_non_circular.ipynb

Replots the four named pressure events centered only on directly measured BCHH receiver arrival picks. It therefore supports waveform-morphology descriptions without using the legacy 351 m/s-reduced source times as an independent timing reference. It optionally reads the production high-quality normalized waveform ensemble.

## V085_audit_bchh_named_event_manual_picks.ipynb

Audits the authoritative DD2/DD3 arrival picks, recomputes differential intervals, and optionally permits an independent second manual-picking pass. Re-picks are saved only to validation outputs; the authoritative metadata CSV is never overwritten automatically.

These notebooks expect to live in a `validation/` directory at repository root and locate the repository by finding `modules/project_config.py` in a parent directory.
