"""Which SDS channel-days (2016-2022 remastered SDS and 2026 SDS) have no response in a StationXML?

    python 03_stationxml/audit/30_check_coverage.py 03_stationxml/KSC.xml [old.xml]

A day counts as covered if a channel epoch with the same NSLC is active at 12:00 UTC (or at the
start/end of the day for epochs that begin/end that day). Writes coverage_<xml stem>.csv.
"""
import os
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from obspy import UTCDateTime, read_inventory

HERE = Path(__file__).resolve().parent
ROOTS = ["/Volumes/classdata/remastered/SDS_KSC", "/Volumes/KSCGTdownld/SDS"]


def sds_days():
    out = defaultdict(set)
    L = lambda p: [x for x in sorted(os.listdir(p)) if not x.startswith(".")]
    for root in ROOTS:
        for y in [d for d in L(root) if d.isdigit()]:
            for net in L(f"{root}/{y}"):
                if net == "DG":                  # MSFC instruments, not part of this network
                    continue
                for sta in L(f"{root}/{y}/{net}"):
                    for cd in L(f"{root}/{y}/{net}/{sta}"):
                        if cd.startswith(("L", "SOH", "V")):
                            continue
                        for f in L(f"{root}/{y}/{net}/{sta}/{cd}"):
                            p = f.split(".")
                            if len(p) >= 7:
                                out[(p[0], p[1], '' if p[2] == '--' else p[2], p[3])].add((int(p[5]), int(p[6])))
    return out


def coverage(xml):
    inv = read_inventory(xml)
    epochs = defaultdict(list)
    for n in inv:
        for s in n:
            for c in s:
                epochs[(n.code, s.code, c.location_code, c.code)].append(
                    (c.start_date, c.end_date or UTCDateTime(2600, 1, 1)))
    rows = []
    for key, days in sorted(sds_days().items()):
        cov = 0
        for y, j in days:
            d0 = UTCDateTime(year=y, julday=j)
            if any(a < d0 + 86400 and b > d0 for a, b in epochs.get(key, [])):
                cov += 1
        rows.append(dict(seed_id=".".join(key), sds_days=len(days), covered=cov, uncovered=len(days) - cov,
                         first=str(UTCDateTime(year=min(days)[0], julday=min(days)[1]).date),
                         last=str(UTCDateTime(year=max(days)[0], julday=max(days)[1]).date)))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    for xml in sys.argv[1:]:
        df = coverage(xml)
        df.to_csv(HERE / f"coverage_{Path(xml).stem}.csv", index=False)
        print(f"{xml}: {df.sds_days.sum()} SDS channel-days, {df.uncovered.sum()} without a response "
              f"({(df.uncovered > 0).sum()} of {len(df)} channels)")
        print(df[df.uncovered > 0].to_string(index=False))
