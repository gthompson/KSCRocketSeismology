"""Characterise the SDS_KSC/unmatched day files (data the remastering could not match to metadata).

For each unmatched NSLC: days, first/last, sample rate, and for a sample day the median absolute
counts of the channel and of the matched channels at the same station that day (to see if it is live
and which sensor it resembles). Writes audit/unmatched_sds.csv.
"""
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import read

HERE = Path(__file__).resolve().parent
ROOT = "/Volumes/classdata/remastered/SDS_KSC"

files = defaultdict(list)
for dp, _, fs in os.walk(f"{ROOT}/unmatched"):
    for f in fs:
        if not f.startswith("."):
            p = f.split(".")
            files[tuple(p[:4])].append((int(p[5]), int(p[6]), os.path.join(dp, f)))


def stats(path):
    try:
        st = read(path, headonly=False)
    except Exception as e:
        return dict(err=str(e)[:60])
    st.merge(fill_value=None)
    d = np.concatenate([np.asarray(tr.data, float) for tr in st])
    d = d - np.median(d)
    return dict(sr=st[0].stats.sampling_rate, npts=d.size, mad=float(np.median(np.abs(d))),
                p999=float(np.percentile(np.abs(d), 99.9)), const=float(np.mean(np.diff(d) == 0)))


rows = []
for key, days in sorted(files.items()):
    days.sort()
    y, j, path = days[len(days) // 2]
    s = stats(path)
    # matched channels at the same station that day
    sib = {}
    sd = f"{ROOT}/{y}/{key[0]}/{key[1]}"
    if os.path.isdir(sd):
        for cd in sorted(os.listdir(sd)):
            f = f"{sd}/{cd}/{key[0]}.{key[1]}.{key[2]}.{cd[:3]}.D.{y}.{j:03d}"
            if os.path.exists(f):
                sib[cd[:3]] = round(stats(f).get("mad", np.nan), 1)
    rows.append(dict(seed_id=".".join(key), ndays=len(days), first=f"{days[0][0]}.{days[0][1]:03d}",
                     last=f"{days[-1][0]}.{days[-1][1]:03d}", sample_day=f"{y}.{j:03d}", **s,
                     matched_siblings_mad=sib))
df = pd.DataFrame(rows)
df.to_csv(HERE / "unmatched_sds.csv", index=False)
pd.set_option("display.width", 250)
print(df.to_string(index=False))
