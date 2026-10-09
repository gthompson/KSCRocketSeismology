# Install release updates

Copy CITATION.cff, DATA_MANIFEST.md, environment.yml and LICENSE into:
/Users/thompsong/Developer/KSCRocketSeismology/08_falcon9_fireball_paper/

Copy notebooks/150_assemble_zenodo_release.ipynb into that repository's notebooks/.
Version is 1.0.0; citation date is 2026-10-06. MIT LICENSE is unchanged.

Restart the notebook kernel and run. Defaults select main61.tex, supplement61.tex
and falcon9_bibfile.bib from latex/. Existing environment variables override defaults.
Existing releases remain protected; set ZENODO_REPLACE=1 intentionally to replace
with timestamped backups. Set ZENODO_BUILD=0 for audit only.

Verification: isolated inventory with these files installed found no missing required
rules; raw accident-window MiniSEED selected. Production release was not rebuilt or
modified. Audit reports included here refer to the temporary validation checkout.
The revised environment adds xlrd and optional-map dependency cartopy; it has not
been installed/tested from scratch, and upstream Git dependencies remain unpinned.

Optional now: calibration provenance document and video synchronization product.
Excluded: extended precursor/48-hour records. Required: environment, license,
citation/data manifest, main observations and core outputs, selected manuscripts.
Author reminders are not blanket build blockers; rights/attribution need checking
before upload. DOI can be added after reservation. No new rights are assigned.

Remaining portability limitation: manuscripts retain external absolute figure paths;
legacy figures outside the manuscript figures/ directory are not gathered automatically.
The banner and local figures/generated tables are included when present. A compiled,
portable manuscript package and a clean scientific rerun are not certified by this audit.
