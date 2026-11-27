"""Launch-catalog rows as ksclib Events, for ensemble studies across 2016–2026.

The launch catalog (``event_catalog_workflow_v5``, import name ``kscrockets``) gives, for each
event, an ``event_id``, a UTC time, a pad and a name. This module turns such a row into a
:class:`ksclib.Event` so that the same reading, instrument-correction and geometry code serves
every launch, whatever the network looked like at the time.

The network changed many times since 2016, so an *ensemble file* (YAML, see
``07_ensemble_paper/ensemble.yaml``) lists **network eras**, each a date range saying where the
waveforms, responses and station coordinates are:

``kind: stationxml``   2016–2022 campaigns. One StationXML with time-dependent epochs
                       (``03_stationxml/KSC.xml``) gives coordinates *and* responses; waveforms
                       come from an SDS root (``/Volumes/classdata/remastered/SDS_KSC``).
``kind: centaur``      2026 network. As ``09_artemis2_paper/artemis2.yaml``: flovopy.ingest project
                       (master SDS), per-station Centaur response XMLs (the latest file written at
                       or before the event is used), infraBSU stage, SmartSolo PAZ, Gem response from
                       gemlog; coordinates from a sheet of the station spreadsheet.

Typical use::

    from ksclib import catalog_events as ce
    ens = ce.load_ensemble("07_ensemble_paper/ensemble.yaml")
    ev = ce.event_from_row(row, ens)          # row: dict / pandas Series from the catalog
    raw = ce.read_raw(ev)
    clips = ce.clip_intervals(raw, ev)        # Gem overflow (eras with Gems only)
    st = ce.correct(raw, ev)                  # Pa and m/s
    peaks = ce.peak_amplitudes(st, ev, ce.station_table(ev), clips)

Nothing here changes the existing ksclib modules; the ``centaur`` era delegates to
:func:`ksclib.instrument_correct`, :func:`ksclib.event_stream_raw` and :func:`ksclib.station_table`.
"""
from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from obspy import Stream, UTCDateTime

from .seedcodes import is_centaur
from .event import DEFAULT_CHANNEL_GROUPS, DEFAULT_SMARTSOLO_GEOPHONE, REPO_ROOT, Event, _expand

STATIC_EVENT_TYPES = {"pad_explosion", "explosion", "static_fire"}


# ---------------------------------------------------------------------------
# Ensemble configuration
# ---------------------------------------------------------------------------
@dataclass
class Era:
    """One configuration of the network, valid for start <= origin time < end."""
    name: str
    kind: str                               # "stationxml" or "centaur"
    start: UTCDateTime
    end: UTCDateTime
    sds: Path | None = None                 # stationxml eras: SDS root
    stationxml: Path | None = None          # stationxml eras: coordinates + responses
    channel_groups: dict = field(default_factory=dict)
    gem_channel_prefix: str | None = None   # channels recorded by Gem loggers (overflow masking)
    seed_band_codes: bool = False           # centaur eras: rename D?? traces to SEED C??/H?? (ksclib.seedcodes)
    centaur: dict = field(default_factory=dict)   # centaur eras: artemis2.yaml-style sections

    def contains(self, t) -> bool:
        return self.start <= UTCDateTime(t) < self.end


@dataclass
class Ensemble:
    """Network eras, pad coordinates, analysis windows and output folder for an ensemble study."""
    eras: list[Era]
    pads: pd.DataFrame                      # index: pad code (LC40, LC39A, ...); columns lat, lon
    window: dict
    out_dir: Path
    yaml_path: Path | None = None
    raw: dict = field(default_factory=dict)

    def era_for(self, t) -> Era:
        for era in self.eras:
            if era.contains(t):
                return era
        raise LookupError(f"No network era covers {UTCDateTime(t)}")


