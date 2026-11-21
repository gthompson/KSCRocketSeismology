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
# Per-run QC products (Gem GPS coordinates, restored channels, ...).
QC_DIR = RUN_DIR / "30_qc"
# gemconvert outputs for this run.
GEM_CONVERT_DIR = RUN_DIR / "10_gemconvert"
GEM_GPS_DIR = GEM_CONVERT_DIR / "gps"

# Guralp Certimus responses (MSFC). B07: dataless SEED downloaded with its data;
# B12: StationXML exported from the digitizer during the 20260310 service run.
GURALP_INVENTORIES = {
    "B07": RUN_DIR / "00_download" / "Guralp" / "B07" / "DG_B07.dataless",
    "B12": PROJECT_ROOT / "20260310_service" / "00_download" / "Guralp" / "Sensor1.xml",
}

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


# ---------------------------------------------------------------------------
# Instrument responses
# ---------------------------------------------------------------------------
# Centaur digitizers write 1R.<STA>_<YYYYMMDDTHHMMSS>Z.xml whenever their
# configuration changes. They hold the full Trillium Compact response (DH?) but
# only the digitizer for the infrasound inputs (DD?, volts in). Trilliums are on
# Sensor A at the 40 Vpp input range ("Analog 1.0 gain" stage, 400,000 counts/V);
# infrasound sensors are on Sensor B at 1 Vpp ("Analog 40.0 gain", 1.6e7 counts/V).
CENTAUR_RESPONSE_DIRS = [
    RUN_DIR / "00_download" / "Centaur0" / "responses",
    Path("/Volumes/haldata/KSC/20260310_service/responses"),
    Path("/Volumes/haldata/KSC/20260605_service/responses"),
]
# infraBSU 0.5-inch sensor stage (46 uV/Pa, single 0.048 Hz high-pass pole).
INFRABSU_XML = Path("/Volumes/haldata/KSC/station_metadata/infraBSU_21s_0.5inch.xml")
# Channels at the Centaur infrasound inputs that carry an infraBSU sensor.
INFRABSU_CHANNELS = ("DD0", "DD1", "DD2")
# Station B29's DHZ for days 082-093 is zero-filled in the SDS; the launch window
# was recovered (exact counts) by restore_B29_DHZ.py into this SDS-style folder.
RESTORED_SDS = RUN_DIR / "30_qc" / "B29_DHZ_restored" / "SDS"
# SmartSolo IGU-16HR-3C: harvested MiniSEED is geophone output in mV. Nominal
# geophone: 5 Hz natural frequency, damping 0.7, 76.7 V/(m/s) (EPIC spec sheet).
SMARTSOLO_GEOPHONE = dict(f0=5.0, damping=0.7, sensitivity_mV_per_mps=76.7e3)


def centaur_response_file(station, when=LAUNCHTIME):
    """Latest Centaur response XML for a station written at or before `when`."""
    import re
    best = None
    for d in CENTAUR_RESPONSE_DIRS:
        for p in Path(d).glob(f"1R.{station}_*Z.xml"):
            m = re.match(rf"1R\.{station}_(\d{{8}}T\d{{6}})Z\.xml$", p.name)
            if not m:
                continue
            t = UTCDateTime(m.group(1))
            if t <= when and (best is None or t > best[0]):
                best = (t, p)
    if best is None:
        raise FileNotFoundError(f"No Centaur response for {station} before {when}")
    return best[1]


def centaur_inventory(station, when=LAUNCHTIME):
    """Centaur response inventory, with the infraBSU stage prepended on DD0-DD2.

    The result converts DH? counts to m/s and infraBSU DD? counts to Pa
    (overall ~736 counts/Pa at the 1 Vpp setting).
    """
    import copy
    from obspy import read_inventory
    inv = read_inventory(str(centaur_response_file(station, when)))
    sensor = read_inventory(str(INFRABSU_XML))[0][0][0].response.response_stages[0]
    for net in inv:
        for sta in net:
            for cha in sta:
                if cha.code not in INFRABSU_CHANNELS:
                    continue
                resp = cha.response
                stage = copy.deepcopy(sensor)
                resp.response_stages.insert(0, stage)
                for i, s in enumerate(resp.response_stages, 1):
                    s.stage_sequence_number = i
                resp.response_stages[1].input_units = "V"
                resp.instrument_sensitivity.input_units = "Pa"
                resp.instrument_sensitivity.value *= stage.stage_gain
                resp.recalculate_overall_sensitivity(1.0)
    return inv


