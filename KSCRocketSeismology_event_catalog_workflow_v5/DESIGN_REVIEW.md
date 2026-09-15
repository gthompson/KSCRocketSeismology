# Design review of the three original code areas

## 04_event_catalog

This is currently the strongest scientific-processing area, but it mixes four concerns: launch-list ingestion, waveform extraction, event detection, and metric generation. The newer `compute_launch_peaks_physical.py` / development notebooks are substantially more modern than the website notebooks and should be the basis of the next migration.

Main issues found:
- several competing launch CSVs with overlapping schemas;
- development logic duplicated between notebooks and scripts;
- path/configuration embedded in scripts/notebooks;
- derived artifact paths stored without a permanent launch key;
- FLOVOpy/ObsPy details leak into downstream catalog consumers.

## 05_website

This is the oldest layer architecturally. It assumes server-local `/var/www`, `/shares/...` paths, custom `header`, `libWellData`, PICKLE waveform files and side-effect execution. It also rebuilds subsets of launch metadata specifically for the site.

The replacement deliberately makes the web site a pure static consumer of the canonical catalog. This is much easier to test, deploy, archive and reproduce.

## 07_ensemble_paper

The newer plotting work is cleaner, but still reads `merged_launches.csv` directly and contains user-machine paths (`~/Dropbox/KSC_paper`). Rocket-family and SLC normalization logic belongs in the shared package because the website and every ensemble paper will need exactly the same definitions.

The station-map module is already relatively reusable and is retained as a standalone utility with optional GIS dependencies.

## Proposed data flow

```text
launch source tables / APIs
          |
          v
 canonical launch catalog  <------- permanent event_id
          |
     +----+---------------------+
     |                          |
     v                          v
waveform/metrics pipeline    static website
     |
     v
product manifest
     |
     +--------------------------+
                                v
                        ensemble analyses/papers
```

The important rule is that paper notebooks should no longer clean/normalize the launch population independently. They should select from a versioned canonical catalog and join versioned derived products.
