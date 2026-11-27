"""Per-event products for the KSC rocket catalog: waveforms, plots, metrics and detected onsets.

One call processes one catalog event (any type: launch, landing boom, static fire, explosion,
rollout ...) with the shared reading and correction code of :mod:`ksclib.catalog_events`::

    from ksclib import catalog_events as ce, event_products as ep
    ens = ce.load_ensemble("07_ensemble_paper/ensemble.yaml")
    res = ep.process_event(row, ens, out_root="/Volumes/classdata/KSC/event_catalog", run_id="pilot-...")
    res.metrics     # long table: one row per channel x metric
    res.onsets      # strongest STA/LTA onset per channel, with origin-time estimate
    res.products    # files written (miniSEED, PNG, CSV)

Products go to ``<out_root>/<YYYY>/<event_id>/``. Every row carries ``data_source`` (the archive or,
later, ``fdsn:<provider>``) so that regional/external data can be processed the same way.

Metrics are on instrument-corrected traces (Pa, m/s), high-passed as Artemis II notebook 40
(pressure 0.5 Hz, seismic 1 Hz), in a signal window around the catalog time with a noise window
before it. Catalog times can be minutes (or a launch window) off, so the STA/LTA onsets are
searched over a wider window and turned into origin-time estimates (onset - distance / c).
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import Stream, UTCDateTime

from . import catalog_events as ce

PRODUCTS_VERSION = "0.2"   # 0.2: metric set of science plan sections 2.1-2.2
SOUND_SPEED = 343.0          # m/s, until per-event weather is available

DEFAULTS = dict(
    read_before=900.0,       # s before catalog time read from the archive
    read_after=900.0,        # s after
    signal=(-30.0, 300.0),   # metric window, s relative to catalog time
    noise_length=300.0,      # noise window just before the signal window
    # STA/LTA search window (s relative to catalog time, + r/c), by catalog time precision:
    # second/minute times are within ~2 min; estimated (landings) ~3 min; others (approximate
    # static fires, launch windows) are searched over the whole read window.
    onset_search={"second": (-120.0, 120.0), "minute": (-120.0, 120.0), "estimated": (-180.0, 180.0),
                  "default": (-600.0, 600.0)},
    onset_relative=0.5,      # earliest trigger at least this fraction of the strongest one
    sta=0.5, lta=20.0, trig_on=5.0, trig_off=1.5,
    pressure_highpass=0.5, seismic_highpass=1.0,
    plot_window=(-60.0, 300.0),
)


# Event types whose detected time is a source time at the pad (ignition, explosion, static fire).
# Booms are made aloft (landings, reentries) and rollouts move, so onset - r/c is not their time.
PAD_SOURCE_TYPES = {"orbital_launch", "launch", "launch_failure", "pad_explosion", "explosion", "static_fire",
                    "pad_abort", "aborted_launch", "suborbital_launch"}
MOVING_SOURCE_TYPES = {"orbital_launch", "launch", "launch_failure", "aborted_launch", "suborbital_launch"}
AMBIGUOUS_RIVAL = 0.8   # one-station detections with a rival arrival this strong are not used
MAX_NEAREST_KM = 5.0     # farther, a launch's first clear arrival comes from the rising vehicle
# Events with no source coordinates (Trident off the Cape, Pegasus air launches, reentry booms,
# bolides): distances and record sections are from this nominal point between the Cape and KSC,
# and their detected times are never used as source times.
REFERENCE_SITE = (28.55, -80.62)


def catalog_usable(event_type, det: dict) -> tuple[bool, str]:
    """Whether a detected origin may be used as the catalog event time, and why not."""
    if not det:
        return False, "no detection"
    if str(event_type) not in PAD_SOURCE_TYPES:
        return False, f"{event_type}: source not at the pad"
    if det.get("n_stations", 0) < 2 and det.get("rival_ratio", 0) >= AMBIGUOUS_RIVAL:
        return False, f"one station with a competing arrival ({det['rival_ratio']:.2f} x as strong)"
    if str(event_type) in MOVING_SOURCE_TYPES and not (det.get("nearest_km", np.inf) <= MAX_NEAREST_KM):
        return False, f"nearest station {det.get('nearest_km', np.nan):.1f} km > {MAX_NEAREST_KM:g} km"
    return True, ""


@dataclass
class EventResult:
    event_id: str
    status: str = "ok"
    error: str = ""
    data_source: str = ""
    n_raw: int = 0
    n_corrected: int = 0
    metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    onsets: pd.DataFrame = field(default_factory=pd.DataFrame)
    detected: dict = field(default_factory=dict)
    products: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------
def _kind(tr) -> str | None:
    u = tr.stats.get("units")
    if u == "Pa":
        return "pressure"
    if u == "m/s":
        return "seismic_" + tr.stats.channel[-1]
    return None


def _filtered(tr, fc):
    t = tr.copy()
    t.data = np.ma.filled(t.data, 0).astype(float) if np.ma.isMaskedArray(t.data) else t.data.astype(float)
    t.detrend("demean"); t.taper(0.02)
    if fc and fc < 0.5 * t.stats.sampling_rate:
        t.filter("highpass", freq=fc, corners=4, zerophase=True)
    return t


def _merged(st: Stream, sid: str):
    """One trace per seed id, gaps filled with zeros, and the fraction of real samples."""
    s = st.select(id=sid).copy()
    n_real = sum(tr.stats.npts for tr in s)
    s.merge(method=1, fill_value=0)
    tr = s[0]
    return tr, n_real / max(tr.stats.npts, 1)


# Frequency bands (Hz) for band-limited metrics; a band is skipped above 0.8 x Nyquist.
BANDS = ((0.5, 2.0), (2.0, 8.0), (8.0, 32.0), (32.0, 100.0))


def channel_metrics(tr, t0: UTCDateTime, signal, noise, fc) -> dict:
    """Standard amplitude, exposure, duration and spectral metrics of one corrected, merged trace.

    Definitions follow notes/rocket_seismology_science_plan.md sections 2.1-2.2. All are
    band-limited: high-pass `fc` (Hz) up to the anti-alias corner (~0.4 x sampling rate), recorded
    as ``band_low_hz`` / ``band_high_hz``. Pressure peaks are unweighted, band-limited peak SPL
    (re 20 uPa); ``sel_db`` and ``leq_db`` integrate over the whole signal window. Seismic channels
    get PGV (peak |v|), PGA (from d/dt) and PGD (from the integral, same high-pass).
    """
    from scipy.signal import welch
    from scipy.stats import kurtosis, skew
    t = _filtered(tr, fc)
    fs = t.stats.sampling_rate
    tt = t.times(reftime=t0)
    x = t.data
    ms = (tt >= signal[0]) & (tt <= signal[1]); mn = (tt >= noise[0]) & (tt < noise[1])
    out = {}
    if ms.sum() < fs or mn.sum() < fs:
        return out
    xs, xn = x[ms], x[mn]
    pressure = tr.stats.get("units") == "Pa"
    out["band_low_hz"], out["band_high_hz"] = float(fc or 0), float(0.4 * fs)
    out["window_start_s"], out["window_end_s"] = float(signal[0]), float(signal[1])
    i = int(np.argmax(np.abs(xs)))
    out["peak"] = float(abs(xs[i])); out["t_peak_s"] = float(tt[ms][i])
    out["peak_positive"] = float(xs.max()); out["peak_negative"] = float(xs.min())
    out["peak_to_peak"] = float(xs.max() - xs.min())
    out["noise_peak"] = float(np.max(np.abs(xn)))
    out["snr_peak"] = out["peak"] / out["noise_peak"] if out["noise_peak"] > 0 else np.nan
    out["rms_signal"] = float(np.sqrt(np.mean(xs ** 2))); out["rms_noise"] = float(np.sqrt(np.mean(xn ** 2)))
    out["integrated_square"] = float(np.sum(xs ** 2) / fs)          # Pa^2 s or m^2/s
    excess = np.clip(xs ** 2 - out["rms_noise"] ** 2, 0, None)
    out["integrated_square_minus_noise"] = float(np.sum(excess) / fs)
    c = np.cumsum(excess)
    if c[-1] > 0:
        i5, i95 = np.searchsorted(c, 0.05 * c[-1]), np.searchsorted(c, 0.95 * c[-1])
        out["duration_5_95_s"] = float((i95 - i5) / fs)
        out["t_energy_5_s"] = float(tt[ms][min(i5, len(xs) - 1)])
    out["skewness"] = float(skew(xs)); out["kurtosis"] = float(kurtosis(xs, fisher=False))
    dx = np.gradient(x, 1 / fs)[ms]
    nper = int(min(len(xs), max(256, 4 * fs)))
    f, p = welch(xs, fs=fs, nperseg=nper)
    _, pn = welch(xn, fs=fs, nperseg=min(nper, len(xn)))
    band = (f >= max(fc or 0, f[1])) & (f <= 0.4 * fs)
    if band.any() and len(pn) == len(p):
        out["f_dominant_hz"] = float(f[band][np.argmax(p[band])])
        out["f_centroid_hz"] = float(np.sum(f[band] * p[band]) / np.sum(p[band]))
        ratio = p[band] / np.where(pn[band] > 0, pn[band], np.nan)
        usable = f[band][ratio > 10]
        if usable.size:
            out["f_snr10_min_hz"], out["f_snr10_max_hz"] = float(usable.min()), float(usable.max())
        df = f[1] - f[0]
        for lo, hi in BANDS:
            if hi > 0.8 * 0.5 * fs or lo < (fc or 0):
                continue
            b = (f >= lo) & (f < hi)
            out[f"band_{lo:g}_{hi:g}hz_mean_square"] = float(np.sum(p[b]) * df)   # variance in band
            if pn[b].sum() > 0:
                out[f"band_{lo:g}_{hi:g}hz_snr_power"] = float(p[b].sum() / pn[b].sum())
    if pressure:
        P = 20e-6
        out["spl_peak_db"] = 20 * np.log10(out["peak"] / P) if out["peak"] > 0 else np.nan
        out["leq_db"] = 10 * np.log10(np.mean(xs ** 2) / P ** 2) if out["rms_signal"] > 0 else np.nan
        out["sel_db"] = 10 * np.log10(out["integrated_square"] / P ** 2) if out["integrated_square"] > 0 else np.nan
        out["dpdt_skewness"] = float(skew(dx)); out["dpdt_kurtosis"] = float(kurtosis(dx, fisher=False))
    else:
        out["pgv"] = out["peak"]
        out["pga"] = float(np.max(np.abs(dx)))
        d = np.cumsum(x) / fs
        dtr = t.copy(); dtr.data = d
        if fc and fc < 0.5 * fs:
            dtr.filter("highpass", freq=fc, corners=4, zerophase=True)
        out["pgd"] = float(np.max(np.abs(dtr.data[ms])))
    return out


def vector_metrics(st_station: Stream, t0, signal, fc) -> dict:
    """Horizontal and three-component vector PGV of one station's velocity channels.

    Uses the first channel set (same location and band code) that has Z plus two horizontals
    (N/E or 1/2). Returns {} if there is none.
    """
    groups = {}
    for tr in st_station:
        if tr.stats.get("units") != "m/s":
            continue
        groups.setdefault((tr.stats.location, tr.stats.channel[:2]), {})[tr.stats.channel[-1]] = tr
    for (loc, band), comps in sorted(groups.items()):
        h = [comps[c] for c in ("N", "E") if c in comps] or [comps[c] for c in ("1", "2") if c in comps]
        if "Z" not in comps or len(h) != 2:
            continue
        fs = comps["Z"].stats.sampling_rate
        trs = [_filtered(tr, fc) for tr in (comps["Z"], *h)]
        if any(tr.stats.sampling_rate != fs for tr in trs):
            continue
        start = max(tr.stats.starttime for tr in trs); end = min(tr.stats.endtime for tr in trs)
        trs = [tr.trim(start, end) for tr in trs]
        n = min(tr.stats.npts for tr in trs)
        z, a, b = (tr.data[:n] for tr in trs)
        tt = trs[0].times(reftime=t0)[:n]
        ms = (tt >= signal[0]) & (tt <= signal[1])
        if ms.sum() < fs:
            continue
        hv = np.hypot(a, b)[ms]; v3 = np.sqrt(z ** 2 + a ** 2 + b ** 2)[ms]
        return {"pgv_horizontal_vector": float(hv.max()), "pgv_3c_vector": float(v3.max()),
                "t_peak_3c_s": float(tt[ms][np.argmax(v3)]), "vector_channels": f"{loc}.{band}?"}
    return {}


def stalta_onset(tr, t0: UTCDateTime, search, fc, sta=0.5, lta=20.0, on=4.0, off=1.5, relative=0.5):
    """STA/LTA onset in `search` (s relative to t0): (onset_s, max_ratio) or None.

    Takes the earliest trigger whose peak ratio is at least `relative` x the strongest one: the
    event is usually the largest arrival, but noise blips trigger earlier and later sources (e.g.
    booster-landing booms ~8 min after a Falcon Heavy launch) can be stronger at some stations.
    """
    from obspy.signal.trigger import classic_sta_lta, trigger_onset
    t = _filtered(tr, fc)
    fs = t.stats.sampling_rate
    ns, nl = int(sta * fs), int(lta * fs)
    if t.stats.npts < 2 * nl:
        return None
    cft = classic_sta_lta(t.data, ns, nl)
    cft[:nl] = 0                                   # LTA not yet filled
    tt = t.times(reftime=t0)
    win = (tt >= search[0]) & (tt <= search[1])
    cft = np.where(win, cft, 0)
    trig = trigger_onset(cft, on, off)
    if len(trig) == 0:
        return None
    peaks = [cft[a:b + 1].max() for a, b in trig]
    top = max(peaks)
    k = next(i for i, pk in enumerate(peaks) if pk >= relative * top)
    a, b = trig[k]
    return float(tt[a]), float(peaks[k])


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_record_section(st: Stream, stations: pd.DataFrame, t0, kind: str, title: str, path: Path,
                        window=(-60, 300), fc=0.5, onsets: pd.DataFrame | None = None, c=SOUND_SPEED):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    trs = [tr for tr in st if _kind(tr) == kind]
    if not trs:
        return None
    def dist(tr):
        s = tr.stats.station
        return float(stations.loc[s, "distance_km"]) if s in stations.index else np.nan
    trs.sort(key=lambda tr: (np.nan_to_num(dist(tr), nan=1e9), tr.id))
    fig, ax = plt.subplots(figsize=(11, 0.45 * len(trs) + 2))
    for k, tr in enumerate(trs):
        t = _filtered(tr, fc)
        tt = t.times(reftime=t0); m = (tt >= window[0]) & (tt <= window[1])
        if not m.any():
            continue
        y = t.data[m]; amp = np.max(np.abs(y)) or 1
        ax.plot(tt[m], k + 0.45 * y / amp, lw=0.5, color="k")
        unit = "Pa" if kind == "pressure" else "mm/s"
        scale = amp if kind == "pressure" else amp * 1e3
        ax.text(window[1], k, f" {scale:.3g} {unit}", va="center", fontsize=7)
        d = dist(tr)
        if np.isfinite(d):
            ax.plot([d * 1000 / c] * 2, [k - 0.4, k + 0.4], color="tab:red", lw=1)
        if onsets is not None and not onsets.empty:
            o = onsets[onsets.seed_id == tr.id]
            if len(o) and np.isfinite(o.onset_s.iloc[0]):
                ax.plot([o.onset_s.iloc[0]] * 2, [k - 0.4, k + 0.4], color="tab:blue", lw=1)
    ax.set_yticks(range(len(trs)))
    ax.set_yticklabels([f"{tr.id}  {dist(tr):.2f} km" for tr in trs], fontsize=7)
    ax.set_xlim(*window); ax.set_ylim(-1, len(trs))
    ax.set_xlabel("Time after catalog time (s)")
    ax.set_title(f"{title}\n{kind}, high-pass {fc} Hz, each trace normalized; "
                 f"red: airwave at {c:.0f} m/s, blue: STA/LTA onset", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def plot_station(st: Stream, station: str, t0, title: str, path: Path, window=(-60, 300), fmax=None):
    """Waveform above spectrogram for each corrected channel of one station."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.signal import spectrogram
    trs = sorted([tr for tr in st if tr.stats.station == station and _kind(tr)], key=lambda tr: tr.id)
    if not trs:
        return None
    fig, axes = plt.subplots(2 * len(trs), 1, figsize=(10, 2.6 * len(trs) + 0.6), sharex=True,
                             gridspec_kw=dict(height_ratios=[1, 1.3] * len(trs)))
    for k, tr in enumerate(trs):
        kind = _kind(tr)
        t = _filtered(tr, 0.5 if kind == "pressure" else 1.0)
        tt = t.times(reftime=t0); m = (tt >= window[0]) & (tt <= window[1])
        aw, asg = axes[2 * k], axes[2 * k + 1]
        if m.sum() < 64:
            aw.text(0.5, 0.5, f"{tr.id}: no data in window", transform=aw.transAxes, ha="center"); continue
        y = t.data[m] if kind == "pressure" else t.data[m] * 1e3
        aw.plot(tt[m], y, lw=0.5, color="k")
        aw.set_ylabel("Pa" if kind == "pressure" else "mm/s", fontsize=8)
        aw.text(0.005, 0.85, tr.id, transform=aw.transAxes, fontsize=8)
        fs = t.stats.sampling_rate
        nper = int(min(m.sum() // 4, max(64, fs)))
        f, ts, S = spectrogram(t.data[m], fs=fs, nperseg=nper, noverlap=nper * 3 // 4)
        top = min(fmax or 0.5 * fs, 0.5 * fs)
        sel = (f > 0) & (f <= top)
        asg.pcolormesh(tt[m][0] + ts, f[sel], 10 * np.log10(S[sel] + 1e-30), shading="auto", cmap="magma",
                       vmin=np.percentile(10 * np.log10(S[sel] + 1e-30), 5),
                       vmax=np.percentile(10 * np.log10(S[sel] + 1e-30), 99.5))
        asg.set_yscale("log"); asg.set_ylim(max(f[sel][0], 0.3), top); asg.set_ylabel("Hz", fontsize=8)
    axes[-1].set_xlabel("Time after catalog time (s)")
    axes[0].set_xlim(*window)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=100); plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# One event
# ---------------------------------------------------------------------------
def _data_source(ev) -> str:
    if ce.is_stationxml_event(ev):
        return f"local_sds:{ev.master_sds}"
    return f"local_sds:{ev.master_sds}"


def detected_origin(onsets: pd.DataFrame, min_ratio=8.0, c=SOUND_SPEED, agree_s=3.0) -> dict:
    """Event origin estimate from onsets: onset - r/c, taken from the largest group of channels
    whose estimates agree within `agree_s` (pressure channels; all channels if none).

    Groups are ranked by number of stations, then by their strongest STA/LTA ratio, then by number
    of channels. ``nearest_km`` is the distance of
    the nearest station in the group: for launches, onsets far from the pad tend to come from the
    rising vehicle, so the estimate is biased late when ``nearest_km`` is more than a few km.
    """
    if onsets.empty:
        return {}
    o = onsets[np.isfinite(onsets.origin_est_s) & (onsets.max_ratio >= min_ratio)]
    for kinds, label in ((["pressure"], "pressure"), (None, "all")):
        g = (o if kinds is None else o[o.kind.isin(kinds)]).reset_index(drop=True)
        if g.empty:
            continue
        x = g.origin_est_s.to_numpy()
        groups = [np.abs(x - xi) <= agree_s for xi in x]
        # rank: distinct stations, then the strongest pick, then channel count (co-located
        # channels of one station often share the same noise burst)
        best = max(groups, key=lambda m: (g.station[m].nunique(), g.max_ratio[m].max(), m.sum()))
        sel = g[best]
        # strongest pick that disagrees with the chosen group: a comparable competing arrival
        # makes a one-station detection ambiguous (e.g. two bursts 65 s apart, which is the event?)
        rival = g[~best & (np.abs(g.origin_est_s - np.median(sel.origin_est_s)) > agree_s)]
        rival_ratio = float(rival.max_ratio.max()) / float(sel.max_ratio.max()) if len(rival) else 0.0
        med = float(np.median(sel.origin_est_s))
        spread = float(np.median(np.abs(sel.origin_est_s - med))) if len(sel) > 1 else np.nan
        return dict(offset_s=med, mad_s=spread, n_channels=int(len(sel)), n_stations=int(sel.station.nunique()),
                    n_channels_disagree=int(len(g) - len(sel)), rival_ratio=rival_ratio,
                    nearest_km=float(sel.distance_km.min()) if "distance_km" in sel else np.nan,
                    method=f"stalta_onset_minus_r_over_{c:.0f}ms_{label}_cluster{agree_s:g}s")
    return {}


def process_event(row, ens, out_root, run_id: str, params: dict | None = None,
                  write_waveforms=True, plots=True) -> EventResult:
    """Read, correct, measure, detect and plot one catalog event. Failures are returned, not raised."""
    p = {**DEFAULTS, **(params or {})}
    eid = str(row["event_id"])
    res = EventResult(event_id=eid)
    try:
        ev = ce.event_from_row(row, ens, unlocated_site=REFERENCE_SITE)
        unlocated = ev.raw.get("source_location") == "reference"
        if unlocated:
            res.warnings.append(f"no coordinates for pad {row.get('pad')!r}: distances are from the reference point "
                                f"{REFERENCE_SITE[0]:.2f}N {abs(REFERENCE_SITE[1]):.2f}W, not from the source")
        t0 = ev.origin_time
        res.data_source = _data_source(ev)
        stations = ce.station_table(ev)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            raw = ce.read_raw(ev, starttime=t0 - p["read_before"], endtime=t0 + p["read_after"])
            clips = ce.clip_intervals(raw, ev)
            st = ce.correct(raw, ev)
        res.warnings = res.warnings + sorted({str(x.message)[:200] for x in w})
        for tr in st:                      # centaur-era correction does not label units
            if not tr.stats.get("units"):
                u = ce.channel_units(ev, tr)
                if u in ("Pa", "m/s"):
                    tr.stats.units = u
        res.n_raw, res.n_corrected = len(raw), len(st)
        if not len(st):
            res.status = "no_data" if not len(raw) else "not_corrected"
            return res
        out = Path(out_root) / f"{t0.year}" / eid
        (out / "plots").mkdir(parents=True, exist_ok=True)
        signal = tuple(p["signal"]); noise = (signal[0] - p["noise_length"], signal[0])
        title = f"{row.get('name', '')} | {row.get('event_type', '')} | {ev.site_name} | {t0}"

        prec = str(row.get("event_time_precision") or "").lower()
        search = p["onset_search"].get(prec, p["onset_search"]["default"])
        search = (max(search[0], -p["read_before"] + p["lta"]), min(search[1], p["read_after"] - 30))
        mrows, orows = [], []
        for sid in sorted({tr.id for tr in st}):
            tr, coverage = _merged(st, sid)
            kind = _kind(tr)
            if kind is None:
                continue
            fc = p["pressure_highpass"] if kind == "pressure" else p["seismic_highpass"]
            sta = tr.stats.station
            dist = float(stations.loc[sta, "distance_km"]) if sta in stations.index else np.nan
            az = float(stations.loc[sta, "azimuth_deg"]) if sta in stations.index else np.nan
            base = dict(event_id=eid, run_id=run_id, seed_id=sid, network=tr.stats.network, station=sta,
                        channel=tr.stats.channel, kind=kind, units=tr.stats.units,
                        sampling_rate=tr.stats.sampling_rate, distance_km=dist, azimuth_deg=az,
                        data_source=res.data_source)
            m = channel_metrics(tr, t0, signal, noise, fc)
            lower = any(a < t0 + signal[1] and b > t0 + signal[0] for a, b in clips.get(sid, []))
            m["coverage"] = coverage
            qc = "lower_bound" if lower else ("low_snr" if m.get("snr_peak", 0) < 3 else "")
            for k, v in m.items():
                mrows.append({**base, "metric": k, "value": v, "qc_flag": qc})
            delay = dist * 1000 / SOUND_SPEED if np.isfinite(dist) else 0.0
            on = stalta_onset(tr, t0, (search[0], search[1] + delay), fc,
                              p["sta"], p["lta"], p["trig_on"], p["trig_off"], p["onset_relative"])
            if on:
                orows.append({**base, "onset_s": on[0], "search_s": f"{search[0]:g}:{search[1]:g}", "onset_utc": str(t0 + on[0]), "max_ratio": on[1],
                              "origin_est_s": on[0] - delay if np.isfinite(dist) else np.nan})
        for sta in sorted({tr.stats.station for tr in st}):
            sst = Stream([_merged(st, sid)[0] for sid in sorted({tr.id for tr in st.select(station=sta)})])
            v = vector_metrics(sst, t0, signal, p["seismic_highpass"])
            if v:
                chans = v.pop("vector_channels")
                net = sst[0].stats.network
                dist = float(stations.loc[sta, "distance_km"]) if sta in stations.index else np.nan
                az = float(stations.loc[sta, "azimuth_deg"]) if sta in stations.index else np.nan
                base = dict(event_id=eid, run_id=run_id, seed_id=f"{net}.{sta}.{chans}", network=net, station=sta,
                            channel=chans.split(".")[-1], kind="seismic_vector", units="m/s",
                            sampling_rate=sst[0].stats.sampling_rate, distance_km=dist, azimuth_deg=az,
                            data_source=res.data_source)
                for k, val in v.items():
                    mrows.append({**base, "metric": k, "value": val, "qc_flag": ""})
        res.metrics = pd.DataFrame(mrows)
        res.onsets = pd.DataFrame(orows)
        det = detected_origin(res.onsets)
        if det:
            det["detected_time_utc"] = str(t0 + det["offset_s"])
            det["catalog_usable"], det["not_usable_reason"] = catalog_usable(row.get("event_type"), det)
            if unlocated:
                det["catalog_usable"], det["not_usable_reason"] = False, "source location unknown (distances from a reference point)"
        res.detected = det

        if write_waveforms:
            # raw counts: integer, Steim2-compressed, whole read window (reprocessable after
            # response fixes); corrected: float32, noise + signal window only (for download/plots)
            raw2 = raw.copy().split()
            for tr in raw2:
                tr.data = np.asarray(tr.data).astype(np.int32)
            raw2.write(str(out / "raw_counts.mseed"), format="MSEED", encoding="STEIM2")
            cor = st.copy().trim(t0 + noise[0] - 30, t0 + max(signal[1], p["plot_window"][1]) + 30)
            for tr in cor:
                tr.data = np.ma.filled(tr.data, 0).astype(np.float32) if np.ma.isMaskedArray(tr.data) \
                    else tr.data.astype(np.float32)
                tr.stats.pop("units", None)
            cor.write(str(out / "corrected.mseed"), format="MSEED", encoding="FLOAT32")
            res.products += [dict(product_type="raw_counts_mseed", path=str(out / "raw_counts.mseed")),
                             dict(product_type="corrected_mseed", path=str(out / "corrected.mseed"))]
        stations.to_csv(out / "stations.csv")
        res.metrics.to_csv(out / "metrics.csv", index=False)
        res.onsets.to_csv(out / "onsets.csv", index=False)
        if plots:
            for kind in ("pressure", "seismic_Z"):
                fc = p["pressure_highpass"] if kind == "pressure" else p["seismic_highpass"]
                f = plot_record_section(st, stations, t0, kind, title, out / "plots" / f"record_section_{kind}.png",
                                        window=p["plot_window"], fc=fc, onsets=res.onsets)
                if f:
                    res.products.append(dict(product_type=f"record_section_{kind}", path=str(f)))
            for sta in sorted({tr.stats.station for tr in st}):
                f = plot_station(st, sta, t0, f"{title}\n{sta}", out / "plots" / f"station_{sta}.png",
                                 window=p["plot_window"])
                if f:
                    res.products.append(dict(product_type="station_waveform_spectrogram", path=str(f), station=sta))
        manifest = dict(event_id=eid, run_id=run_id, products_version=PRODUCTS_VERSION,
                        catalog_time=str(t0), era=ev.raw.get("era"), data_source=res.data_source,
                        stationxml=str(ev.paths.get("stationxml", "")), params=p, detected=det,
                        n_raw=res.n_raw, n_corrected=res.n_corrected, warnings=res.warnings,
                        created_utc=str(UTCDateTime()))
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
        res.products.append(dict(product_type="manifest", path=str(out / "manifest.json")))
    except Exception as exc:
        res.status, res.error = "error", f"{type(exc).__name__}: {exc}"
    return res
