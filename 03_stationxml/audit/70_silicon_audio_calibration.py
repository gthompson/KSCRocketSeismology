"""Calibrate the Silicon Audio accelerometer (DG.B23.01.CL?, 2026) against the co-located SmartSolo
(1R.B23..DP?) on Artemis II, and check XA.MTEGL.01.CN? (2022) against S39A1 on two launches.

Kelunji-format recorder: 419430.4 counts/V x gain (settings.ss: gain x8 at B23 in 2026; x1 at the
2026-01 huddle). Output is proportional to acceleration: |counts / SmartSolo velocity| grows as f.
Writes audit/silicon_audio_calibration.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read, read_inventory
from scipy.signal import csd, welch

HERE = Path(__file__).resolve().parent
INV = read_inventory(str(HERE.parent / "KSC.xml"))
T0 = UTCDateTime("2026-04-01T22:35:12")   # Artemis II
rows = []
for cha in "ZNE":
    a = read(f"/Volumes/KSCGTdownld/SDS/2026/1R/B23/DP{cha}.D/1R.B23.--.DP{cha}.D.2026.091").slice(T0 - 100, T0 + 500).merge()[0]
    b = read(f"/Volumes/KSCGTdownld/SDS/2026/DG/B23/CL{cha}.D/DG.B23.01.CL{cha}.D.2026.091").slice(T0 - 100, T0 + 500).merge()[0]
    a.remove_response(INV, output="ACC", pre_filt=[0.3, 0.6, 100, 200])
    b.data = b.data.astype(float)
    t1 = max(a.stats.starttime, b.stats.starttime) + 1
    a.trim(t1, t1 + 550); b.trim(t1, t1 + 550)
    n = min(a.stats.npts, b.stats.npts)
    x, y = a.data[:n] - a.data[:n].mean(), b.data[:n] - b.data[:n].mean()
    f, Pxy = csd(x, y, fs=a.stats.sampling_rate, nperseg=4096)
    _, Pxx = welch(x, fs=a.stats.sampling_rate, nperseg=4096)
    _, Pyy = welch(y, fs=a.stats.sampling_rate, nperseg=4096)
    coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    H = np.abs(Pxy) / Pxx                                  # counts per (m/s^2)
    good = (f >= 1) & (f <= 20) & (coh > 0.95)
    rows.append(dict(channel=f"DG.B23.01.CL{cha}", n_freqs=int(good.sum()),
                     counts_per_mps2_median=float(np.median(H[good])) if good.any() else np.nan,
                     p16=float(np.percentile(H[good], 16)) if good.any() else np.nan,
                     p84=float(np.percentile(H[good], 84)) if good.any() else np.nan))
df = pd.DataFrame(rows)
df["V_per_mps2_at_gain8"] = df.counts_per_mps2_median / (419430.4 * 8)
df.to_csv(HERE / "silicon_audio_calibration.csv", index=False)
print(df.to_string(index=False))