def read_restored(seed_id, starttime=STARTTIME, endtime=ENDTIME):
    """Read a channel from the restored-data SDS folder (e.g. 1R.B29.00.DHZ)."""
    from obspy.clients.filesystem.sds import Client
    net, sta, loc, cha = seed_id.split(".")
    return Client(str(RESTORED_SDS)).get_waveforms(net, sta, loc, cha, starttime, endtime)


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


# ---------------------------------------------------------------------------
# Station geometry
# ---------------------------------------------------------------------------
PAD = "LC39B"
# Launch azimuth (degrees clockwise from north) used to place the 2-D forward
# model on the map. Not yet confirmed for Artemis II; notebook 40 tests it.
LAUNCH_AZIMUTH_DEG = 90.0


def station_table(pad=PAD):
    """Station coordinates with east/north offsets (m), distance (km) and azimuth (deg) from the pad."""
    import numpy as np
    import pandas as pd
    from obspy.geodetics import gps2dist_azimuth
    sta = pd.read_excel(STATION_XLS, sheet_name="artemis2")
    pads = pd.read_excel(STATION_XLS, sheet_name="launchpads_2026").set_index("pad")
    plat, plon = pads.loc[pad, ["lat", "lon"]]
    rows = []
    for _, r in sta.iterrows():
        d, az, _ = gps2dist_azimuth(plat, plon, r.lat, r.lon)
        rows.append(dict(station=r.station, lat=r.lat, lon=r.lon, distance_km=d / 1000, azimuth_deg=az,
                         east_m=d * np.sin(np.radians(az)), north_m=d * np.cos(np.radians(az))))
    return pd.DataFrame(rows).set_index("station")


# ---------------------------------------------------------------------------
# Gem 16-bit overflow
# ---------------------------------------------------------------------------
# Near the pad the launch exceeded the Gem's 16-bit range (onset ~100-140 Pa at
# high gain, measured at B01 against the co-located infraBSU). While overflowing,
# consecutive raw samples jump by >20000 counts and the baseline walks off by
# 6.6e4 to 2e6 counts, a step that persists afterwards. Outside those intervals
# the corrected Gem waveform matches the infraBSU (cc ~0.99), so only the
# overflow interval is lost. Steep crackle shock fronts (e.g. -71 to +122 Pa in
# 4 ms at B29, 5.6 km) also make >20000-count one-sample jumps but leave no
# baseline step; they are classified as "shock" and NOT masked.
GEM_JUMP_COUNTS = 20000
GEM_STEP_COUNTS = 32768       # persistent baseline step that marks a real overflow


def gem_jump_clusters(tr_raw, jump=GEM_JUMP_COUNTS, gap_s=2.0, pad_s=0.25, side_s=3.0):
    """All clusters of large one-sample jumps in a raw-count Gem trace, classified.

    Returns a list of dicts: t0, t1 (UTCDateTime), n_jumps, step (median after minus
    median before, counts) and kind: "overflow" (several jumps, persistent step),
    "reset" (single jump, persistent step: a baseline jump) or "shock" (no step).
    """
    import numpy as np
    d = tr_raw.data.astype(np.int64)
    k = np.flatnonzero(np.abs(np.diff(d)) > jump)
    if not len(k):
        return []
    dt, t0 = tr_raw.stats.delta, tr_raw.stats.starttime
    groups, start, prev = [], k[0], k[0]
    for x in k[1:]:
        if (x - prev) * dt > gap_s:
            groups.append((start, prev)); start = x
        prev = x
    groups.append((start, prev))
    out = []
    for a, b in groups:
        ta, tb = t0 + a * dt - pad_s, t0 + (b + 1) * dt + pad_s
        pre, post = tr_raw.slice(ta - side_s, ta).data, tr_raw.slice(tb, tb + side_s).data
        step = float(np.median(post) - np.median(pre)) if len(pre) and len(post) else np.nan
        n = int(((k >= a) & (k <= b)).sum())
        big = abs(step) > GEM_STEP_COUNTS
        kind = "shock" if not big else ("overflow" if n > 1 else "reset")
        out.append(dict(t0=ta, t1=tb, n_jumps=n, step=step, kind=kind))
    return out


