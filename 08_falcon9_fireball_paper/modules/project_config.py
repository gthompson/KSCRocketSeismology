"""Shared configuration for the Falcon 9 seismo-acoustic workflow.

Repository layout::

    falcon9-seismoacoustic-workflow-1.0.0/
        modules/project_config.py
        notebooks/
        local_config.example.toml

External paper workspace (external_paths.paper_dir in local_config.toml)::

    PAPER_DIR/
        inputs/metadata/
        inputs/miniseed/
        inputs/videos/
        inputs/legacy_export/
        outputs/
        release/

All workflow data inputs and generated products reside in the external paper
workspace. Repository paths are derived from this file. Machine-specific paths
are read from the private local_config.toml; copy local_config.example.toml
and set paper_dir before importing this module.
"""

from __future__ import annotations

import sys
from functools import lru_cache
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 and earlier
from pathlib import Path

import pandas as pd
from obspy.core import UTCDateTime




def _load_local_config() -> dict:
    """Load optional machine-specific settings from the repository root."""
    if not LOCAL_CONFIG_FILE.is_file():
        return {}
    with LOCAL_CONFIG_FILE.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a TOML table in {LOCAL_CONFIG_FILE}")
    return payload

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


# -----------------------------------------------------------------------------
# Repository locations
# -----------------------------------------------------------------------------

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
LOCAL_CONFIG_FILE = PROJECT_ROOT / "local_config.toml"

LOCAL_CONFIG = _load_local_config()
PAPER_DIR = _optional_local_path("paper_dir")

if PAPER_DIR is None:
    raise RuntimeError(
        "Set external_paths.paper_dir in local_config.toml "
        "to the external paper workspace (inputs, outputs, and release)."
    )

INPUT_DIR = PAPER_DIR / "inputs"
METADATA_DIR = INPUT_DIR / "metadata"
MINISEED_DIR = INPUT_DIR / "miniseed"
VIDEO_DIR = INPUT_DIR / "videos"
LEGACY_EXPORT_DIR = INPUT_DIR / "legacy_export"
OUTPUT_DIR = PAPER_DIR / "outputs"
RELEASE_DIR = PAPER_DIR / "release"

# Optional fallback used by Notebook 000 only when RAW_MSEED is absent.
SDS_DIR = _optional_local_path("sds_dir")

# Public USLaunchReport source recording, stored with the external inputs.
# The copyrighted movie is not included in the repository deposit.
USLAUNCHREPORT_VIDEO_FILE = (
    VIDEO_DIR / "SpaceXStaticFireAnomalyAMOS_6_Youtube.mov"
)

# -----------------------------------------------------------------------------
# External paper-workspace input products
# -----------------------------------------------------------------------------

# Notebook 000 falls back to SDS_DIR only when this primary input is absent.
RAW_MSEED = MINISEED_DIR / "bchh_raw_event_window.mseed"

STATIONXML_FILE = METADATA_DIR / "KSC.xml"
CSS_CALIBRATION_FILE = METADATA_DIR / "sitedb.calibration"
KML_FILE = METADATA_DIR / "launchpads_cameras.kml"
BCHH_NAMED_EVENT_ARRIVAL_PICKS_FILE = (
    METADATA_DIR / "bchh_named_event_pressure_arrival_picks.csv"
)
UCS3_VIDEO_EVENT_FRAMES_FILE = METADATA_DIR / "ucs3_video_event_frames.csv"

# -----------------------------------------------------------------------------
# Standardized paper-workflow output locations
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
NB040_DIR = notebook_output_dir(40, "validate_event_catalogue_with_array_processing")
NB050_DIR = notebook_output_dir(50, "prepare_event_waveform_products")
NB060_DIR = notebook_output_dir(60, "analyze_planar_array_propagation")
NB070_DIR = notebook_output_dir(70, "measure_event_amplitudes_and_acoustic_seismic_coupling")
NB080_DIR = notebook_output_dir(80, "analyze_named_events_and_timing")
NB090_DIR = notebook_output_dir(90, "estimate_acoustic_energetics")
NB100_DIR = notebook_output_dir(100, "analyze_seismic_polarization")
NB110_DIR = notebook_output_dir(110, "search_for_direct_seismic_waves")
NB120_DIR = notebook_output_dir(120, "analyze_regional_detectability")
NB130_DIR = notebook_output_dir(130, "generate_supplement_event_table")
NB140_DIR = notebook_output_dir(140, "generate_publication_figures")
NB150_DIR = notebook_output_dir(150, "assemble_zenodo_release")

NOTEBOOK_OUTPUT_DIRS = (
    NB000_DIR, NB010_DIR, NB020_DIR, NB030_DIR, NB040_DIR, NB050_DIR, NB060_DIR,
    NB070_DIR, NB080_DIR, NB090_DIR, NB100_DIR, NB110_DIR, NB120_DIR, NB130_DIR,
    NB140_DIR, NB150_DIR,
)

