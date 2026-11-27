"""Do the unmatched/ channels of 2022 record KSC launches?

The user asked (2026-11-26) whether the "possibly live" Centaur inputs (BCHH4 HD3, S39A3 HD2/HD3)
and the 2022 Raspberry Shakes in SDS_KSC/unmatched/ (R095E, R17FC, R976A, RC57A, RCC6E) were at KSC.
The Shakes were sometimes at KSC and sometimes at USF; the only test is whether they record launches
that the KSC stations record.

For every catalog launch in 2022 with data, each channel gets SNR = peak |x| in -30..+300 s over the
peak in -330..-30 s, high-passed at 1 Hz. Reference channels: S39A1 HDF/HHZ and BCHH2 HD4 (and the
same-station sibling for the Centaur inputs). Writes unmatched_launch_test.csv.

    PYTHONPATH=<worktree>/ksclib/src python 03_stationxml/audit/90_unmatched_launch_test.py
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import Stream, UTCDateTime, read

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ksclib" / "src"))
from ksclib import catalog_events as ce  # noqa: E402

warnings.filterwarnings("ignore")
ROOTS = ["/Volumes/classdata/remastered/SDS_KSC", "/Volumes/classdata/remastered/SDS_KSC/unmatched"]
SIGNAL, NOISE = (-30.0, 300.0), (-330.0, -30.0)

TARGETS = {  # seed id -> (first, last day with data)
    "1R.BCHH4.00.HD3": ("2022-05-26", "2022-12-03"),
    "1R.S39A3.00.HD2": ("2022-04-01", "2022-05-26"),
    "1R.S39A3.00.HD3": ("2022-04-01", "2022-05-26"),
    "AM.R095E.00.EHZ": ("2022-06-30", "2022-11-26"), "AM.R095E.00.HDF": ("2022-06-30", "2022-11-26"),
    "AM.R17FC.00.EHZ": ("2022-06-30", "2022-11-27"), "AM.R17FC.00.HDF": ("2022-06-30", "2022-11-27"),
    "AM.R976A.00.EHZ": ("2022-09-23", "2022-11-27"),
    "AM.RC57A.00.EHZ": ("2022-06-30", "2022-11-27"),
    "AM.RCC6E.00.EHZ": ("2022-06-30", "2022-11-26"), "AM.RCC6E.00.HDF": ("2022-06-30", "2022-11-26"),
}
REFS = ["1R.S39A1.00.HDF", "1R.S39A1.00.HHZ", "1R.BCHH2.00.HD4", "1R.BCHH4.00.HD2", "1R.S39A3.00.HDF"]


def get(sid, t0):
    n, s, l, c = sid.split(".")
    st = Stream()
    for t in sorted({(t0 + NOISE[0] - 20).date, (t0 + SIGNAL[1] + 20).date}):
        t = UTCDateTime(t)
        for root in ROOTS:
            p = Path(f"{root}/{t.year}/{n}/{s}/{c}.D/{n}.{s}.{l or '--'}.{c}.D.{t.year}.{t.julday:03d}")
            if not p.exists() and not l:
                p = Path(str(p).replace("..", ".--."))
            if p.exists():
                try:
                    st += read(str(p), starttime=t0 + NOISE[0] - 20, endtime=t0 + SIGNAL[1] + 20)
                except Exception:
                    pass
    if not st:
        return None
    st.merge(fill_value=0)
    return st[0]


def snr(tr, t0):
    tr = tr.copy()
    tr.data = tr.data.astype(float)
    tr.detrend("demean")
    tr.taper(0.02)
    tr.filter("highpass", freq=1.0, corners=4, zerophase=True)
    t = tr.times(reftime=t0)
    a = np.abs(tr.data)
    s = (t >= SIGNAL[0]) & (t <= SIGNAL[1])
    n = (t >= NOISE[0]) & (t < NOISE[1])
    if s.sum() < 0.9 * 330 * tr.stats.sampling_rate or n.sum() < 0.5 * 300 * tr.stats.sampling_rate:
        return np.nan
    return float(a[s].max() / max(a[n].max(), 1e-12))


def main():
    ens = ce.load_ensemble(REPO / "07_ensemble_paper" / "ensemble.yaml")
    cat = ce.load_catalog(ens, extra=False)
    cat = cat[(cat.event_time_utc >= "2022-03-24") & (cat.event_time_utc < "2022-12-05")]
    rows = []
    for r in cat.itertuples():
        t0 = UTCDateTime(str(r.event_time_utc))
        row = dict(event_id=r.event_id, time=str(t0)[:19])
        for sid, (a, b) in TARGETS.items():
            if UTCDateTime(a) <= t0 < UTCDateTime(b) + 86400:
                tr = get(sid, t0)
                row[sid] = snr(tr, t0) if tr is not None else np.nan
        for sid in REFS:
            tr = get(sid, t0)
            row[sid] = snr(tr, t0) if tr is not None else np.nan
        rows.append(row)
        print(row["time"], {k: round(v, 1) for k, v in row.items() if isinstance(v, float) and not np.isnan(v)},
              flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "unmatched_launch_test.csv", index=False)
    ref = df[["1R.S39A1.00.HDF", "1R.BCHH2.00.HD4"]].max(axis=1)
    print("\nlaunches with a reference SNR > 5:", (ref > 5).sum())
    for sid in TARGETS:
        m = df[sid].notna() & (ref > 5) if sid in df else []
        if sid in df and m.sum():
            x = df.loc[m, sid]
            print(f"{sid}: n={m.sum()} median SNR {x.median():.1f}, SNR>3 on {(x > 3).sum()}, "
                  f"max {x.max():.1f}")


if __name__ == "__main__":
    main()