def load_ensemble(yaml_path) -> Ensemble:
    """Read an ensemble file (eras, pads, window, output)."""
    yaml_path = Path(yaml_path).resolve()
    base = yaml_path.parent
    raw = yaml.safe_load(yaml_path.read_text())
    subs = {"base_dir": base, "repo_root": REPO_ROOT}
    P = lambda v: _expand(v, subs, base)  # noqa: E731

    pads = []
    pcfg = raw.get("pads", {})
    for f in pcfg.get("files", []):
        pads.append(pd.read_csv(P(f)))
    extra = pcfg.get("extra", {}) or {}
    if extra:
        pads.append(pd.DataFrame([dict(pad=k, lat=v[0], lon=v[1]) for k, v in extra.items()]))
    pads = pd.concat(pads, ignore_index=True) if pads else pd.DataFrame(columns=["pad", "lat", "lon"])
    pads["pad"] = pads["pad"].map(normalize_pad)
    pads = pads.drop_duplicates("pad", keep="last").set_index("pad")

    eras = []
    for e in raw["eras"]:
        eras.append(Era(
            name=e["name"], kind=e["kind"],
            start=UTCDateTime(str(e["start"])), end=UTCDateTime(str(e["end"])),
            sds=P(e.get("sds")), stationxml=P(e.get("stationxml")),
            channel_groups={k: tuple(v) for k, v in e.get("channel_groups", DEFAULT_CHANNEL_GROUPS).items()},
            gem_channel_prefix=e.get("gem_channel_prefix"),
            seed_band_codes=bool(e.get("seed_band_codes", False)),
            centaur={k: e[k] for k in ("ingest", "stations", "responses", "paths") if k in e},
        ))
    out = raw.get("output", {})
    env = out.get("env")
    out_dir = Path(os.environ[env]).expanduser() if env and env in os.environ else P(out.get("dir", "output"))
    return Ensemble(eras=eras, pads=pads, window=raw.get("window", {}), out_dir=out_dir,
                    yaml_path=yaml_path, raw=raw)


# ---------------------------------------------------------------------------
# Catalog fields
# ---------------------------------------------------------------------------
def normalize_pad(value) -> str:
    """Pad code as used in the pad tables: '40', 'SLC-40', 'LC-40', 'Space Launch Complex 40' -> 'LC40'.

    Values that are not launch complexes (SLF, L1011, 'Cape Canaveral', blank) are returned stripped.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = str(value).strip()
    u = re.sub(r"\s+", " ", s.upper())
    u = re.sub(r"^(SPACE LAUNCH COMPLEX|LAUNCH COMPLEX|SLC|LC)[ -]*", "", u)
    if re.fullmatch(r"\d{2}[A-Z]?", u):
        return "LC" + u
    return s


def pad_location(ens: Ensemble, pad) -> tuple[float, float]:
    """(lat, lon) of a pad from the ensemble's pad tables."""
    code = normalize_pad(pad)
    if code not in ens.pads.index:
        raise KeyError(f"No coordinates for pad {pad!r} (normalized {code!r}); add it under pads: extra")
    r = ens.pads.loc[code]
    return float(r.lat), float(r.lon)


def _get(row, key, default=None):
    try:
        v = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
        return default
    return v


