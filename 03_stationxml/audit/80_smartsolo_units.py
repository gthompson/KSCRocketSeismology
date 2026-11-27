"""Part 2 (below the first table): DG Certimus at B12 and B07 against the co-located SmartSolo.

Are the 2026 SmartSolo miniSEED values mV or uV of geophone output?

Compare each SmartSolo DP? (velocity through the KSC.xml response, which assumes 1 count = 1 mV)
with the co-located Centaur Trillium (B01, B14, B20, B24) on Artemis II: amplitude ratio and
coherence of the vertical, 5-20 Hz, where both sensors are flat. A ratio near 1 means mV;
near 1000 means the KSC.xml response would read 1000x high, i.e. the data are in uV.
Writes audit/smartsolo_units.csv.
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read, read_inventory
from scipy.signal import csd, welch

HERE = Path(__file__).resolve().parent
INV = read_inventory(str(HERE.parent / "KSC.xml"))
T0 = UTCDateTime("2026-04-01T22:35:12")
SDS = "/Volumes/KSCGTdownld/SDS/2026/1R"
rows = []
for sta in ["B01", "B03", "B14", "B20", "B24"]:
    fs_ = glob.glob(f"{SDS}/{sta}/DPZ.D/*.2026.091"); ft = glob.glob(f"{SDS}/{sta}/DHZ.D/*.2026.091")
    if not fs_ or not ft:
        continue
    a = read(fs_[0]).slice(T0 - 100, T0 + 500).merge()[0]
    b = read(ft[0]).slice(T0 - 100, T0 + 500).merge()[0]
    a.stats.location = "" if a.stats.location == "--" else a.stats.location
    for tr in (a, b):
        tr.data = tr.data.astype(float)
        tr.remove_response(INV, output="VEL", pre_filt=[0.5, 1, 40, 45])
    b.resample(a.stats.sampling_rate) if b.stats.sampling_rate != a.stats.sampling_rate else None
    t1 = max(a.stats.starttime, b.stats.starttime) + 2
    a.trim(t1, t1 + 550); b.trim(t1, t1 + 550)
    n = min(a.stats.npts, b.stats.npts); x, y = b.data[:n], a.data[:n]
    f, Pxy = csd(x, y, fs=a.stats.sampling_rate, nperseg=4096)
    _, Pxx = welch(x, fs=a.stats.sampling_rate, nperseg=4096); _, Pyy = welch(y, fs=a.stats.sampling_rate, nperseg=4096)
    coh = np.abs(Pxy) ** 2 / (Pxx * Pyy); H = np.abs(Pxy) / Pxx
    band = (f >= 5) & (f <= 20)
    good = band & (coh > 0.8)
    rows.append(dict(station=sta, n_good_freqs=int(good.sum()), median_coherence_5_20Hz=float(np.median(coh[band])),
                     smartsolo_over_trillium=float(np.median(H[good])) if good.any() else np.nan,
                     peak_ratio_5_20Hz=float(np.abs(a.copy().filter("bandpass", freqmin=5, freqmax=20).data).max()
                                             / np.abs(b.copy().filter("bandpass", freqmin=5, freqmax=20).data).max())))
df = pd.DataFrame(rows)
df.to_csv(HERE / "smartsolo_units.csv", index=False)
print(df.to_string(index=False))

# Part 2: Certimus (DG.*.1L.CH?) vs SmartSolo DP? at the same site, through KSC.xml
rows = []
for sta, chans in (("B12", "ZNE"), ("B07", "Z")):
    for c in chans:
        fa = glob.glob(f"{SDS}/{sta}/DP{c}.D/*.2026.091"); fb = glob.glob(f"/Volumes/KSCGTdownld/SDS/2026/DG/{sta}/CH{c}.D/*.2026.091")
        if not fa or not fb:
            continue
        a = read(fa[0]).slice(T0 - 100, T0 + 500).merge()[0]; b = read(fb[0]).slice(T0 - 100, T0 + 500).merge()[0]
        a.stats.location = ""
        for tr in (a, b):
            tr.data = tr.data.astype(float); tr.remove_response(INV, output="VEL", pre_filt=[0.5, 1, 40, 45])
        if b.stats.sampling_rate != a.stats.sampling_rate:
            a.resample(b.stats.sampling_rate)
        t1 = max(a.stats.starttime, b.stats.starttime) + 2
        a.trim(t1, t1 + 550); b.trim(t1, t1 + 550)
        n = min(a.stats.npts, b.stats.npts); x, y = b.data[:n], a.data[:n]
        fs = b.stats.sampling_rate
        f, Pxy = csd(x, y, fs=fs, nperseg=4096); _, Pxx = welch(x, fs=fs, nperseg=4096); _, Pyy = welch(y, fs=fs, nperseg=4096)
        coh = np.abs(Pxy) ** 2 / (Pxx * Pyy); H = np.abs(Pxy) / Pxx
        good = (f >= 5) & (f <= 20) & (coh > 0.8)
        rows.append(dict(station=sta, component=c, n_good_freqs=int(good.sum()),
                         smartsolo_over_certimus=float(np.median(H[good])) if good.any() else np.nan))
d2 = pd.DataFrame(rows)
d2.to_csv(HERE / "certimus_vs_smartsolo.csv", index=False)
print(d2.to_string(index=False))
