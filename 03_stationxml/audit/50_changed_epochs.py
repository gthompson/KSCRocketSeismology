"""Every channel epoch of the sheet, with old (2025 KSC.xml) and new sensitivity and the evidence.

Writes 03_stationxml/audit/changed_epochs.csv (rows whose response, epoch or inclusion changed).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read_inventory

HERE = Path(__file__).resolve().parent
OLD = read_inventory("/Volumes/haldata/KSC/station_metadata/KSC.xml")
NEW = read_inventory(str(HERE.parent / "KSC.xml"))
sheet = pd.read_excel(HERE.parent / "ksc_stations_master_v3.xlsx", sheet_name="channel_epochs",
                      dtype={"location": str}).fillna({"end": "", "change": "", "evidence": "", "notes": ""})


def sens(inv, sid, t):
    try:
        r = inv.get_response(sid, t)
        return r.instrument_sensitivity.value, r.instrument_sensitivity.input_units
    except Exception:
        return np.nan, ""


rows = []
for r in sheet.itertuples():
    loc = "" if r.location in ("--", "nan") else r.location
    sid = f"{r.network}.{r.station}.{loc}.{r.channel}"
    t0 = UTCDateTime(r.start)
    t1 = UTCDateTime(r.end) if r.end else t0 + 86400
    tm = t0 + (t1 - t0) / 2
    so, uo = sens(OLD, sid, tm)
    sn, un = sens(NEW, sid, tm) if r.include else (np.nan, "")
    ratio = sn / so if so and not np.isnan(so) and not np.isnan(sn) else np.nan
    changed = bool(r.change) or not r.include or not (np.isclose(ratio, 1, rtol=0.01) if not np.isnan(ratio) else False)
    rows.append(dict(seed_id=sid, start=r.start, end=r.end, datalogger=r.datalogger, sensor=r.sensor,
                     sensor_serial=r.sensor_serial, vpp=r.vpp, include=r.include, status=r.status,
                     old_counts_per_unit=so, new_counts_per_unit=sn, units=un or uo, new_over_old=ratio,
                     change=r.change, evidence=r.evidence, notes=r.notes, changed=changed))
df = pd.DataFrame(rows)
df[df.changed].drop(columns="changed").to_csv(HERE / "changed_epochs.csv", index=False)
print(f"{df.changed.sum()} of {len(df)} channel epochs changed; written to changed_epochs.csv")
g = df[df.changed & df.new_over_old.notna() & ~np.isclose(df.new_over_old, 1, rtol=0.01)]
print(g.groupby(["seed_id"]).new_over_old.first().round(4).to_string())
