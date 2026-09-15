"""Shared configuration for the Falcon 9 seismo-acoustic workflow.

Expected repository layout::

    falcon9-seismoacoustic-workflow-1.0.0/
        modules/project_config.py
        notebooks/
        data/metadata/
        data/miniseed/
        data/outputs/

Repository paths are derived from this file. Optional machine-specific paths
are read from ``local_config.toml`` in the repository root. That file is not
part of the public repository; use ``local_config.example.toml`` as a template.
"""

from __future__ import annotations

import sys
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 and earlier
from pathlib import Path

import pandas as pd
from obspy.core import UTCDateTime


# -----------------------------------------------------------------------------
# Repository locations
# -----------------------------------------------------------------------------

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"

DATA_DIR = PROJECT_ROOT / "data"
METADATA_DIR = DATA_DIR / "metadata"
MINISEED_DIR = DATA_DIR / "miniseed"
OUTPUT_DIR = DATA_DIR / "outputs"
LEGACY_EXPORT_DIR = DATA_DIR / "legacy_export"


LOCAL_CONFIG_FILE = PROJECT_ROOT / "local_config.toml"


def _load_local_config() -> dict:
    """Load optional machine-specific settings from the repository root."""
    if not LOCAL_CONFIG_FILE.is_file():
        return {}
    with LOCAL_CONFIG_FILE.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a TOML table in {LOCAL_CONFIG_FILE}")
    return payload


LOCAL_CONFIG = _load_local_config()


def _optional_local_path(key: str) -> Path | None:
    """Return an optional path from ``[external_paths]`` in local_config.toml."""
    external_paths = LOCAL_CONFIG.get("external_paths", {})
    if not isinstance(external_paths, dict):
        raise TypeError(
            f"[external_paths] in {LOCAL_CONFIG_FILE} must be a TOML table"
        )
    value = external_paths.get(key)
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


# Optional fallback used by Notebook 000 only when RAW_MSEED is absent.
SDS_DIR = _optional_local_path("sds_dir")

# The copyrighted source movie is not included in the repository deposit.
USLAUNCHREPORT_VIDEO_FILE = _optional_local_path(
    "uslaunchreport_video_file"
)


# -----------------------------------------------------------------------------
# Repository input products
# -----------------------------------------------------------------------------

# Notebook 000 falls back to SDS_DIR only when this primary input is absent.
RAW_MSEED = MINISEED_DIR / "01_bchh_raw_event_window.mseed"

STATIONXML_FILE = METADATA_DIR / "KSC.xml"
CSS_CALIBRATION_FILE = METADATA_DIR / "sitedb.calibration"
KML_FILE = METADATA_DIR / "launchpads_cameras.kml"


# -----------------------------------------------------------------------------
# Standardized workflow output locations
# -----------------------------------------------------------------------------

def notebook_output_dir(number: str | int, slug: str) -> Path:
    """Return the canonical output directory for one workflow notebook."""
    number_text = f"{int(number):03d}"
    clean_slug = str(slug).strip().replace(" ", "_")
    if not clean_slug:
        raise ValueError("Notebook output slug cannot be empty")
    return OUTPUT_DIR / f"{number_text}_{clean_slug}"


NB000_DIR = notebook_output_dir(0, "correct_bchh_instrument_response")
NB010_DIR = notebook_output_dir(10, "prepare_analysis_inputs")
NB020_DIR = notebook_output_dir(20, "analyze_ksc_weather")
NB030_DIR = notebook_output_dir(30, "reconcile_manual_event_catalogues")
NB040_DIR = notebook_output_dir(
    40, "validate_event_catalogue_with_array_processing"
)
NB050_DIR = notebook_output_dir(50, "review_event_catalogue_waveforms")
NB060_DIR = notebook_output_dir(
    60, "validate_infrasound_baseline_correction"
)
NB070_DIR = notebook_output_dir(70, "prepare_event_waveform_products")
NB080_DIR = notebook_output_dir(80, "analyze_planar_array_propagation")
NB090_DIR = notebook_output_dir(90, "analyze_finite_distance_propagation")
NB100_DIR = notebook_output_dir(
    100, "measure_event_amplitudes_and_acoustic_seismic_coupling"
)
NB110_DIR = notebook_output_dir(110, "measure_named_events")
NB120_DIR = notebook_output_dir(120, "estimate_acoustic_energetics")
NB130_DIR = notebook_output_dir(130, "analyze_seismic_polarization")
NB140_DIR = notebook_output_dir(140, "search_for_direct_seismic_waves")
NB145_DIR = notebook_output_dir(145, "analyze_regional_detectability")
NB150_DIR = notebook_output_dir(150, "align_uslaunchreport_video")
NB160_DIR = notebook_output_dir(160, "generate_synchronized_phase1_video")
NB170_DIR = notebook_output_dir(170, "generate_publication_figures")