def _classify_vehicle():
    """kscrockets.catalog.classify_vehicle, loaded from this repository's source tree if not installed."""
    try:
        from kscrockets.catalog import classify_vehicle
        return classify_vehicle
    except ImportError:          # not installed (or shadowed by a stale namespace directory)
        import importlib.util
        path = REPO_ROOT / "event_catalog_workflow_v5" / "src" / "kscrockets" / "catalog.py"
        spec = importlib.util.spec_from_file_location("_kscrockets_catalog", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.classify_vehicle


def load_catalog(ens: Ensemble, event_types=None, start=None, end=None, extra=True) -> pd.DataFrame:
    """Catalog events from the ensemble's sqlite (``events`` table) plus its ``extra_events``.

    Adds ``vehicle`` (kscrockets rules, from the name), ``pad_code`` (normalized), ``year`` and
    ``era``. `event_types` filters on ``event_type``; `start`/`end` on the event time.
    """
    import sqlite3
    base = ens.yaml_path.parent if ens.yaml_path else Path.cwd()
    db = _expand(ens.raw["catalog"]["sqlite"], {"base_dir": base, "repo_root": REPO_ROOT}, base)
    with sqlite3.connect(db) as con:
        df = pd.read_sql("SELECT * FROM events", con)
    if extra and ens.raw.get("extra_events"):
        df = pd.concat([df, pd.DataFrame(ens.raw["extra_events"])], ignore_index=True)
    t = pd.to_datetime(df["event_time_utc"].astype(str), utc=True, format="mixed")
    df["event_time_utc"] = t.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ").str.replace(".000000Z", "Z")
    if event_types:
        df = df[df.event_type.isin(event_types)]
    if start is not None:
        df = df[t.loc[df.index] >= pd.Timestamp(str(UTCDateTime(start)))]
    if end is not None:
        df = df[t.loc[df.index] <= pd.Timestamp(str(UTCDateTime(end)))]
    df = df.copy()
    t = t.loc[df.index]
    classify = _classify_vehicle()
    vehicle = df["vehicle"] if "vehicle" in df else pd.Series("", index=df.index)
    df["vehicle"] = [v if isinstance(v, str) and v.strip() else classify(n)
                     for v, n in zip(vehicle, df["name"].fillna(""))]
    df["pad_code"] = df["pad"].map(normalize_pad)
    df["year"] = t.dt.year
    era_names = []
    for x in df["event_time_utc"]:
        try:
            era_names.append(ens.era_for(x).name)
        except LookupError:
            era_names.append(None)
    df["era"] = era_names
    return df.sort_values("event_time_utc").reset_index(drop=True)


def event_kind(event_type) -> str:
    """'static' for pad explosions and static fires, otherwise 'launch' (moving source)."""
    return "static" if str(event_type or "").lower() in STATIC_EVENT_TYPES else "launch"


# ---------------------------------------------------------------------------
# Row -> Event
# ---------------------------------------------------------------------------
def event_from_row(row, ens: Ensemble, unlocated_site: tuple[float, float] | None = None, **overrides) -> Event:
    """Build a :class:`ksclib.Event` from a launch-catalog row (dict or pandas Series).

    Uses ``event_id``, ``event_time_utc``, ``pad``, ``name`` (or ``mission``) and ``event_type``.
    The network era is chosen from the origin time. Keyword ``overrides`` replace Event fields
    (e.g. ``restored=...`` or ``launch_azimuth_deg=...``). Catalog fields and the era name are kept
    in ``Event.raw``.

    Events with no pad coordinates (offshore Trident launches, air launches, reentry booms) raise
    KeyError, unless ``unlocated_site`` = (lat, lon) is given: that reference point is used for
    distances, and ``Event.raw["source_location"]`` is "reference" (else "pad").
    """
    t0 = UTCDateTime(str(_get(row, "event_time_utc")))
    era = ens.era_for(t0)
    located = "pad"
    try:
        lat, lon = pad_location(ens, _get(row, "pad"))
    except KeyError:
        if unlocated_site is None:
            raise
        (lat, lon), located = unlocated_site, "reference"
    event_id = str(_get(row, "event_id", f"ksc-{t0.strftime('%Y%m%dT%H%M%S')}"))
    name = str(_get(row, "name") or _get(row, "mission") or event_id)
    w = ens.window
    common = dict(
        name=name, kind=event_kind(_get(row, "event_type")), origin_time=t0,
        site_name=normalize_pad(_get(row, "pad")), site_lat=lat, site_lon=lon,
        pretrigger=float(w.get("pretrigger", 600)), duration=float(w.get("duration", 600)),
        posttrigger=float(w.get("posttrigger", 0)),
        trim_before=float(w.get("trim_before", 30)), trim_after=float(w.get("trim_after", 300)),
        out_dir=ens.out_dir / event_id, channel_groups=dict(era.channel_groups),
        raw={"catalog_row": {k: (str(v) if v is not None else None) for k, v in dict(row).items()},
             "era": era.name, "era_kind": era.kind, "event_id": event_id,
             "gem_channel_prefix": era.gem_channel_prefix, "source_location": located},
        yaml_path=ens.yaml_path,
        seed_band_codes=era.kind == "stationxml" or era.seed_band_codes,
    )
    if era.kind == "stationxml":
        ev = Event(project_yaml=None, run_id=None, project={}, project_root=era.sds.parent,
                   master_sds=era.sds, run_dir=None, station_file=era.stationxml, station_sheet=None,
                   site_sheet=None, paths={"stationxml": era.stationxml}, **common)
    elif era.kind == "centaur":
        ev = _centaur_event(era, ens, common)
    else:
        raise ValueError(f"Unknown era kind {era.kind!r}")
    for k, v in overrides.items():
        if not hasattr(ev, k):
            raise AttributeError(f"Event has no field {k!r}")
        setattr(ev, k, v)
    return ev


def _centaur_event(era: Era, ens: Ensemble, common: dict) -> Event:
    from flovopy.ingest.config import load_project, master_sds, run_dir

    base = ens.yaml_path.parent if ens.yaml_path else Path.cwd()
    subs = {"base_dir": base, "repo_root": REPO_ROOT}
    c = era.centaur
    ing = c["ingest"]
    project_yaml = _expand(ing["project_yaml"], subs, base)
    project = load_project(project_yaml)
    project_root = Path(project["_root"])
    run_id = ing.get("run_id")
    rdir = Path(run_dir(project, run_id)) if run_id else None
    subs.update(project_root=project_root, run_dir=rdir or project_root)
    P = lambda v: _expand(v, subs, base)  # noqa: E731
    st, resp = c["stations"], c.get("responses", {})
    return Event(
        project_yaml=project_yaml, run_id=run_id, project=project, project_root=project_root,
        master_sds=Path(master_sds(project)), run_dir=rdir,
        station_file=P(st["file"]), station_sheet=st["sheet"], site_sheet=st.get("site_sheet"),
        centaur_response_dirs=[P(d) for d in resp.get("centaur_dirs", [])],
        infrabsu_xml=P(resp.get("infrabsu_xml")),
        infrabsu_channels=tuple(resp.get("infrabsu_channels", ("DD0", "DD1", "DD2"))),
        smartsolo_geophone={**DEFAULT_SMARTSOLO_GEOPHONE, **resp.get("smartsolo_geophone", {})},
        paths={k: P(v) for k, v in c.get("paths", {}).items()},
        **common,
    )


def is_stationxml_event(ev: Event) -> bool:
    return "stationxml" in ev.paths


# ---------------------------------------------------------------------------
# Stations, waveforms, correction
# ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _inventory(path: str):
    from obspy import read_inventory
    return read_inventory(path)


def inventory(ev: Event):
    """The era's StationXML inventory, restricted to epochs active at the origin time."""
    return _inventory(str(ev.paths["stationxml"])).select(time=ev.origin_time)


def station_table(ev: Event) -> pd.DataFrame:
    """Stations active at the event, with distance (km) and azimuth (deg) from the pad.

    Same columns as :func:`ksclib.station_table` (index: station code).
    """
    if not is_stationxml_event(ev):
        from .geometry import station_table as sheet_table
        return sheet_table(ev)
    from obspy.geodetics import gps2dist_azimuth
    rows, seen = [], set()
    for net in inventory(ev):
        for sta in net:
            if sta.code in seen:
                continue
            seen.add(sta.code)
            d, az, _ = gps2dist_azimuth(ev.site_lat, ev.site_lon, sta.latitude, sta.longitude)
            rows.append(dict(station=sta.code, network=net.code, lat=sta.latitude, lon=sta.longitude,
                             distance_km=d / 1000, azimuth_deg=az,
                             east_m=d * np.sin(np.radians(az)), north_m=d * np.cos(np.radians(az))))
    cols = ["station", "network", "lat", "lon", "distance_km", "azimuth_deg", "east_m", "north_m"]
    return pd.DataFrame(rows, columns=cols).set_index("station")


def read_raw(ev: Event, starttime=None, endtime=None) -> Stream:
    """Raw counts for the event window from the era's SDS archive (all channel groups)."""
    from . import data
    if is_stationxml_event(ev):     # KSC.xml uses SEED codes (C??/H??): rename D?? traces to match
        from .seedcodes import normalize_stream
        return normalize_stream(data.get_event_stream(ev, starttime=starttime, endtime=endtime))
    groups = tuple(g for g in ("USF", "BSU", "SmartSolo") if g in ev.channel_groups)
    return data.event_stream_raw(ev, groups=groups, starttime=starttime, endtime=endtime)


def _era_gem_prefix(ev: Event):
    return ev.raw.get("gem_channel_prefix")


def clip_intervals(raw: Stream, ev: Event) -> dict:
    """Gem overflow/reset intervals ``{seed_id: [(t0, t1), ...]}`` (empty where no Gems were deployed)."""
    prefix = _era_gem_prefix(ev)
    if not prefix:
        return {}
    from flovopy.ingest.gem_overflow import stream_clip_intervals
    gems = Stream([tr for tr in raw if not is_centaur(tr)])   # Centaur HD? (100 sps) are not Gems
    return stream_clip_intervals(gems, channel_prefix=prefix)


def channel_units(ev: Event, tr) -> str | None:
    """Physical input units of a channel: 'Pa', 'm/s', ... (None if no response is known)."""
    if is_stationxml_event(ev):
        try:
            resp = inventory(ev).get_response(tr.id, tr.stats.starttime)
        except Exception:
            return None
        u = (resp.instrument_sensitivity.input_units or "").strip()
        return {"PA": "Pa", "M/S": "m/s", "M/S**2": "m/s**2", "M": "m"}.get(u.upper(), u or None)
    cha = tr.stats.channel
    if cha.startswith(("DH", "CH", "DP", "HH", "EH")):
        return "m/s"
    if cha.startswith(("DD", "CD", "HD")):
        return "Pa"
    return None


def correct(st: Stream, ev: Event, pre_filt_low=(0.01, 0.02)) -> Stream:
    """Copy of `st` in physical units (Pa for pressure, m/s for ground velocity).

    stationxml eras: response removal from the era's StationXML at the trace time (ground motion
    to velocity; pressure left as pressure); traces from Gem channels are overflow-repaired first.
    centaur eras: :func:`ksclib.instrument_correct`. Channels without a response are dropped with
    a warning.
    """
    if not is_stationxml_event(ev):
        from .correct import instrument_correct
        return instrument_correct(st, ev, pre_filt_low=pre_filt_low)
    inv = inventory(ev)
    prefix = _era_gem_prefix(ev)
    out = Stream()
    for tr in st.copy().split():        # gaps: correct each contiguous segment
        if tr.stats.npts < 2 * tr.stats.sampling_rate:
            continue
        t = tr.copy()
        units = channel_units(ev, t)
        if units is None:
            warnings.warn(f"{tr.id}: no response in {ev.paths['stationxml'].name} at {ev.origin_time}; dropped")
            continue
        nyq = 0.5 * t.stats.sampling_rate
        try:
            if prefix and t.stats.channel.startswith(prefix) and not is_centaur(t):
                from flovopy.ingest.gem_overflow import repair_gem_overflow
                t = repair_gem_overflow(t)
            t.detrend("linear")
            out_kind = {"m/s": "VEL", "m/s**2": "VEL", "m": "VEL"}.get(units, "DEF")
            with warnings.catch_warnings():     # ObsPy: "can not map unit 'PA'" (expected for pressure)
                warnings.filterwarnings("ignore", message="ObsPy can not map unit")
                t.remove_response(inventory=inv, output=out_kind, zero_mean=True, taper=True,
                                  pre_filt=(*pre_filt_low, 0.94 * nyq, 0.98 * nyq))
        except Exception as exc:
            warnings.warn(f"{tr.id}: not corrected ({type(exc).__name__}: {exc})")
            continue
        t.stats.units = "Pa" if units == "Pa" else "m/s"
        out.append(t)
    return out


# ---------------------------------------------------------------------------
# Peak amplitudes
# ---------------------------------------------------------------------------
def _mask_from_intervals(tr, intervals):
    from flovopy.ingest.gem_overflow import clip_mask
    return clip_mask(tr, intervals) if intervals else np.zeros(tr.stats.npts, bool)


def peak_amplitudes(st: Stream, ev: Event, stations: pd.DataFrame | None = None, clips: dict | None = None,
                    signal=(-30.0, 300.0), noise=None, pressure_highpass=0.5, seismic_highpass=1.0,
                    units=None) -> pd.DataFrame:
    """Peak |p| (Pa) on pressure channels and peak |v| (m/s) on vertical velocity channels.

    `signal` and `noise` are windows in seconds relative to the origin time (noise defaults to the
    same length just before the signal window). Pressure traces are high-passed at
    `pressure_highpass` Hz, seismic at `seismic_highpass` Hz (as Artemis II notebook 40). Samples
    inside `clips` intervals (Gem overflow) are excluded; if any fall in the signal window the
    peak is a lower bound (``lower_bound=True``). `units` maps seed_id -> 'Pa'/'m/s' (default:
    ``tr.stats.units`` or :func:`channel_units`).
    """
    clips = clips or {}
    noise = noise or (signal[0] - (signal[1] - signal[0]), signal[0])
    t0 = ev.origin_time
    rows = []
    for sid in sorted({tr.id for tr in st}):
        segs = st.select(id=sid)
        tr = segs[0]
        u = (units or {}).get(sid) or tr.stats.get("units") or channel_units(ev, tr)
        cha = tr.stats.channel
        if u == "Pa":
            kind, fc = "pressure", pressure_highpass
        elif u == "m/s" and cha.endswith("Z"):
            kind, fc = "seismic_Z", seismic_highpass
        else:
            continue
        best, noise_peak, n_sig, lower = None, np.nan, 0, False
        for seg in segs:                      # contiguous segments (gaps split upstream)
            t = seg.copy()
            t.data = np.ma.filled(t.data, 0).astype(float) if np.ma.isMaskedArray(t.data) else t.data.astype(float)
            t.detrend("demean")
            t.taper(0.02)
            if fc and fc < 0.5 * t.stats.sampling_rate:
                t.filter("highpass", freq=fc, corners=4, zerophase=True)
            tt = t.times(reftime=t0)
            bad = _mask_from_intervals(t, clips.get(sid, []))
            x = np.abs(t.data)
            ms = (tt >= signal[0]) & (tt <= signal[1])
            mn = (tt >= noise[0]) & (tt < noise[1])
            n_sig += int(ms.sum())
            lower |= bool((ms & bad).any())
            good = ms & ~bad
            if good.any():
                i = np.flatnonzero(good)[np.argmax(x[good])]
                if best is None or x[i] > best[0]:
                    best = (float(x[i]), float(tt[i]))
            if (mn & ~bad).any():
                noise_peak = np.nanmax([noise_peak, float(x[mn & ~bad].max())])
        if best is None:
            continue
        sta = tr.stats.station
        dist = az = np.nan
        if stations is not None and sta in stations.index:
            dist, az = float(stations.loc[sta, "distance_km"]), float(stations.loc[sta, "azimuth_deg"])
        rows.append(dict(
            event_id=ev.raw.get("event_id"), event=ev.name, origin_time=str(t0), pad=ev.site_name,
            era=ev.raw.get("era"), seed_id=sid, station=sta, channel=cha, kind=kind, units=u,
            sampling_rate=tr.stats.sampling_rate, distance_km=dist, azimuth_deg=az,
            peak=best[0], t_peak_s=best[1], noise_peak=noise_peak,
            snr=best[0] / noise_peak if noise_peak and noise_peak > 0 else np.nan,
            coverage=min(1.0, n_sig / max(1, round((signal[1] - signal[0]) * tr.stats.sampling_rate))),
            lower_bound=lower,
        ))
    return pd.DataFrame(rows)
