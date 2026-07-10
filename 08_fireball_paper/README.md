# Falcon 9 paper figure workflow

## Contents

```text
falcon9_paper_figures/
├── generate_all_paper_figures.ipynb
├── modules/
│   ├── kml_utils.py
│   ├── xml_utils.py
│   ├── physics.py
│   └── figure1_utils.py
├── notebooks/
│   ├── 01_generate_figure1.ipynb
│   └── 02_generate_figures_other_than_1.ipynb
├── metadata/
│   ├── launchpads_cameras.kml   # add locally
│   └── KSC.xml                  # add locally
├── outputs/
│   ├── main/
│   └── supplement/
├── cache/
└── archive/
    └── read_launchpads_from_kml.py
```

## Design

- KML parsing is centralized in `modules/kml_utils.py`.
- StationXML processing is centralized in `modules/xml_utils.py`.
- Acoustic calculations are centralized in `modules/physics.py`.
- Figure 1 plotting helpers remain in `modules/figure1_utils.py`.
- The duplicate `read_launchpads_from_kml.py` is archived and is not imported.
- Each figure notebook can run independently.
- `generate_all_paper_figures.ipynb` runs the current figure notebooks sequentially.

## Before running

1. Copy `launchpads_cameras.kml` and `KSC.xml` into `metadata/`.
2. Check the external MiniSEED and audio paths in
   `notebooks/02_generate_figures_other_than_1.ipynb`.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run either notebook independently, or run
   `generate_all_paper_figures.ipynb`.

## Future split

The second notebook currently generates several figures. Once the final paper
figure list stabilizes, it can be split into `02_...ipynb`, `03_...ipynb`, and
so on without changing the shared metadata modules.