NOTEBOOK_OUTPUT_DIRS = (
    NB000_DIR,
    NB010_DIR,
    NB020_DIR,
    NB030_DIR,
    NB040_DIR,
    NB050_DIR,
    NB060_DIR,
    NB070_DIR,
    NB080_DIR,
    NB090_DIR,
    NB100_DIR,
    NB110_DIR,
    NB120_DIR,
    NB130_DIR,
    NB140_DIR,
    NB145_DIR,
    NB150_DIR,
    NB160_DIR,
    NB170_DIR,
)


# Notebook 000 authoritative response-correction products.
EVENT_STATIONXML_COPY = NB000_DIR / "bchh_event_inventory_original.xml"
CHANNEL_METADATA_CSV = NB000_DIR / "bchh_channel_metadata.csv"
ACTIVE_CALIBRATION_CSV = NB000_DIR / "bchh_active_antelope_calibration.csv"
PROCESSING_JSON = NB000_DIR / "bchh_response_processing.json"

FINAL_INVENTORY_XML = NB000_DIR / "BCHH_20160901_empirically_calibrated.xml"
FINAL_CORRECTED_MSEED = NB000_DIR / "BCHH_20160901_response_corrected.mseed"
FINAL_CORRECTED_PICKLE = NB000_DIR / "BCHH_20160901_response_corrected.pkl"
FINAL_CORRECTION_SUMMARY = NB000_DIR / "BCHH_20160901_correction_summary.csv"

# Optional catalogue registration stays within Notebook 000's output tree.
ROCKET_CATALOG_DIR = NB000_DIR / "event_catalogue"


# -----------------------------------------------------------------------------
# Authoritative event, video, and display timing
# -----------------------------------------------------------------------------

# Source times inferred by reducing reviewed BCHH pressure arrivals with the
# meteorologically predicted 351 m/s source-to-array velocity.
SOURCE_EVENT_TIMES = {
    "upper_stage": UTCDateTime("2016-09-01T13:07:11.9130"),
    "lower_stage": UTCDateTime("2016-09-01T13:07:15.5136"),
    "payload_impact": UTCDateTime("2016-09-01T13:07:24.4200"),
    "payload_explosion": UTCDateTime("2016-09-01T13:07:24.9875"),
    "event_024": UTCDateTime("2016-09-01T13:07:26.4580"),
}

# Earlier development products used ``capsule_*`` identifiers. Falcon 9 was
# carrying the AMOS-6 payload rather than a crew capsule, so new code and new
# products use ``payload_*``. These aliases are deliberately kept outside
# SOURCE_EVENT_TIMES: adding duplicate dictionary entries would cause code that
# iterates over the event table to process the same physical events twice.
LEGACY_SOURCE_EVENT_KEY_ALIASES = {
    "capsule_impact": "payload_impact",
    "capsule_explosion": "payload_explosion",
    "after_capsule_explosion": "event_024",
}

# Backward-compatible name used by the notebook sequence.
EXPLOSION_TIME = SOURCE_EVENT_TIMES["upper_stage"]

# Native movie PTS used to anchor the upper-stage event. The recording has no
# independent absolute UTC clock.
VIDEO_ANCHOR_MOVIE_S_UNCORRECTED = 71.70496666666667
USLAUNCHREPORT_AV_TIME_SHIFT_S = 0.0164
VIDEO_ANCHOR_MOVIE_S = (
    VIDEO_ANCHOR_MOVIE_S_UNCORRECTED
    + USLAUNCHREPORT_AV_TIME_SHIFT_S
)
VIDEO_ANCHOR_UTC = SOURCE_EVENT_TIMES["upper_stage"]

VIDEO_NOMINAL_FPS = 30000 / 1001
VIDEO_PICK_UNCERTAINTY_S = 1.0 / VIDEO_NOMINAL_FPS


# Broad overview annotations. These intervals are not event-catalogue entries.
OVERVIEW_PHASE_INTERVALS = (
    (
        "Phase I",
        SOURCE_EVENT_TIMES["upper_stage"],
        SOURCE_EVENT_TIMES["upper_stage"] + 70.0,
    ),
    (
        "Phase II",
        UTCDateTime("2016-09-01T13:14:15") - 10.0,
        UTCDateTime("2016-09-01T13:15:45") + 10.0,
    ),
    (
        "Phase III",
        UTCDateTime("2016-09-01T13:19:12") - 10.0,
        UTCDateTime("2016-09-01T13:25:00"),
    ),
    (
        "Phase IV",
        UTCDateTime("2016-09-01T13:29:54") - 15.0,
        UTCDateTime("2016-09-01T13:34:54"),
    ),
)

