"""Raw-count launch peaks and ambient levels for every 2016-2022 1R channel (gain audit input).

For each catalog event 2016-2022 and every 1R channel in the remastered SDS:
  * pressure channels (?D?): peak |counts| high-passed at 0.5 Hz (as notebooks 15/20),
  * vertical seismic channels (?HZ, EHZ): peak |counts| band-passed 5-20 Hz (where both the
    2 Hz L-22 and the Trillium Compact are flat) and high-passed at 1 Hz,
in the window -30..+300 s from the catalog time, and the same over the 330 s before (noise).
Ambient: night-time (05-07 UTC) RMS counts in 0.15-0.35 Hz for pressure channels on chosen days.

Outputs (03_stationxml/audit/):  launch_peaks_counts_2016_2022.csv, ambient_counts.csv
Run:  PYTHONPATH=<repo>/ksclib/src python 03_stationxml/audit/10_measure_launch_peaks.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy.clients.filesystem.sds import Client

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ksclib" / "src"))
from ksclib import catalog_events as ce  # noqa: E402

warnings.filterwarnings("ignore")
SDS = Client("/Volumes/classdata/remastered/SDS_KSC")
SIGNAL, NOISE = (-30.0, 300.0), (-330.0, -30.0)


def _measure(tr, t0, kind):
    tr = tr.copy()
    tr.data = tr.data.astype(float)
    tr.detrend("demean")
    tr.taper(0.02)
    out = {}
    bands = {"pressure": {"hp05": ("highpass", dict(freq=0.5))},
             "seismic": {"bp5_20": ("bandpass", dict(freqmin=5.0, freqmax=20.0)),
                         "hp1": ("highpass", dict(freq=1.0))}}[kind]
    for name, (ftype, kw) in bands.items():
        x = tr.copy()
        x.filter(ftype, corners=4, zerophase=True, **kw)
        t = x.times(reftime=t0)
        a = np.abs(x.data)
        s = (t >= SIGNAL[0]) & (t <= SIGNAL[1])
        n = (t >= NOISE[0]) & (t < NOISE[1])
        if s.sum() < 0.9 * (SIGNAL[1] - SIGNAL[0]) * tr.stats.sampling_rate:
            return None
        out[f"peak_{name}"] = float(a[s].max())
        out[f"noise_{name}"] = float(a[n].max()) if n.sum() > 0.5 * (NOISE[1] - NOISE[0]) * tr.stats.sampling_rate else np.nan
        out[f"t_peak_{name}"] = float(t[s][np.argmax(a[s])])
    return out


def _has_data(t0):
    import glob
    for t in (t0 + NOISE[0] - 20, t0 + SIGNAL[1] + 20):
        if not glob.glob(f"/Volumes/classdata/remastered/SDS_KSC/{t.year}/1R/*/*/1R.*.{t.year}.{t.julday:03d}"):
            return False
    return True


def _one_event(r):
    rows = []
    t0 = UTCDateTime(r["event_time_utc"])
    if not _has_data(t0):
        return rows
    try:
        st = SDS.get_waveforms("1R", "*", "*", "*", t0 + NOISE[0] - 20, t0 + SIGNAL[1] + 20)
    except Exception:
        return rows
    st.merge(fill_value=0)
    if True:
        for tr in st:
            cha = tr.stats.channel
            kind = "pressure" if cha[1] == "D" else ("seismic" if cha[1] in "HP" and cha[2] == "Z" else None)
            if kind is None or tr.stats.npts < 100 * tr.stats.sampling_rate:
                continue
            m = _measure(tr, t0, kind)
            if m:
                rows.append(dict(event_id=r["event_id"], time=str(t0)[:19], vehicle=r.get("vehicle"),
                                 pad=r.get("pad_code") or r.get("pad"),
                                 seed_id=tr.id, station=tr.stats.station, location=tr.stats.location,
                                 channel=cha, sampling_rate=tr.stats.sampling_rate, kind=kind, **m))
    print(f"{r['event_id']} {str(t0)[:16]} {len(st)} traces", flush=True)
    return rows


def launch_peaks(nproc=8):
    from multiprocessing import Pool
    ens = ce.load_ensemble(REPO / "07_ensemble_paper" / "ensemble.yaml")
    cat = ce.load_catalog(ens, extra=False)
    cat = cat[(cat.event_time_utc >= "2016-01-01") & (cat.event_time_utc < "2023-01-01")]
    recs = [{k: (str(v) if k == "event_time_utc" else v) for k, v in r.items()} for r in cat.to_dict("records")]
    with Pool(nproc) as pool:
        out = pool.map(_one_event, recs, chunksize=1)
    return pd.DataFrame([x for rows in out for x in rows])


def band_rms(net, sta, cha, t0, t1, band=(0.15, 0.35)):
    try:
        st = SDS.get_waveforms(net, sta, "*", cha, t0 - 300, t1 + 300)
    except Exception:
        return np.nan
    if not st:
        return np.nan
    st.merge(fill_value=0)
    tr = st[0]
    if tr.stats.npts < 0.8 * (t1 - t0 + 600) * tr.stats.sampling_rate:
        return np.nan
    tr.data = tr.data.astype(float)
    tr.detrend("demean")
    tr.taper(0.05)
    tr.filter("bandpass", freqmin=band[0], freqmax=band[1], corners=4, zerophase=True)
    tr.trim(t0, t1)
    return float(np.sqrt(np.mean(tr.data ** 2)))


def ambient():
    jobs = []
    # 2016 beach house: every recorded day (sensor 295 swap between DD1 and DD2 on 2016-03-04)
    for day in pd.date_range("2016-02-24", "2016-10-05"):
        for cha in ("DD1", "DD2", "DD3"):
            jobs.append(("BCHH", cha, day))
    # 2021-10-16 RBLAB deployment (Centaur serials 166/268/383) with the beach-house references
    for day in pd.date_range("2021-10-15", "2021-10-18"):
        for sta, chans in {"RB166": ["HD1", "HD2", "HD3"], "RB268": ["DDF"], "RB383": ["HD1", "HD2", "HD3"],
                           "BCHH1": ["DD1", "DD2"], "BCHH2": ["DD4", "DD5", "DD6", "DD7", "DD8", "DD9"]}.items():
            for cha in chans:
                jobs.append((sta, cha, day))
    # 2022 beach house and S39A
    for day in ("2022-04-05", "2022-05-10", "2022-06-15", "2022-08-15", "2022-11-01"):
        for sta, chans in {"BCHH2": ["HD4", "HD5", "HD6", "HD7", "HD8", "HD9"], "BCHH3": ["HDF"],
                           "BCHH4": ["HD2", "HDF"], "S39A1": ["HDF"], "S39A2": ["HDF"], "S39A3": ["HDF"]}.items():
            for cha in chans:
                jobs.append((sta, cha, pd.Timestamp(day)))
    rows = []
    for sta, cha, day in jobs:
        t0 = UTCDateTime(day.strftime("%Y-%m-%d") + "T05:00:00")
        rows.append(dict(station=sta, channel=cha, day=day.strftime("%Y-%m-%d"),
                         rms_counts=band_rms("1R", sta, cha, t0, t0 + 7200)))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = HERE
    if not (out / "ambient_counts.csv").exists():
        amb = ambient()
        amb.to_csv(out / "ambient_counts.csv", index=False)
        print("ambient done", len(amb), flush=True)
    pk = launch_peaks()
    pk.to_csv(out / "launch_peaks_counts_2016_2022.csv", index=False)
    print("peaks done", len(pk))
