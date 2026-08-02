from __future__ import annotations

import os
import sys
from pathlib import Path


# -----------------------------------------------------------------------------
# Project locations
# -----------------------------------------------------------------------------

# project_config.py is expected at:
# <project root>/modules/project_config.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = PROJECT_ROOT / "modules"
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks2"


# -----------------------------------------------------------------------------
# External data locations
# -----------------------------------------------------------------------------

# Environment variables allow these machine-specific paths to be overridden.
DATA_DIR = Path(
    os.environ.get(
        "FALCON9_DATA_DIR",
        "~/Library/CloudStorage/Box-Box/thompsong/"
        "3_Project_Documents/NASAprojects/"
        "201602_Rocket_Seismology/writing/spacex_paper/data",
    )
).expanduser()

# obsolete - replaced by SDS
MINISEED_DIR = Path(
    os.environ.get(
        "FALCON9_MINISEED_DIR",
        "/Volumes/haldata/KSC/beforePASSCAL/EVENTS/"
        "20160901_SpaceXplosion",
    )
).expanduser()

SDS_DIR = "/Volumes/haldata/remastered/SDS_KSC"

ROCKET_CATALOG_DIR = Path('~/Library/CloudStorage/Box-Box/thompsong/DATA/rocket_events').expanduser()


# -----------------------------------------------------------------------------
# Metadata inputs
# -----------------------------------------------------------------------------

LEGACY_EXPORT_DIR = DATA_DIR / "legacy_export"
METADATA_DIR = DATA_DIR / "metadata"

STATIONXML_FILE = METADATA_DIR / "KSC.xml"
CSS_CALIBRATION_FILE = METADATA_DIR / "sitedb.calibration"

KML_FILE = METADATA_DIR / "launchpads_cameras.kml"


# -----------------------------------------------------------------------------
# Notebook 01 output products
# -----------------------------------------------------------------------------

OUTPUT_DIR = DATA_DIR / "outputs2"

RAW_MSEED = OUTPUT_DIR / "01_bchh_raw_event_window.mseed"
EVENT_STATIONXML_COPY = OUTPUT_DIR / "01_bchh_event_inventory_original.xml"
CHANNEL_METADATA_CSV = OUTPUT_DIR / "01_bchh_channel_metadata.csv"
ACTIVE_CALIBRATION_CSV = OUTPUT_DIR / "01_bchh_active_antelope_calibration.csv"
PROCESSING_JSON = OUTPUT_DIR / "01_bchh_response_processing.json"

FINAL_INVENTORY_XML = OUTPUT_DIR / "01_BCHH_20160901_empirically_calibrated.xml"
FINAL_CORRECTED_MSEED = OUTPUT_DIR / "01_BCHH_20160901_response_corrected.mseed"
FINAL_CORRECTED_PICKLE = OUTPUT_DIR / "01_BCHH_20160901_response_corrected.pkl"
FINAL_CORRECTION_SUMMARY = OUTPUT_DIR / "01_BCHH_20160901_correction_summary.csv"

from obspy.core import UTCDateTime
EXPLOSION_TIME = UTCDateTime("2016-09-01T13:07:12.080")
PRETRIGGER_WINDOW = 180.0
POSTTRIGGER_WINDOW = 1800.0


# -----------------------------------------------------------------------------
# Notebook 02 output products
# -----------------------------------------------------------------------------
import pandas as pd
events = pd.DataFrame([
    {
        "event_id": "upper_stage",
        "label": "Upper Stage",
        "source_time": str(EXPLOSION_TIME),
    },
    {
        "event_id": "lower_stage",
        "label": "Lower Stage",
        "source_time": str(UTCDateTime("2016-09-01T13:07:15.750")),
    },
    {
        "event_id": "capsule_impact",
        "label": "Capsule Impact",
        "source_time": str(UTCDateTime("2016-09-01T13:07:24.600")),
    },
    {
        "event_id": "capsule_explosion",
        "label": "Capsule Explosion",
        "source_time": str(UTCDateTime("2016-09-01T13:07:25.150")),
    },
])


# -----------------------------------------------------------------------------
# Project output locations
# -----------------------------------------------------------------------------

DERIVED_DIR = DATA_DIR / "derived2"
FIGURE_DIR = DATA_DIR / "figures2"

RESPONSE_CORRECTION_DIR = (
    OUTPUT_DIR
    / "response_correction"
)

for dirname in (METADATA_DIR, OUTPUT_DIR, DERIVED_DIR, FIGURE_DIR):
    dirname.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def find_project_root(start: str | Path | None = None) -> Path:
    """Find the repository root from a path inside the project."""
    if start is None:
        return PROJECT_ROOT

    current = Path(start).expanduser().resolve()

    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "modules" / "project_config.py").exists():
            return candidate

    raise FileNotFoundError(
        f"Could not locate the project root above {current}"
    )


def add_modules_to_path(
    project_root: str | Path = PROJECT_ROOT,
) -> Path:
    """Add the project's modules directory to sys.path."""
    module_dir = Path(project_root).resolve() / "modules"

    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

    return module_dir


def ensure_input_directories() -> None:
    """Create directories that hold externally managed input data."""
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def ensure_output_dirs() -> dict[str, Path]:
    """Create and return all standard output directories."""
    paths = {
        "data_outputs": OUTPUT_DIR,
        "project_outputs": PROJECT_OUTPUT_DIR,
        "derived": DERIVED_DIR,
        "figures": FIGURE_DIR,
        "response_correction": RESPONSE_CORRECTION_DIR,
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def validate_required_inputs() -> None:
    """Raise a useful error if required input files are unavailable."""
    required = {
        "MiniSEED directory": MINISEED_DIR,
        "StationXML file": STATIONXML_FILE,
        "CSS calibration file": CSS_CALIBRATION_FILE,
    }

    missing = [
        f"{label}: {path}"
        for label, path in required.items()
        if not path.exists()
    ]

    if missing:
        message = "\n".join(f"- {item}" for item in missing)
        raise FileNotFoundError(
            "Required Falcon 9 inputs were not found:\n"
            f"{message}"
        )