def gem_clip_intervals(tr_raw, kinds=("overflow", "reset")):
    """Intervals [(t0, t1), ...] to mask in a raw-count Gem trace (overflow and baseline resets)."""
    return [(c["t0"], c["t1"]) for c in gem_jump_clusters(tr_raw) if c["kind"] in kinds]


def repair_gem_overflow(tr_raw, side_s=3.0):
    """Copy of a raw Gem trace with each overflow/reset interval bridged and its baseline step removed.

    The persistent step left by an overflow otherwise leaks through the 0.05 Hz
    high-pass of the Gem correction as a slow swing lasting tens of seconds
    (+170/-50 Pa at B01). Samples inside the interval are replaced by a straight
    line and must still be masked (they carry no signal); samples after it are
    shifted by -step.
    """
    import numpy as np
    t = tr_raw.copy()
    t.data = t.data.astype(np.float64)
    t0, dt = t.stats.starttime, t.stats.delta
    for c in gem_jump_clusters(tr_raw):
        if c["kind"] == "shock":
            continue
        i0 = max(int(round((c["t0"] - t0) / dt)), 1)
        i1 = min(int(round((c["t1"] - t0) / dt)), t.stats.npts - 1)
        pre = np.median(t.data[max(i0 - int(side_s / dt), 0):i0])
        post = np.median(t.data[i1:i1 + int(side_s / dt)])
        t.data[i1:] -= post - pre
        t.data[i0:i1] = np.linspace(t.data[i0 - 1], t.data[i1], i1 - i0, endpoint=False)
    return t


def stream_clip_intervals(st_raw):
    """{seed_id: [(t0, t1), ...]} for every Gem (HD?) trace in a raw-count stream."""
    return {tr.id: gem_clip_intervals(tr) for tr in st_raw if tr.stats.channel.startswith("HD")}


def clip_mask(tr, intervals):
    """Boolean array, True where the trace's samples fall inside any clipped interval."""
    import numpy as np
    t = tr.stats.starttime.timestamp + tr.times()
    m = np.zeros(tr.stats.npts, bool)
    for a, b in intervals:
        m |= (t >= a.timestamp) & (t <= b.timestamp)
    return m


# ---------------------------------------------------------------------------
# Instrument correction (shared by notebooks 20-60)
# ---------------------------------------------------------------------------
def smartsolo_paz():
    """Nominal SmartSolo geophone PAZ (velocity in m/s -> mV)."""
    import numpy as np
    g = SMARTSOLO_GEOPHONE
    w0 = 2 * np.pi * g["f0"]
    poles = list(np.roots([1, 2 * g["damping"] * w0, w0 ** 2]))
    return {"poles": poles, "zeros": [0j, 0j], "gain": 1.0, "sensitivity": g["sensitivity_mV_per_mps"]}


