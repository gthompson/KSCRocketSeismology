"""Artemis II configuration for the notebooks in this folder.

A thin wrapper over the shared `ksclib` package: all event-specific settings live in
artemis2.yaml (edit that, not the notebooks, when a drive or folder moves), and the
code lives in ksclib and flovopy. This module keeps the names the notebooks use
(cfg.LAUNCHTIME, cfg.instrument_correct, ...).
"""
from __future__ import annotations

from pathlib import Path

from obspy import Stream

import ksclib
from ksclib import data as _data
from ksclib.seedcodes import alias_patterns, normalize_stream, same_code
from flovopy.ingest import gem_overflow as _gem

PAPER_DIR = Path(__file__).resolve().parent
REPO_ROOT = PAPER_DIR.parent
EVENT = ksclib.load_event(PAPER_DIR / "artemis2.yaml")

# ---------------------------------------------------------------------------
# Archive, service run and paths
# ---------------------------------------------------------------------------
PROJECT_YAML = EVENT.project_yaml
INGEST_CONFIG_DIR = PROJECT_YAML.parent
INGEST_DIR = INGEST_CONFIG_DIR.parent
PROJECT = EVENT.project
PROJECT_ROOT = EVENT.project_root
MASTER_SDS = EVENT.master_sds
RUN_ID = EVENT.run_id
RUN_DIR = EVENT.run_dir
GEM_MAPPING_CSV = EVENT.paths["gem_mapping_csv"]
SMARTSOLO_MAPPING_CSV = EVENT.paths["smartsolo_mapping_csv"]
EVENT_WAV_DIR = EVENT.paths["event_wav_dir"]
QC_DIR = EVENT.paths["qc_dir"]
GEM_CONVERT_DIR = EVENT.paths["gem_convert_dir"]
GEM_GPS_DIR = GEM_CONVERT_DIR / "gps"
GURALP_INVENTORIES = {"B07": EVENT.paths["guralp_B07"], "B12": EVENT.paths["guralp_B12"]}
OUT_DIR = EVENT.out_dir
STATION_XLS = EVENT.station_file
BOX_WRITING = STATION_XLS.parent
STATION_MAP_MODULE_DIR = REPO_ROOT / "07_ensemble_paper"
ROCKET_MODEL_DIR = REPO_ROOT / "rocket_infrasound_model"

# ---------------------------------------------------------------------------
# Launch window
# ---------------------------------------------------------------------------
LAUNCHTIME = EVENT.origin_time
DURATION = EVENT.duration
PRETRIGGER = EVENT.pretrigger
POSTTRIGGER = EVENT.posttrigger
STARTTIME = EVENT.starttime
ENDTIME = EVENT.endtime
STARTTRIM = EVENT.starttrim
ENDTRIM = EVENT.endtrim
CHANNEL_GROUPS = EVENT.channel_groups
PAD = EVENT.site_name
LAUNCH_AZIMUTH_DEG = EVENT.launch_azimuth_deg

# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
CENTAUR_RESPONSE_DIRS = EVENT.centaur_response_dirs
INFRABSU_XML = EVENT.infrabsu_xml
INFRABSU_CHANNELS = EVENT.infrabsu_channels
RESTORED_SDS = EVENT.restored["1R.B29.00.DHZ"]
SMARTSOLO_GEOPHONE = EVENT.smartsolo_geophone

# ---------------------------------------------------------------------------
# Functions (bound to this event)
# ---------------------------------------------------------------------------
SKIPPED_FILES = _data.SKIPPED_FILES


def sds_client(sds_root=MASTER_SDS):
    return ksclib.sds_client(sds_root)


def centaur_response_file(station, when=LAUNCHTIME):
    return ksclib.centaur_response_file(EVENT, station, when)


def centaur_inventory(station, when=LAUNCHTIME):
    return ksclib.centaur_inventory(EVENT, station, when)


def read_restored(seed_id, starttime=STARTTIME, endtime=ENDTIME):
    return ksclib.read_restored(EVENT, seed_id, starttime, endtime)


def get_group_stream(group, client=None, starttime=STARTTIME, endtime=ENDTIME):
    return ksclib.get_group_stream(EVENT, group, client, starttime, endtime)


def get_launch_stream(client=None, groups=None, starttime=STARTTIME, endtime=ENDTIME):
    return ksclib.get_event_stream(EVENT, client, groups, starttime, endtime)


def launch_stream_raw(client=None):
    """Raw launch-window stream for USF, BSU and SmartSolo groups, with restored B29 CHZ."""
    return ksclib.event_stream_raw(EVENT, client)


def read_channel(seed_id, starttime=STARTTIME, endtime=ENDTIME, client=None):
    """One channel by SEED id (e.g. 1R.B01.00.CD0), whichever spelling the archive uses.

    Centaur channels are read as D?? or C??/H?? (the SDS is being renamed to SEED band codes)
    and returned under the SEED code. A channel with a restored copy in artemis2.yaml
    (1R.B29.00.CHZ, zero-filled in the SDS on days 082-093) is read from that copy.
    """
    net, sta, loc, cha = seed_id.split(".")
    for rid in EVENT.restored:
        r_net, r_sta, r_loc, r_cha = rid.split(".")
        if (r_net, r_sta, r_loc) == (net, sta, loc) and same_code(r_cha, cha):
            st = ksclib.read_restored(EVENT, rid, starttime, endtime)
            if st:
                return st
    client = client or sds_client()
    centaur = loc == "00" and len(cha) == 3 and cha[0] in "CDH" and cha[1] in "DH"
    st = Stream()
    for l, c in alias_patterns(loc, "D" + cha[1:] if centaur else cha):
        if l in ("", "--"):     # Gem/SmartSolo files use location "--"; the client matches it only as "*"
            st += Stream([tr for tr in client.get_waveforms(net, sta, "*", c, starttime, endtime)
                          if tr.stats.location in ("", "--")])
        else:
            st += client.get_waveforms(net, sta, l, c, starttime, endtime)
    return normalize_stream(st) if EVENT.seed_band_codes else st


def station_table(pad=PAD):
    if pad != PAD:
        raise ValueError(f"This configuration is centred on {PAD}")
    return ksclib.station_table(EVENT)


def smartsolo_paz():
    return ksclib.smartsolo_paz(EVENT)


def instrument_correct(st, pre_filt_low=(0.01, 0.02)):
    return ksclib.instrument_correct(st, EVENT, pre_filt_low)


def source_geometry(station, ts=None, c=343.0, az=None):
    return ksclib.source_geometry(EVENT, station, ts=ts, c=c, az=az)


# Gem 16-bit overflow (flovopy.ingest.gem_overflow)
GEM_JUMP_COUNTS = _gem.JUMP_COUNTS
GEM_STEP_COUNTS = _gem.STEP_COUNTS
gem_jump_clusters = _gem.gem_jump_clusters
gem_clip_intervals = _gem.gem_clip_intervals
stream_clip_intervals = _gem.stream_clip_intervals
clip_mask = _gem.clip_mask
repair_gem_overflow = _gem.repair_gem_overflow