OVERVIEW_PROLONGED_SIGNAL_INTERVAL = (
    UTCDateTime("2016-09-01T13:08:48"),
    UTCDateTime("2016-09-01T13:12:00"),
)

# No empirical display shift is applied after physical travel-time reduction.
REDUCED_TIME_RESIDUAL_SHIFT_S = 0.0
LEGACY_REDUCED_TIME_SHIFT_CANDIDATE_S = 0.20

PRETRIGGER_WINDOW = 180.0
POSTTRIGGER_WINDOW = 1800.0


# -----------------------------------------------------------------------------
# Shared named-event table used by Notebook 010
# -----------------------------------------------------------------------------

events = pd.DataFrame(
    [
        {
            "event_id": "upper_stage",
            "label": "Upper stage",
            "source_time": str(SOURCE_EVENT_TIMES["upper_stage"]),
        },
        {
            "event_id": "lower_stage",
            "label": "Principal explosion",
            "source_time": str(SOURCE_EVENT_TIMES["lower_stage"]),
        },
        {
            "event_id": "payload_impact",
            "label": "Payload impact",
            "source_time": str(SOURCE_EVENT_TIMES["payload_impact"]),
        },
        {
            "event_id": "payload_explosion",
            "label": "Payload explosion",
            "source_time": str(SOURCE_EVENT_TIMES["payload_explosion"]),
        },
        {
            "event_id": "event_024",
            "label": "Event 024",
            "source_time": str(SOURCE_EVENT_TIMES["event_024"]),
        },
    ]
)


# -----------------------------------------------------------------------------
# Backward-compatible output aliases
# -----------------------------------------------------------------------------

DERIVED_DIR = OUTPUT_DIR
FIGURE_DIR = OUTPUT_DIR
RESPONSE_CORRECTION_DIR = NB000_DIR


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def canonical_source_event_key(event_key: str) -> str:
    """Return the canonical identifier for a source-event key.

    This permits current notebooks to read archived CSV/JSON products that
    contain the former ``capsule_*`` identifiers without perpetuating those
    names in newly written products.
    """
    normalized = str(event_key).strip().lower()
    return LEGACY_SOURCE_EVENT_KEY_ALIASES.get(normalized, normalized)


def source_event_time(event_key: str) -> UTCDateTime:
    """Return an authoritative source time, accepting legacy identifiers."""
    canonical_key = canonical_source_event_key(event_key)
    try:
        return SOURCE_EVENT_TIMES[canonical_key]
    except KeyError as exc:
        raise KeyError(
            f"Unknown source event {event_key!r}; canonical key "
            f"{canonical_key!r}. Available keys: "
            f"{sorted(SOURCE_EVENT_TIMES)}"
        ) from exc

def find_project_root(start: str | Path | None = None) -> Path:
    """Find the repository root from a path inside the project."""
    if start is None:
        return PROJECT_ROOT

    current = Path(start).expanduser().resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "modules" / "project_config.py").is_file():
            return candidate

    raise FileNotFoundError(
        f"Could not locate the project root above {current}"
    )


def add_modules_to_path(
    project_root: str | Path = PROJECT_ROOT,
) -> Path:
    """Add the repository's modules directory to sys.path."""
    module_dir = Path(project_root).resolve() / "modules"
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
    return module_dir


def ensure_input_directories() -> dict[str, Path]:
    """Create the documented repository input directories if required."""
    paths = {
        "data": DATA_DIR,
        "metadata": METADATA_DIR,
        "miniseed": MINISEED_DIR,
        "legacy_export": LEGACY_EXPORT_DIR,
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def ensure_output_dirs() -> dict[str, Path]:
    """Create and return all standardized workflow output directories."""
    paths = {"outputs": OUTPUT_DIR}
    paths.update(
        {
            path.name.split("_", 1)[0]: path
            for path in NOTEBOOK_OUTPUT_DIRS
        }
    )
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def validate_required_inputs() -> None:
    """Raise a useful error when core repository inputs are unavailable."""
    required = {
        "StationXML file": STATIONXML_FILE,
        "launchpad/camera KML": KML_FILE,
    }

    missing = [
        f"{label}: {path}"
        for label, path in required.items()
        if not path.is_file()
    ]

    raw_available = RAW_MSEED.is_file()
    sds_available = SDS_DIR is not None and SDS_DIR.is_dir()
    if not raw_available and not sds_available:
        missing.append(
            "raw waveform input: "
            f"{RAW_MSEED} (or set external_paths.sds_dir in "
            f"{LOCAL_CONFIG_FILE})"
        )

    if missing:
        message = "\n".join(f"- {item}" for item in missing)
        raise FileNotFoundError(
            "Required Falcon 9 workflow inputs were not found:\n"
            f"{message}"
        )


# Notebooks can write their first products without repeating initialization.
ensure_output_dirs()