def instrument_correct(st, pre_filt_low=(0.01, 0.02)):
    """Copy of `st` in physical units: DH? m/s, DD0-2 Pa (Centaur), HD? Pa (Gem), DP? m/s (SmartSolo).

    Channels without a usable response (MSFC DG, B20 DDF, ...) are dropped.
    `pre_filt_low` sets the two low corners of the Centaur pre-filter.
    """
    import gemlog
    out = Stream()
    inventories = {}
    for tr in st:
        t = tr.copy()
        cha, sta = t.stats.channel, t.stats.station
        nyq = 0.5 * t.stats.sampling_rate
        try:
            if t.stats.network == "1R" and (cha.startswith("DH") or cha in INFRABSU_CHANNELS):
                inv = inventories.setdefault(sta, centaur_inventory(sta))
                t.detrend("linear")
                t.remove_response(inventory=inv, output="VEL" if cha.startswith("DH") else "DEF",
                                  pre_filt=(*pre_filt_low, 0.94 * nyq, 0.98 * nyq),
                                  zero_mean=True, taper=True)
            elif cha.startswith("HD"):
                t = repair_gem_overflow(t)       # clipped intervals must still be masked
                t.detrend("demean")
                t.filter("highpass", freq=0.05)
                t = gemlog.deconvolve_gem_response(t, gain="high")
            elif cha.startswith("DP"):
                t.detrend("linear")
                t.simulate(paz_remove=smartsolo_paz(), paz_simulate=None, remove_sensitivity=True,
                           pre_filt=(0.5, 1.0, 0.8 * nyq, 0.9 * nyq), taper=True)
            else:
                continue
        except Exception as exc:          # e.g. no Centaur response for a station
            import warnings
            warnings.warn(f"{tr.id}: not corrected ({type(exc).__name__}: {exc})")
            continue
        out.append(t)
    return out


def launch_stream_raw(client=None):
    """Raw launch-window stream for USF, BSU and SmartSolo groups, with restored B29 DHZ."""
    st = get_launch_stream(client, groups=("USF", "BSU", "SmartSolo"))
    if not st.select(id="1R.B29.00.DHZ"):
        st += read_restored("1R.B29.00.DHZ")
        st.merge()
    return st


# ---------------------------------------------------------------------------
# Moving-source geometry (forward model of notebook 35, placed on the map)
# ---------------------------------------------------------------------------
def source_geometry(station, ts=None, c=343.0, az=None):
    """Per source time t_s: source position, distance, arrival time, emission angle, ray elevation.

    Uses the nominal gravity-turn trajectory along `az` (default LAUNCH_AZIMUTH_DEG),
    straight rays at sound speed `c`, t_s = 0 at LAUNCHTIME.
    """
    import sys
    import numpy as np
    import pandas as pd
    if str(ROCKET_MODEL_DIR) not in sys.path:
        sys.path.append(str(ROCKET_MODEL_DIR))
    from rocket_infrasound_model.trajectory import GravityTurnParameters, gravity_turn_trajectory
    az = LAUNCH_AZIMUTH_DEG if az is None else az
    ts = np.arange(0.0, 200.0 + 1e-9, 0.1) if ts is None else np.asarray(ts, float)
    tt = np.arange(0.0, ts.max() + 0.2, 0.1)
    s = gravity_turn_trajectory(tt, GravityTurnParameters())
    g = {k: np.interp(ts, tt, s[k]) for k in ("x_m", "z_m", "vx_mps", "vz_mps", "speed_mps", "mach")}
    sa, ca = np.sin(np.radians(az)), np.cos(np.radians(az))
    r = station_table().loc[station]
    dx, dy, dz = r.east_m - g["x_m"] * sa, r.north_m - g["x_m"] * ca, -g["z_m"]
    R = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    sp = np.maximum(g["speed_mps"], 1e-6)
    moving = g["speed_mps"] >= 1
    ux = np.where(moving, -g["vx_mps"] * sa / sp, 0.0)
    uy = np.where(moving, -g["vx_mps"] * ca / sp, 0.0)
    uz = np.where(moving, -g["vz_mps"] / sp, -1.0)
    cosphi = np.clip((ux * dx + uy * dy + uz * dz) / R, -1, 1)
    return pd.DataFrame(dict(t_s=ts, t_obs=ts + R / c, r_m=R, alt_km=g["z_m"] / 1000,
                             downrange_km=g["x_m"] / 1000, speed_mps=g["speed_mps"], mach=g["mach"],
                             phi_deg=np.degrees(np.arccos(cosphi)),
                             elevation_deg=np.degrees(np.arcsin(g["z_m"] / R))))
