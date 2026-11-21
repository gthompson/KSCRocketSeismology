"""Shared paths and launch parameters for the Artemis II notebooks (05, 25, 35).

Waveforms come from the master SDS archive defined in the KSC flovopy.ingest
project file (2026_ingest_service_runs/config/ksc.yaml). Paper products
(CSVs, figures, corrected streams) go to the Box writing/Artemis2 folder.
Edit this file, not the notebooks, when a drive or folder moves.
"""
from __future__ import annotations

import os
from pathlib import Path

from obspy import Stream, UTCDateTime

from flovopy.ingest.config import load_project, master_sds, run_dir

# ---------------------------------------------------------------------------
# Repository and flovopy.ingest project
# ---------------------------------------------------------------------------
PAPER_DIR = Path(__file__).resolve().parent
REPO_ROOT = PAPER_DIR.parent
INGEST_DIR = REPO_ROOT / "2026_ingest_service_runs"
INGEST_CONFIG_DIR = INGEST_DIR / "config"
PROJECT_YAML = INGEST_CONFIG_DIR / "ksc.yaml"

# Service run that recovered the Artemis II launch data (first field day 2026-04-03).
RUN_ID = "20260403_service"

# Campaign-specific serial -> SEED ID tables used by flovopy.ingest.
GEM_MAPPING_CSV = INGEST_CONFIG_DIR / "gem_mapping_artemis2_example.csv"
SMARTSOLO_MAPPING_CSV = INGEST_CONFIG_DIR / "smartsolo_mapping_artemis2.csv"

PROJECT = load_project(PROJECT_YAML)
PROJECT_ROOT = PROJECT["_root"]          # e.g. /Volumes/KSCGTdownld
MASTER_SDS = master_sds(PROJECT)         # e.g. /Volumes/KSCGTdownld/SDS
RUN_DIR = run_dir(PROJECT, RUN_ID)       # e.g. /Volumes/KSCGTdownld/20260403_service

# Seisan-style event WAV files cut from the master SDS.
EVENT_WAV_DIR = PROJECT_ROOT / "30_eventwav"

# ---------------------------------------------------------------------------
# Paper inputs/outputs (Box)
# ---------------------------------------------------------------------------
BOX_WRITING = (Path("~").expanduser() / "Library" / "CloudStorage" / "Box-Box"
               / "thompsong" / "3_Project_Documents" / "NASAprojects"
               / "201602_Rocket_Seismology" / "writing")
# Set ARTEMIS2_OUT_DIR to send products elsewhere (e.g. a test run).
OUT_DIR = Path(os.environ.get("ARTEMIS2_OUT_DIR", BOX_WRITING / "Artemis2")).expanduser()
STATION_XLS = BOX_WRITING / "KSC_seismic_network_2016_2022.xls"

# Shared plotting helpers (plot_station_map_tiles, save_figures).
STATION_MAP_MODULE_DIR = REPO_ROOT / "07_ensemble_paper"
# Forward model package.
ROCKET_MODEL_DIR = REPO_ROOT / "rocket_infrasound_model"

# ---------------------------------------------------------------------------
# Launch window
# ---------------------------------------------------------------------------
LAUNCHTIME = UTCDateTime("2026-04-01T22:35:12")
DURATION = 900            # s of launch signal of interest
PRETRIGGER = 1800         # s before launch
POSTTRIGGER = PRETRIGGER  # s after LAUNCHTIME + DURATION
STARTTIME = LAUNCHTIME - PRETRIGGER
ENDTIME = LAUNCHTIME + DURATION + POSTTRIGGER
STARTTRIM = LAUNCHTIME - 30     # plotting / amplitude window
ENDTRIM = LAUNCHTIME + 270

# ---------------------------------------------------------------------------
# Channel groups in the master SDS
# ---------------------------------------------------------------------------
# name: (network, station, location, channel)
CHANNEL_GROUPS = {
    "USF": ("1R", "*", "*", "D[DH]?"),        # Centaur: Trillium DH?, infraBSU/Chaparral DD?
    "BSU": ("1R", "*", "*", "HD?"),           # Gem infrasound loggers HDF/HDI
    "SmartSolo": ("1R", "*", "*", "DP?"),     # SmartSolo geophones
    "MSFC": ("DG", "*", "*", "C*"),           # Guralp and Silicon Audio (MSFC)
}


def sds_client(sds_root=MASTER_SDS):
    """EnhancedSDSClient on the master SDS archive."""
    from flovopy.enhanced.sdsclient import EnhancedSDSClient
    root = Path(sds_root)
    if not root.is_dir():
        raise FileNotFoundError(f"Master SDS not found (is the drive mounted?): {root}")
    return EnhancedSDSClient(str(root))


SKIPPED_FILES = []   # unreadable SDS files met by get_group_stream (path, error)


def _read_sds_files(net, sta, loc, cha, starttime, endtime, sds_root=MASTER_SDS):
    """Read matching SDS day files one by one, skipping (and recording) unreadable ones."""
    import warnings
    from obspy import read
    st = Stream()
    day = UTCDateTime(starttime.date)
    while day <= endtime:
        pattern = f"{day.year}/{net}/{sta}/{cha}.D/{net}.{sta}.{loc}.{cha}.D.{day.year}.{day.julday:03d}"
        for path in sorted(Path(sds_root).glob(pattern)):
            try:
                st += read(str(path), format="MSEED", starttime=starttime, endtime=endtime)
            except Exception as exc:
                SKIPPED_FILES.append((str(path), f"{type(exc).__name__}: {exc}"))
                warnings.warn(f"SKIPPED unreadable SDS file {path} ({type(exc).__name__})")
        day += 86400
    return st


def get_group_stream(group, client=None, starttime=STARTTIME, endtime=ENDTIME):
    """Waveforms for one CHANNEL_GROUPS entry from the master SDS.

    If any file in the group is unreadable, the group is re-read file by file and the
    bad files are skipped with a warning and listed in SKIPPED_FILES.
    """
    client = client or sds_client()
    net, sta, loc, cha = CHANNEL_GROUPS[group]
    try:
        return client.get_waveforms(network=net, station=sta, location=loc, channel=cha,
                                    starttime=starttime, endtime=endtime)
    except Exception:
        return _read_sds_files(net, sta, loc, cha, starttime, endtime)


def get_launch_stream(client=None, groups=None, starttime=STARTTIME, endtime=ENDTIME):
    """All launch-window waveforms (every CHANNEL_GROUPS entry), merged."""
    client = client or sds_client()
    st = Stream()
    for group in groups or CHANNEL_GROUPS:
        st += get_group_stream(group, client, starttime, endtime)
    st.merge()
    return st
