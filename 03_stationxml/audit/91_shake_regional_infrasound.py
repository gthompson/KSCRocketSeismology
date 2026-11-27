"""Did the Miami-area Raspberry Shakes/Booms (AM.R095E, R17FC, RCC6E HDF; RC57A, R976A EHZ) record KSC
launches at ~300 km?

Distances from LC-39A (Raspberry Shake FDSN station service, 2022 epochs): R095E 298 km, R17FC 303,
R976A 301, RC57A 291, RCC6E 297. Stratospheric/tropospheric infrasound (celerity 0.26-0.35 km/s)
arrives 830-1170 s after launch.

Test: 0.5-5 Hz, 20 s RMS envelope. SNR = max envelope in the expected window over the median envelope
in -600..-30 s. Null distribution: the same statistic at the same time of day on days -3, -2, +2, +3
(launch days excluded). Writes shake_regional_infrasound.csv.
"""
import importlib.util
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import UTCDateTime

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ult", HERE / "90_unmatched_launch_test.py")
ult = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ult)
warnings.filterwarnings("ignore")

DIST_KM = {"R095E": 298, "R17FC": 303, "R976A": 301, "RC57A": 291, "RCC6E": 297}
CHANS = ["AM.R095E.00.HDF", "AM.R17FC.00.HDF", "AM.RCC6E.00.HDF", "AM.RC57A.00.EHZ", "AM.R976A.00.EHZ"]
ult.NOISE, ult.SIGNAL = (-600.0, -30.0), (-30.0, 1400.0)


def stat(sid, t0):
    tr = ult.get(sid, t0)
    if tr is None:
        return np.nan, np.nan
    tr = tr.copy()
    tr.data = tr.data.astype(float)
    if np.mean(tr.data == 0) > 0.01:          # gaps were merged with zeros
        return np.nan, np.nan
    tr.detrend("demean")
    tr.taper(0.02)
    tr.filter("bandpass", freqmin=0.5, freqmax=5.0, corners=4, zerophase=True)
    t = tr.times(reftime=t0)
    k = int(20 * tr.stats.sampling_rate)
    env = np.sqrt(np.convolve(tr.data ** 2, np.ones(k) / k, "same"))
    km = DIST_KM[sid.split(".")[1]]
    w = (t >= km / 0.35) & (t <= km / 0.26)
    n = (t >= -600) & (t < -30)
    if w.sum() < 0.9 * (km / 0.26 - km / 0.35) * tr.stats.sampling_rate or n.sum() < 400 * tr.stats.sampling_rate:
        return np.nan, np.nan
    i = np.argmax(np.where(w, env, 0))
    return float(env[i] / np.median(env[n])), float(t[i])


def main():
    df = pd.read_csv(HERE / "unmatched_launch_test.csv")
    launch_days = {str(UTCDateTime(t).date) for t in df.time}
    rows = []
    for r in df.itertuples():
        t0 = UTCDateTime(r.time)
        for sid in CHANS:
            if sid not in df or pd.isna(df.loc[r.Index, sid]):
                continue
            snr, tp = stat(sid, t0)
            nulls = []
            for dd in (-3, -2, 2, 3):
                tn = t0 + dd * 86400
                if str(tn.date) not in launch_days:
                    nulls.append(stat(sid, tn)[0])
            rows.append(dict(time=r.time, event_id=r.event_id, seed_id=sid, snr=snr, t_arrival=tp,
                             celerity=DIST_KM[sid.split(".")[1]] / tp if tp == tp and tp > 0 else np.nan,
                             null_max=np.nanmax(nulls) if np.isfinite(nulls).any() else np.nan,
                             ref_snr_S39A1_HDF=df.loc[r.Index, "1R.S39A1.00.HDF"]))
            print(rows[-1], flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "shake_regional_infrasound.csv", index=False)
    for sid, g in out.groupby("seed_id"):
        g = g.dropna(subset=["snr"])
        allnull = g.null_max.dropna()
        thr = 3.0
        print(f"{sid}: {len(g)} launches, SNR>{thr} on {(g.snr > thr).sum()}; "
              f"null days with max>{thr}: {(allnull > thr).sum()}/{len(allnull)}; "
              f"detections: {g[g.snr > thr][['time', 'snr', 't_arrival', 'null_max']].round(1).values.tolist()}")


if __name__ == "__main__":
    main()