# -----------------------------------------------------------------------------
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
# Reviewed BCHH receiver arrival picks
# -----------------------------------------------------------------------------

def _load_bchh_named_event_arrival_picks() -> pd.DataFrame:
    """Load reviewed DD2/DD3 pressure arrival picks for the named events.

    These are receiver arrival measurements at BCHH. They are intentionally
    distinct from ``SOURCE_EVENT_TIMES``, which are source-time coordinates
    obtained by reducing BCHH arrivals with the adopted 351 m/s propagation
    velocity.
    """
    path = BCHH_NAMED_EVENT_ARRIVAL_PICKS_FILE
    if not path.is_file():
        raise FileNotFoundError(
            "Required BCHH named-event arrival-pick file was not found: "
            f"{path}"
        )

    df = pd.read_csv(path, dtype=str)
    required_columns = {
        "event",
        "trace_id",
        "sensor_kind",
        "pick_time_utc",
    }
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(
            f"{path} is missing required columns: {sorted(missing)}"
        )

    df = df.loc[:, [
        "event",
        "trace_id",
        "sensor_kind",
        "pick_time_utc",
    ]].copy()

    if df.duplicated(["event", "trace_id"]).any():
        duplicates = df.loc[
            df.duplicated(["event", "trace_id"], keep=False),
            ["event", "trace_id"],
        ]
        raise ValueError(
            "Duplicate BCHH arrival picks found for event/trace pairs:\n"
            f"{duplicates.to_string(index=False)}"
        )

    df["channel"] = df["trace_id"].str.rsplit(".", n=1).str[-1]
    df["pick_time"] = df["pick_time_utc"].map(UTCDateTime)
    return df


@lru_cache(maxsize=1)
def get_bchh_named_event_arrival_picks() -> pd.DataFrame:
    """Load and cache reviewed picks only when a timing consumer requests them."""
    return _load_bchh_named_event_arrival_picks()


@lru_cache(maxsize=1)
def get_bchh_pressure_arrival_picks() -> dict:
    """Return the reviewed picks indexed by event and channel, loaded on demand."""
    return {
        event_id: {row.channel: row.pick_time for row in group.itertuples(index=False)}
        for event_id, group in get_bchh_named_event_arrival_picks().groupby(
            "event", sort=False
        )
    }


# -----------------------------------------------------------------------------
# Same-camera UCS-3 video timing observations
# -----------------------------------------------------------------------------

def _load_ucs3_video_event_frames() -> pd.DataFrame:
    """Load manually reviewed event frames from the SpaceX UCS-3 camera near BCHH/Astronaut Beach House.

    Absolute synchronization of this camera to BCHH is not assumed. Quantitative
    use is restricted to event-to-event intervals measured within this camera.
    The burned-in timecode advances at 30 fps while the video contains two
    60-fps images for each displayed timecode frame.
    """
    path = UCS3_VIDEO_EVENT_FRAMES_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Required UCS-3 timing file was not found: {path}")
    df = pd.read_csv(path)
    required = {"event", "estimate", "timecode_hms", "timecode_frame_30fps",
                "member_60fps", "included_in_analysis", "timing_role"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    if not df["member_60fps"].isin([1, 2]).all():
        raise ValueError("member_60fps must be 1 or 2")
    if not df["timecode_frame_30fps"].between(0, 29).all():
        raise ValueError("timecode_frame_30fps must be 0..29")
    return df


def ucs3_frame_clock_seconds(timecode_hms: str, frame_30fps: int, member_60fps: int) -> float:
    """Camera-clock seconds for one decoded 60-fps image.

    Only differences between values from this same camera are scientifically
    meaningful; the camera clock is not assumed synchronized to BCHH.
    """
    hh, mm, ss = (int(x) for x in str(timecode_hms).split(":"))
    if not 0 <= int(frame_30fps) <= 29:
        raise ValueError("frame_30fps must be 0..29")
    if int(member_60fps) not in (1, 2):
        raise ValueError("member_60fps must be 1 or 2")
    return (hh * 3600.0 + mm * 60.0 + ss
            + int(frame_30fps) / 30.0 + (int(member_60fps) - 1) / 60.0)


@lru_cache(maxsize=1)
def get_ucs3_video_event_frames() -> pd.DataFrame:
    """Load, validate and cache UCS-3 frames only when requested."""
    frames = _load_ucs3_video_event_frames()
    frames["camera_clock_s"] = [
        ucs3_frame_clock_seconds(r.timecode_hms, r.timecode_frame_30fps, r.member_60fps)
        for r in frames.itertuples(index=False)
    ]
    return frames


def clear_timing_data_cache() -> None:
    """Call after editing timing CSVs during an existing notebook session."""
    get_bchh_pressure_arrival_picks.cache_clear()
    get_bchh_named_event_arrival_picks.cache_clear()
    get_ucs3_video_event_frames.cache_clear()


def __getattr__(name: str):
    """Keep existing config.DATAFRAME access compatible without eager CSV reads."""
    loaders = {
        "BCHH_NAMED_EVENT_ARRIVAL_PICKS": get_bchh_named_event_arrival_picks,
        "BCHH_PRESSURE_ARRIVAL_PICKS": get_bchh_pressure_arrival_picks,
        "UCS3_VIDEO_EVENT_FRAMES": get_ucs3_video_event_frames,
    }
    if name in loaders:
        return loaders[name]()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def ucs3_video_interval_s(event_key: str, estimate: str = "preferred",
                            reference_event: str = "upper_stage",
                            reference_estimate: str = "preferred") -> float:
    """Return a same-camera relative event interval in seconds."""
    event_key = canonical_source_event_key(event_key) if "canonical_source_event_key" in globals() else str(event_key)
    reference_event = canonical_source_event_key(reference_event) if "canonical_source_event_key" in globals() else str(reference_event)
    frames = get_ucs3_video_event_frames()
    def one(event, est):
        rows = frames.loc[
            frames["event"].eq(event)
            & frames["estimate"].eq(est)
        ]
        if len(rows) != 1:
            raise KeyError(f"Expected one UCS-3 row for event={event!r}, estimate={est!r}; found {len(rows)}")
        return float(rows.iloc[0]["camera_clock_s"])
    return one(event_key, estimate) - one(reference_event, reference_estimate)


# -----------------------------------------------------------------------------
# Legacy/model-derived event coordinates and display timing
# -----------------------------------------------------------------------------

# LEGACY/MODEL-DERIVED source-time coordinate. These times were inferred by
# reducing reviewed BCHH pressure arrivals with the meteorologically predicted
# 351 m/s source-to-array velocity. They are NOT independent source-time picks
# and must not be used to test propagation speed against the same BCHH arrivals.
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

# Legacy USLaunchReport visualization alignment only.
#
# These values are retained for figures that align the public recording to
# the waveform display. They are not the independent public-video PTS picks
# used for the differential propagation analysis.
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
    """Return a legacy/model-derived source-time coordinate, accepting legacy identifiers."""
    canonical_key = canonical_source_event_key(event_key)
    try:
        return SOURCE_EVENT_TIMES[canonical_key]
    except KeyError as exc:
        raise KeyError(
            f"Unknown source event {event_key!r}; canonical key "
            f"{canonical_key!r}. Available keys: "
            f"{sorted(SOURCE_EVENT_TIMES)}"
        ) from exc


def bchh_pressure_arrival_time(
    event_key: str,
    channel: str,
) -> UTCDateTime:
    """Return a reviewed BCHH DD2/DD3 pressure arrival time."""
    canonical_key = canonical_source_event_key(event_key)
    channel = str(channel).strip().upper()
    try:
        return get_bchh_pressure_arrival_picks()[canonical_key][channel]
    except KeyError as exc:
        raise KeyError(
            f"No BCHH pressure arrival pick for event={canonical_key!r}, "
            f"channel={channel!r}"
        ) from exc


def bchh_pressure_interval_s(
    event0: str,
    event1: str,
    channel: str,
) -> float:
    """Return the same-channel BCHH pressure arrival interval in seconds."""
    return float(
        bchh_pressure_arrival_time(event1, channel)
        - bchh_pressure_arrival_time(event0, channel)
    )


def bchh_median_pressure_interval_s(
    event0: str,
    event1: str,
    channels: tuple[str, ...] = ("DD2", "DD3"),
) -> float:
    """Return the median same-channel BCHH pressure interval."""
    values = [
        bchh_pressure_interval_s(event0, event1, channel)
        for channel in channels
    ]
    return float(pd.Series(values, dtype=float).median())


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
    """Create the documented external paper-workspace input directories if required."""
    paths = {
        "inputs": INPUT_DIR,
        "metadata": METADATA_DIR,
        "miniseed": MINISEED_DIR,
        "videos": VIDEO_DIR,
        "legacy_export": LEGACY_EXPORT_DIR,
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def ensure_output_dirs() -> dict[str, Path]:
    """Create and return all standardized workflow output directories."""
    paths = {"paper": PAPER_DIR, "outputs": OUTPUT_DIR, "release": RELEASE_DIR}
    paths.update(
        {
            path.name.split("_", 1)[0]: path
            for path in NOTEBOOK_OUTPUT_DIRS
        }
    )
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def validate_required_inputs(*, include_timing: bool = False) -> None:
    """Validate core files; opt in to timing CSV checks with include_timing=True."""
    required = {
        "StationXML file": STATIONXML_FILE,
        "launchpad/camera KML": KML_FILE,
    }
    if include_timing:
        required.update({
            "BCHH named-event pressure arrival picks": BCHH_NAMED_EVENT_ARRIVAL_PICKS_FILE,
            "UCS-3 same-camera video event frames": UCS3_VIDEO_EVENT_FRAMES_FILE,
        })

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
