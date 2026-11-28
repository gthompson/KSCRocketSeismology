"""Corrected KSC station sheet (v3): one row per NSLC channel epoch, 2016 to 2026.

Inputs (read-only):
  /Volumes/haldata/KSC/station_metadata/ksc_stations_master_v2.xlsx   2016-2022 master sheet
  2026 Centaur response files (Centaur-written StationXML, one per configuration change)
  2026 SDS (/Volumes/KSCGTdownld/SDS) for channel lists and day ranges
  Box spreadsheet KSC_seismic_network_2016_2022.xls (SDS2026_metadata, gem_gps_data, artemis2)
  2026_ingest_service_runs/config/{gem_mapping_artemis2_example,smartsolo_mapping_artemis2}.csv
  audit decisions: AUDIT below (evidence in 03_stationxml/audit/)

Output: 03_stationxml/ksc_stations_master_v3.xlsx
  channel_epochs  one row per channel epoch, with datalogger, input range (vpp), sensor, gains,
                  status, include flag, response source and the reason for any change
  changes         rows whose response or epoch differs from the 2016-2022 KSC.xml / master v2
  README          column meanings

Every Centaur row carries an explicit vpp (1 or 40); build_ksc_stationxml.py refuses anything else.
"""
from __future__ import annotations

import datetime as dt
import glob
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read, read_inventory

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MASTER_V2 = "/Volumes/haldata/KSC/station_metadata/ksc_stations_master_v2.xlsx"
BOX_XLS = Path.home() / ("Library/CloudStorage/Box-Box/thompsong/3_Project_Documents/NASAprojects/"
                         "201602_Rocket_Seismology/writing/KSC_seismic_network_2016_2022.xls")
SDS2026 = "/Volumes/KSCGTdownld/SDS/2026"
CENTAUR_DIRS_2026 = sorted(glob.glob("/Volumes/KSCGTdownld/2026*_service/00_download/Centaur*/responses")
                           + glob.glob("/Volumes/haldata/KSC/2026*/responses"))
OUT = HERE / "ksc_stations_master_v3.xlsx"

# ---------------------------------------------------------------------------------------------
# Sensor and datalogger catalogue
# ---------------------------------------------------------------------------------------------
INFRABSU_V_PER_PA = 4.6e-5          # infraBSU 0.5" (infraBSU_21s_0.5inch.xml)
TRILLIUM_V_PER_MPS = 754.3          # Trillium Compact 120 s Posthole
# Sercel/Mark L-22D 2 Hz, 2200 Ohm coil. NRL gives 62.95 V/(m/s) with a 10854 Ohm damping shunt; 88 is
# the unshunted generator constant. At RT130 gain 32 the geophone/Trillium launch ratio is 1.47 (median,
# IQR 1.29-1.93, 68 pairs; audit/T1_geophone_vs_trillium.csv) with 62.95, and 1.05 with 88. User chose
# 88 on 2026-11-25. The PAZ (poles, damping) is still the NRL shunted one; only the gain changed.
L22_V_PER_MPS = 88.0
SMARTSOLO_V_PER_MPS = 76.7          # SmartSolo IGU-16HR 5 Hz geophone (data harvested in mV)
# Silicon Audio accelerometer on a Kelunji-format recorder (MSFC unit; XA.MTEGL 2022, DG.B23 2026).
# 15 V/g: measured 1.51 (Z) and 1.57 (N) V/(m/s^2) against the B23 SmartSolo on Artemis II
# (audit/70_silicon_audio_calibration.py). Recorder: 419430.4 counts/V x gain (settings.ss).
SILICON_AUDIO_V_PER_MPS2 = 15.0 / 9.80665
KELUNJI_COUNTS_PER_V = 419430.4

# Filled from the audit (03_stationxml/audit/AUDIT_REPORT.md); see the evidence column of each row.
AUDIT = {
    "chaparral_V_per_Pa": 0.4,      # Chaparral M25 low gain; unclipped launches give 0.26-0.45 (audit T3)
    "sensor295_correction": 1 / 14.7,   # infraBSU 295 (2016 BCHH): DD1/DD2, DD3/DD2 median 14.7, 6 launches (T2)
    "sensor295_swap": "2016-03-04T20:00:00",   # 295 moved DD1->DD2: service gap 19:58-20:05 UTC (audit T2c)
    "rt130_gain": 32,               # RT130 preamp gain for the L-22 channels (CONFIG/*.par, T1)
    "rblab2021_vpp": None,          # RB166/RB268/RB383 infrasound (T4/T5)
    "dvel3_2020_vpp": "dead",       # DVEL3 2020-11-05..2020-12-11: infrasound SNR~1 on 5 launches, Trillium alive
}

SENSORS = {
    "infraBSU": dict(desc='infraBSU 0.5" infrasound sensor (Boise State)', manufacturer="Boise State University",
                     model="infraBSU 0.5in", units="Pa", sens=INFRABSU_V_PER_PA),
    "Chaparral": dict(desc="Chaparral Physics Model 25 infrasound microphone (low gain)",
                      manufacturer="Chaparral Physics", model="M25", units="Pa", sens=None),
    "TCP": dict(desc="Nanometrics Trillium Compact Posthole 120 s", manufacturer="Nanometrics",
                model="Trillium Compact Posthole 120s", units="m/s", sens=TRILLIUM_V_PER_MPS),
    "L-22": dict(desc="Sercel/Mark Products L-22D 2 Hz geophone", manufacturer="Sercel/Mark Products",
                 model="L-22D", units="m/s", sens=L22_V_PER_MPS),
    "Gem": dict(desc="Gem infrasound logger v1 (sensor + 16-bit logger, high gain)", manufacturer="Anderson/Boise State",
                model="Gem v1", units="Pa", sens=None),
    "SmartSolo": dict(desc="SmartSolo IGU-16HR 5 Hz 3C geophone node (harvested in mV)", manufacturer="DTCC",
                      model="SmartSolo IGU-16HR", units="m/s", sens=SMARTSOLO_V_PER_MPS),
}

COLUMNS = ["network", "station", "location", "channel", "start", "end", "latitude", "longitude", "elevation",
           "depth", "azimuth", "dip", "sample_rate", "datalogger", "datalogger_serial", "vpp", "datalogger_gain",
           "sensor", "sensor_serial", "sensor_V_per_unit", "sensitivity_correction", "units", "polarity",
           "status", "include", "response_source", "change", "evidence", "notes", "source_row"]


def expand(code: str):
    code = str(code)
    if len(code) <= 3:
        return [code]
    return [code[:2] + c for c in code[2:]]


def orient(cha):
    c = cha[-1]
    if c == "Z":
        return 0.0, -90.0
    if c in "N1":
        return 0.0, 0.0
    if c in "E2":
        return 90.0, 0.0
    return 0.0, 0.0        # pressure


def loc_code(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    s = str(x).strip()
    if s in ("", "--"):
        return "--"
    return f"{int(float(s)):02d}"


def iso(x):
    if x is None or (isinstance(x, float) and np.isnan(x)) or (isinstance(x, str) and not x):
        return ""
    return str(UTCDateTime(pd.Timestamp(x).to_pydatetime()))[:19]


# ---------------------------------------------------------------------------------------------
# 2016-2022 from master v2
# ---------------------------------------------------------------------------------------------
def rows_2016_2022():
    m = pd.read_excel(MASTER_V2, sheet_name="ksc_stations_master")
    rows = []
    for i, r in m.iterrows():
        for cha in expand(r.channel):
            az, dip = orient(cha)
            sensor = r.sensor if isinstance(r.sensor, str) else None
            dl = r.datalogger
            row = dict(network=r.network, station=r.station, location=loc_code(r.location), channel=cha,
                       start=iso(r.ondate), end=iso(r.offdate), latitude=r.lat, longitude=r.lon,
                       elevation=r.elev if pd.notna(r.elev) else 0.0, depth=r.depth if pd.notna(r.depth) else 0.0,
                       azimuth=az, dip=dip, sample_rate=float(r.fsamp), datalogger=dl,
                       datalogger_serial=str(r.das_serial) if pd.notna(r.das_serial) else "",
                       vpp=r.vpp if pd.notna(r.vpp) else np.nan, datalogger_gain=np.nan,
                       sensor=sensor or "", sensor_serial=str(r.sensor_serial) if pd.notna(r.sensor_serial) else "",
                       sensor_V_per_unit=np.nan, sensitivity_correction=1.0, units="", polarity="normal",
                       status="ok", include=True, response_source="", change="", evidence="",
                       notes=r.notes if isinstance(r.notes, str) else "", source_row=f"master_v2:{i + 2}")
            rows.append(row)
    df = pd.DataFrame(rows, columns=COLUMNS)

    # --- network-specific defaults ------------------------------------------------------------
    is_cent = df.datalogger == "Centaur"
    df.loc[is_cent & (df.sensor == "TCP"), "vpp"] = 40.0       # Trillium always on Sensor A at 40 Vpp
    df.loc[is_cent & (df.sensor == "TCP"), "evidence"] = (
        "Trillium on Centaur Sensor A at 40 Vpp in every Centaur-written response (BCHH1 2018, DVEL3 2019, "
        "BCHH3 2022, all 2026: preamp x0.9925)")
    df.loc[df.sensor == "infraBSU", "sensor_V_per_unit"] = INFRABSU_V_PER_PA
    df.loc[df.sensor == "Chaparral", "sensor_V_per_unit"] = AUDIT["chaparral_V_per_Pa"]
    df.loc[df.sensor == "TCP", "sensor_V_per_unit"] = TRILLIUM_V_PER_MPS
    df.loc[df.sensor == "L-22", "sensor_V_per_unit"] = L22_V_PER_MPS
    df.loc[df.sensor.isin(["infraBSU", "Chaparral"]), "units"] = "Pa"
    df.loc[df.sensor.isin(["TCP", "L-22"]), "units"] = "m/s"
    df.loc[is_cent, "response_source"] = "template:KSC.xml(haldata 2025-08-27) Centaur FIR, by sample rate"

    def setv(mask, **kw):
        for k, v in kw.items():
            if k in ("change", "evidence", "notes"):
                df.loc[mask, k] = [(a + "; " if a else "") + v for a in df.loc[mask, k]]
            else:
                df.loc[mask, k] = v

    S = lambda sta, cha=None, loc=None: (df.station == sta) & (True if cha is None else df.channel.isin(
        [cha] if isinstance(cha, str) else cha)) & (True if loc is None else df.location == loc)

    # --- RT130 + L-22 geophones -------------------------------------------------------------
    rt = df.datalogger == "RT130"
    setv(rt, evidence="L-22 constant 88 V/(m/s), not the NRL 62.95: geophone/Trillium launch ratio 1.47 -> 1.05 "
                      "(audit/T1_geophone_vs_trillium.csv); user decision 2026-11-25")
    setv(rt, datalogger_gain=float(AUDIT["rt130_gain"]), response_source="template:KSC.xml(haldata) RT130 FIR",
         change=f"RT130 gain 1 -> {AUDIT['rt130_gain']} (sensitivity x{AUDIT['rt130_gain']})",
         evidence="duringPASSCAL/CONFIG/network2018222..2019183.par and parfile.txt: gain 32 on every EH? channel; "
                  "launch peaks vs co-located Trillium BCHH1 DHZ (audit T1)")
    # --- DVEL1/DVEL2/RBLAB (2018) and DVEL3 (2019-20): notebook 15 --------------------------
    aud = pd.read_csv(HERE / "vpp_audit_DVEL_RBLAB.csv")
    for _, a in aud.iterrows():
        mask = S(a.station, a.channel)
        if pd.notna(a.proposed_vpp):
            setv(mask, vpp=float(a.proposed_vpp), change="vpp blank (built as 40) -> 1",
                 evidence="vpp_audit_DVEL_RBLAB.csv: " + a.evidence)
        else:
            setv(mask, status="dead", evidence="vpp_audit_DVEL_RBLAB.csv: " + str(a.evidence or "no signal"))
    # dead inputs on the same Centaur port as live 1 Vpp inputs share their setting (Sensor A = inputs 1-3)
    setv(S("DVEL1", ["DD3"]), vpp=1.0, change="vpp blank -> 1 (same Sensor A port as DD1/DD2); dead input")
    setv(S("RBLAB", ["DD1"]), vpp=1.0, change="vpp blank -> 1 (same Sensor A port as DD2/DD3); dead input")
    setv(S("DVEL1", ["DD4", "DD5", "DD6", "HD4", "HD5", "HD6"]), status="dead", include=False,
         change="excluded: Sensor B port, no signal and no evidence of its input range",
         evidence="vpp_audit_DVEL_RBLAB.csv: digitizer floor (~1.5 counts) at night, no launch signal")
    setv(S("DVEL1", ["HD1", "HD2", "HD3"]), vpp=1.0,
         change="vpp blank -> 1 (100 sps stream of DD1-DD3)",
         evidence="notebook 15: HD1-HD6 hold only the early hours of 2018-02-06, no launch; same inputs as DD1-DD3")
    # 2017 DVEL: no waveforms anywhere; vpp unknowable; its end date overlapped DVEL1-3
    setv(S("DVEL"), include=False, status="no_data",
         change="excluded: no SDS data for 2017-02-13..2018-12-31 and infrasound vpp unknown",
         evidence="SDS_KSC 2017-2018 has no DVEL directory (also not in unmatched/)")

    # --- 2016 BCHH: low-gain infraBSU 295 ----------------------------------------------------
    swap = AUDIT["sensor295_swap"]
    new = []
    for _, r in df[S("BCHH", ["DD1", "DD2"], "00")].iterrows():
        a, b = r.copy(), r.copy()
        a["end"], b["start"] = swap, swap
        new += [a, b]
    df = pd.concat([df[~S("BCHH", ["DD1", "DD2"], "00")], pd.DataFrame(new)], ignore_index=True)
    pre, post = df.start < swap, df.start >= swap
    S = lambda sta, cha=None, loc=None: (df.station == sta) & (True if cha is None else df.channel.isin(
        [cha] if isinstance(cha, str) else cha)) & (True if loc is None else df.location == loc)
    ev295 = ("sitedb.calibration: infraBSU 295 on HD1 2016-02-24..03-04, on HD2 from 2016-03-05 (calib 1.45 vs "
             "0.12 Pa/count for 283); launch peaks DD2 vs DD1/DD3 (audit T2)")
    for mask, ser in ((S("BCHH", "DD1", "00") & pre, "295"), (S("BCHH", "DD2", "00") & pre, "283"),
                      (S("BCHH", "DD1", "00") & post, "283"), (S("BCHH", "DD2", "00") & post, "295"),
                      (S("BCHH", "DD3", "00"), "291"), (S("BCHH", "DD1", "10"), "283"),
                      (S("BCHH", "DD2", "10"), "295"), (S("BCHH", "DD3", "10"), "291")):
        setv(mask, sensor_serial=ser)
    m295 = (df.station == "BCHH") & (df.sensor_serial == "295")
    setv(m295, sensitivity_correction=AUDIT["sensor295_correction"],
         change=f"low-gain infraBSU 295: sensitivity x{AUDIT['sensor295_correction']:.4g} (measured)", evidence=ev295)
    setv(S("BCHH", ["DD1", "DD2"], "00"), change="epoch split at the 295/283 swap")

    # --- Chaparral channels (were missing from KSC.xml) ----------------------------------------
    chap = df.sensor == "Chaparral"
    setv(chap, change="added (missing from KSC.xml)",
         evidence=f"Chaparral M25 {AUDIT['chaparral_V_per_Pa']:.3g} V/Pa from co-located infraBSU launch peaks (audit T3)")
    # --- BCHH3: Centaur 383 wrote x40 on HDF/HD2/HD3 until 2022-05-26 15:09:33 ---------------------
    t_b3 = "2022-05-26T15:09:33"
    b3 = S("BCHH3", ["HD2", "HDF"])
    keep = df[b3].copy()
    late = keep.copy()
    df.loc[b3, "end"] = t_b3
    setv(b3, vpp=1.0, change="vpp 40 -> 1",
         evidence="Centaur-written FL.BCHH3_20220324..20220401*.xml: preamp x40 on HD2/HD3/HDF; librockets.py: "
                  "'Chaparral M25 ... set to 1 V FS' before 2022-05-26; launch p*r vs BCHH2 (audit T4)")
    late["start"], late["end"], late["vpp"] = t_b3, "2022-05-27T00:00:00", 40.0
    late["change"] = "new epoch: input range changed to 40 Vpp at 2022-05-26 15:09:33"
    late["evidence"] = "FL.BCHH3_20220526T150857Z.xml: preamp x1"
    df = pd.concat([df, late], ignore_index=True)
    S = lambda sta, cha=None, loc=None: (df.station == sta) & (True if cha is None else df.channel.isin(
        [cha] if isinstance(cha, str) else cha)) & (True if loc is None else df.location == loc)
    setv(S("BCHH4", ["HD2", "HDF"]), evidence="FL.BCHH3_20220526T150857Z.xml (x1, 40 Vpp) and librockets.py "
                                              "'Chaparral switched to 40 V FS' from 2022-05-26; launch p*r (audit T4)")
    setv(S("BCHH1", ["DD1", "DD2"]), evidence="Centaur 383 dataless 2018-08-10: preamp x1 on HD1-HD3; syslog "
                                              "2020-12-11 'Applying input range for THAC_0/1: 40'")
    # --- RB166/RB268/RB383 (2021-10-16) ----------------------------------------------------------
    rb = df.station.isin(["RB166", "RB268", "RB383"]) & (df.sensor == "infraBSU")
    if AUDIT["rblab2021_vpp"] in (1, 40):
        setv(rb, vpp=float(AUDIT["rblab2021_vpp"]), change=f"vpp blank -> {AUDIT['rblab2021_vpp']}")
    else:
        setv(rb, include=False, status="dead",
             change="excluded: no launch signal on any infrasound input and input range not determinable",
             evidence="audit T5: Atlas V Lucy SNR ~1 on all RB infrasound channels while RB383 HHZ recorded it; "
                       "master notes: RB166 'infrasound ... did not record', RB383 'infrasound cable had no power', "
                       "RB268 'data look like noise'")
    df.loc[df.station.isin(["RB166", "RB268", "RB383"]) & (df.sensor == "TCP"), "change"] = \
        "vpp blank (built as 40) -> 40 explicit"
    # --- DVEL3 late 2020 (data beyond the master epoch) --------------------------------------------
    if AUDIT["dvel3_2020_vpp"]:
        extra = df[S("DVEL3")].copy()
        extra["start"], extra["end"] = "2020-11-05T00:00:00", "2020-12-12T00:00:00"
        extra["change"] = "new epoch: SDS has DVEL3 data 2020-11-05..2020-12-11 (master ends 2020-01-31)"
        extra["evidence"] = "SDS_KSC 2020; Trillium recorded the 2020-12-11 Delta IV (SNR 12)"
        inf = extra.sensor == "infraBSU"
        if AUDIT["dvel3_2020_vpp"] in (1, 40):
            extra.loc[inf, "vpp"] = float(AUDIT["dvel3_2020_vpp"])
        else:
            extra.loc[inf, ["include", "status"]] = [False, "dead"]
            extra.loc[inf, "change"] = "excluded: no launch signal on 5 launches BCHH2 recorded (SNR ~1); vpp unknown"
            extra.loc[inf, "evidence"] = "audit T4/T6 (launch_peaks_counts_2016_2022.csv, Nov-Dec 2020)"
        df = pd.concat([df, extra], ignore_index=True)
    # --- epoch ends that cut off data or overlapped --------------------------------------------------
    S = lambda sta, cha=None, loc=None: (df.station == sta) & (True if cha is None else df.channel.isin(
        [cha] if isinstance(cha, str) else cha)) & (True if loc is None else df.location == loc)
    setv(S("BHP8"), end="2019-02-13T00:00:00", change="end 2019-02-05 -> 2019-02-13 (data to 2019-02-12; "
                                                       "notes: 'removed on 2019-02-12?')")
    setv(S("BHP8"), notes="SDS also has BHP8 2019-04-10..06-25 = DAS 9BC5 after it moved to BHP7 (BHP7.10 "
                          "covers the same days); not given an epoch")
    # FIRE: no infrasound signal in 2016 (bad cable)
    setv(S("FIRE", ["DD1", "DD2", "DD3"]), status="dead",
         evidence="notebook 20: no launch signal; notes: 'still no infrasound data by 2016/03/23 so probably bad cable'")
    # Install days before the first epoch (user 2026-11-26: Trillium always on the 40 V input; infrasound at
    # 40 Vpp in 2016 and 1 Vpp in 2022). The Centaur-written FL.BCHH3_20220324*.xml already has x40 (1 Vpp)
    # on HDF/HD2, so the first epoch's settings are taken back to the first SDS day.
    for sta, old, new in [("BCHH3", "2022-03-30T00:00:00", "2022-03-24T00:00:00"),
                          ("S39A3", "2022-03-30T00:00:00", "2022-03-25T00:00:00"),
                          ("TANK", "2016-02-25T00:00:00", "2016-02-24T00:00:00"),
                          ("BHP2", "2018-10-16T00:00:00", "2018-10-15T00:00:00"),
                          ("BHP7", "2019-04-11T00:00:00", "2019-04-10T00:00:00")]:
        setv(S(sta) & (df.start == old), start=new,
             change=f"start {old[:10]} -> {new[:10]} (install-day SDS data)",
             evidence={"BHP2": "SDS_KSC/unmatched 1R.BHP2 2018.288 = XX.91F8 (DAS of BHP2), identical samples",
                       "BHP7": "SDS BHP8 2019.100 = DAS 9BC5 on the day it was installed at BHP7 (relabelled to "
                               "BHP7.10 by archive_fix/fix_sds_ksc.py)"}.get(
                 sta, "user 2026-11-26: same Centaur set-up as the rest of the deployment"))
    # XA.MTEGL: the MSFC Silicon Audio accelerometer later deployed at B23 (2026); same response.
    xa = df.network == "XA"
    df.loc[xa, "channel"] = df.loc[xa, "channel"].str.replace("EN", "CN", regex=False)
    df.loc[xa, "location"] = "01"
    setv(xa, sample_rate=250.0, datalogger="SiliconAudio", datalogger_gain=1.0, vpp=np.nan,
         sensor="SiliconAudio", sensor_V_per_unit=SILICON_AUDIO_V_PER_MPS2, sensitivity_correction=1.0,
         units="m/s**2", polarity="normal", status="estimated", include=True,
         response_source=f"flat: 15 V/g x {KELUNJI_COUNTS_PER_V} counts/V x gain",
         change="added: was excluded (no response); channels EN?.00 -> CN?.01 and 200 -> 250 Hz as in the SDS",
         evidence=("user: same Silicon Audio accelerometer as B23 2026; sensor 15 V/g from the B23 calibration "
                   "(audit/silicon_audio_calibration.csv). Recorder gain x1: the unit's 2026-01 huddle "
                   "settings say x1, and with x1 MTEGL reads 2.3x S39A1 (Artemis I, closer to 39B) and "
                   "0.8x S39A1 (2022-11-12 SLC-40); with x8 it would read 3.5x and 10x low"),
         notes=("SDS files are filed one day late: the file for day N holds day N+1 (records start "
                "~0.25 s before midnight); ObsPy's SDS client misses them unless the archive is re-filed"))
    # AM Raspberry Shakes: copy from the old KSC.xml; extend to cover the SDS
    am = df.network == "AM"
    setv(am, response_source="copy:KSC.xml(haldata) AM channel", vpp=np.nan,
         units="m/s")
    df.loc[am & (df.channel == "HDF"), "units"] = "Pa"
    df = df.drop_duplicates(subset=["network", "station", "location", "channel", "start", "end"])
    S = lambda sta, cha=None, loc=None: (df.station == sta) & (True if cha is None else df.channel.isin(
        [cha] if isinstance(cha, str) else cha)) & (True if loc is None else df.location == loc)
    r37 = S("R37BE") & (df.start.str[:4] == "2021")
    setv(r37, start="2019-05-21T00:00:00", end="2021-05-20T00:00:00",
         change="epoch 2021-01-01..05-18 -> 2019-05-21..2021-05-20 (SDS has data from 2019-05-21)")
    setv(S("R37BE") & (df.start.str[:4] == "2017"), start="2017-02-13T00:00:00", end="2017-11-26T00:00:00")
    rcd = S("RCD29")
    setv(rcd, start="2019-08-28T00:00:00", end="2021-05-20T00:00:00",
         change="epoch 2021-01-01..05-18 -> 2019-08-28..2021-05-20 (SDS has data from 2019-08-28)")
    S = lambda sta, cha=None, loc=None: (df.station == sta) & (True if cha is None else df.channel.isin(
        [cha] if isinstance(cha, str) else cha)) & (True if loc is None else df.location == loc)
    # SON2 (2017): huddle inputs DD4-DD6 read 33-38x fewer counts than DD1-DD3 on both launches
    setv(S("SON2", ["DD4", "DD5", "DD6"]), vpp=40.0, change="vpp 1 -> 40",
         evidence="audit T4b: TDRS-M 2017-08-18 DD1-3 ~1.0e5 counts vs DD4-6 ~3.2e3 (x33); 2017-08-26 x38; "
                  "40 Vpp gives 165-184 Pa, matching SON1 DD3 (178 Pa) and SON2 DD1-3 at 1 Vpp (140 Pa)")
    # SON1 DD1 (2017) behaves as an infraBSU at 40 Vpp, not the Chaparral
    setv(S("SON1", "DD1"), sensor="infraBSU", sensor_serial="", sensor_V_per_unit=INFRABSU_V_PER_PA,
         change="sensor Chaparral -> infraBSU (serial unknown)",
         evidence="audit T3/T4b: TDRS-M 2017-08-18 DD1 = 2797 counts = 152 Pa as infraBSU at 40 Vpp (SON1 DD3 178 Pa, "
                  "SON2 140-184 Pa) but 0.017 Pa as a Chaparral; master notes: the Chaparral moved to SON1 later")
    # RBLAB 2021 Trillium/channels with no signal
    setv(S("RB166", ["HHZ", "HHN", "HHE"]) | S("RB268", ["DHZ", "DHN", "DHE"]), status="dead",
         evidence="audit T5: Atlas V Lucy SNR ~1 (RB383 HHZ SNR 42); RB268 DHZ peak 2 counts")
    setv(S("TANK", "DD1"), notes="audit: no launch signal except SES-9 (SNR 7); notes say not working by 2016-03-23")
    # BCHH1 from the 2020-01-31 service: Trillium ~70x low, infraBSU DD2 0.01-0.08 of BCHH2, Chaparral dead
    t_b1 = "2020-01-31T00:00:00"
    b1 = (df.station == "BCHH1") & (df.start < t_b1) & ((df.end == "") | (df.end > t_b1))
    late = df[b1].copy()
    df.loc[b1, "end"] = t_b1
    late["start"] = t_b1
    late["status"] = "suspect"
    late["change"] = "epoch split at the 2020-01-31 service (status flag only, response unchanged)"
    late["notes"] = ("from 2020-01-31 (BCHH battery dead since 2019-09-23, ant/mouse nests, Chaparral bucket broken): "
                     "DHZ air-coupling 0.12 vs 9 um/s/Pa before (~70x low; BHP2 unchanged); DD2 0.01-0.08 of BCHH2 on "
                     "8 of 10 launches (0.91 on 2020-10-24); DD1 ~5-15 counts = no signal")
    late.loc[late.channel == "DD1", "status"] = "dead"
    df = pd.concat([df, late], ignore_index=True)
    # BCHH3 HDF: Chaparral at 1 Vpp clips above ~1.2 Pa
    setv((df.station.isin(["BCHH1", "BCHH3", "BCHH4"])) & (df.sensor == "Chaparral"),
         notes="M25 output +-18 V: clips above ~45 Pa at 40 Vpp and ~1.2 Pa at 1 Vpp (all BCHH3 launches clipped)")
    # BCHH 2016 location codes: SDS uses 00 (Feb-Apr) and 10 (May-Sep); 20 has no data but is kept.
    # Master off-dates are inclusive days: if the SDS has data on the end day (and no later epoch of the
    # same NSLC starts then), end the epoch at the following midnight.
    sds = "/Volumes/classdata/remastered/SDS_KSC"
    for i, r in df.iterrows():
        e = r.end
        if not e or not e.endswith("T00:00:00"):
            continue
        t = UTCDateTime(e)
        loc = "" if r.location == "--" else r.location
        # the archive may hold a Centaur D?? channel under its SEED name C??/H?? (archive_fix/rename_band_codes.py)
        chans = [r.channel] + ([b + r.channel[1:] for b in "CH"] if r.channel[:2] in ("DD", "DH") else [])
        fs = [f"{sds}/{t.year}/{r.network}/{r.station}/{c}.D/{r.network}.{r.station}.{loc}.{c}.D.{t.year}.{t.julday:03d}"
              for c in chans]
        later = ((df.network == r.network) & (df.station == r.station) & (df.location == r.location)
                 & (df.channel == r.channel) & (df.start == e)).any()
        if any(os.path.exists(f) for f in fs) and not later:
            df.at[i, "end"] = str(t + 86400)[:19]
            df.at[i, "change"] = (r.change + "; " if r.change else "") + "end +1 day (SDS has data on the off-date)"
    return df


# ---------------------------------------------------------------------------------------------
# 2026
# ---------------------------------------------------------------------------------------------
def sds_2026_extents():
    out = {}
    L = lambda p: [x for x in sorted(os.listdir(p)) if not x.startswith(".")]
    for sta in L(f"{SDS2026}/1R"):
        for cd in L(f"{SDS2026}/1R/{sta}"):
            if cd[0] not in "DH" or cd.startswith("SOH"):
                continue
            days = defaultdict(list)
            for f in L(f"{SDS2026}/1R/{sta}/{cd}"):
                p = f.split(".")
                if len(p) >= 7:
                    days[p[2]].append(int(p[6]))
            for loc, d in days.items():
                first = sorted(glob.glob(f"{SDS2026}/1R/{sta}/{cd}/1R.{sta}.{loc}.{cd[:3]}.D.2026.*"))[0]
                sr = read(first, headonly=True)[0].stats.sampling_rate
                out[(sta, loc or "--", cd[:3])] = (min(d), max(d), sr)
    return out


def doy(d, end=False):
    t = UTCDateTime(2026, 1, 1) + (d - 1 + (1 if end else 0)) * 86400
    return str(t)[:19]


def centaur_configs():
    files = {}
    for d in CENTAUR_DIRS_2026:
        for p in glob.glob(f"{d}/1R.*_*Z.xml"):
            files.setdefault(os.path.basename(p), p)
    by_sta = defaultdict(list)
    for name, p in files.items():
        sta, ts = re.match(r"1R\.(\w+?)_(\d{8}T\d{6})Z\.xml", name).groups()
        inv = read_inventory(p)
        s = inv[0][0]
        chans = {}
        for c in s:
            if c.code[0] not in "DH":
                continue
            st = c.response.response_stages
            chans[c.code] = (c.sample_rate, round(st[1].stage_gain, 4))
        sig = (round(s.latitude, 4), round(s.longitude, 4), tuple(sorted(chans.items())))
        by_sta[sta].append((UTCDateTime(ts), p, sig, s.latitude, s.longitude, s.elevation))
    cfg = {}
    for sta, lst in by_sta.items():
        lst.sort()
        merged = []
        for t, p, sig, la, lo, el in lst:
            if not merged or merged[-1]["sig"] != sig:
                merged.append(dict(t=t, path=p, sig=sig, lat=la, lon=lo, elev=el, chans=dict(sig[2]), n_files=1))
            else:
                merged[-1]["n_files"] += 1
        cfg[sta] = merged
    return cfg


def rows_2026():
    ext = sds_2026_extents()
    cfg = centaur_configs()
    sheet = pd.read_excel(BOX_XLS, sheet_name="SDS2026_metadata")
    gemgps = pd.read_excel(BOX_XLS, sheet_name="gem_gps_data", header=None, names=["serial", "id", "lat", "lon"])
    a2 = pd.read_excel(BOX_XLS, sheet_name="artemis2").set_index("station")
    gem_map = pd.read_csv(REPO / "2026_ingest_service_runs/config/gem_mapping_artemis2_example.csv")
    solo_map = pd.read_csv(REPO / "2026_ingest_service_runs/config/smartsolo_mapping_artemis2.csv")
    gem_serial = {r.id: str(r.serial) for r in gem_map.itertuples()}
    gem_xy = {str(r.id).strip(): (float(r.lat), float(r.lon)) for r in gemgps.itertuples()}
    solo_serial = {r.seed_prefix.split(".")[1]: str(r.serial) for r in solo_map.itertuples()}
    huddle = sheet[sheet.Station.astype(str).str.startswith("C")].groupby("Station")[["Lat", "Lon"]].first()

    rows = []
    centaur_stations = sorted({k[0] for k in ext if k[1] == "00"})
    template_cfg = cfg["C371"][0]      # nominal 2026 configuration (all Centaurs identical at 500 sps)
    for sta in centaur_stations:
        chans = sorted(k[2] for k in ext if k[0] == sta and k[1] == "00")
        d0 = min(ext[(sta, "00", c)][0] for c in chans)
        d1 = max(ext[(sta, "00", c)][1] for c in chans)
        data_start, data_end = doy(d0), doy(d1, end=True)
        epochs = cfg.get(sta)
        if not epochs:
            la, lo = huddle.loc[sta, ["Lat", "Lon"]]
            epochs = [dict(t=UTCDateTime(data_start), path=template_cfg["path"], chans=template_cfg["chans"],
                           lat=la, lon=lo, elev=0.0, n_files=0, nominal=True)]
        bounds = []
        for i, e in enumerate(epochs):
            s = data_start if i == 0 and str(e["t"])[:19] > data_start else str(e["t"])[:19]
            en = str(epochs[i + 1]["t"])[:19] if i + 1 < len(epochs) else data_end
            if en <= s:
                continue
            bounds.append((s, en, e))
        if sta == "B20":       # metadata/metadata.md: Sensor B 1 Vpp until the 2026-09-23 visit, then 40 Vpp
            last = bounds[-1]
            bounds[-1] = (last[0], "2026-09-23T00:00:00", last[2])
            bounds.append(("2026-09-23T00:00:00", "", dict(last[2], forced_vpp=40.0)))
        for s, en, e in bounds:
            for cha in chans:
                if cha not in e["chans"]:
                    continue
                sr, pre = e["chans"][cha]
                is_inf = cha.startswith("DD")
                vpp = e.get("forced_vpp") if is_inf and e.get("forced_vpp") else (
                    1.0 if np.isclose(pre, 40) else 40.0 if np.isclose(pre, 1, atol=0.01) else np.nan)
                sensor = "TCP" if cha.startswith("DH") else ("Chaparral" if cha == "DDF" else "infraBSU")
                az, dip = orient(cha)
                if cha in ("DH1", "DH2"):
                    az = 0.0 if cha == "DH1" else 90.0
                src = ("nominal:" if e.get("nominal") else "centaur:") + e["path"]
                ev = (f"Centaur-written response ({os.path.basename(e['path'])}, {e['n_files']} identical files): "
                      f"preamp x{pre:g}") if not e.get("nominal") else \
                     "no Centaur response file for this station: nominal 2026 configuration (as every other Centaur)"
                if e.get("forced_vpp"):
                    ev = "metadata/metadata.md: B20 Sensor B observed at 1 Vpp and changed to 40 Vpp on 2026-09-23"
                notes = ""
                if sta == "B03":
                    notes = "Centaur ~100x low on all channels (hardware fault, Artemis II); DD0-2 no signal"
                if sta in ("B05", "B29") and cha in ("DD1", "DD2"):
                    notes = "no infrasound signal at Artemis II"
                if sta == "B05" and cha.startswith("DH"):
                    notes = "Trillium mass off-centre (DH1/DH2 at 79%/98% of full scale)"
                if sta == "B20" and cha == "DDF":
                    notes = "Chaparral did not record the Artemis II launch"
                rows.append(dict(network="1R", station=sta, location="00", channel=cha, start=s, end=en,
                                 latitude=e["lat"], longitude=e["lon"], elevation=e["elev"], depth=0.0,
                                 azimuth=az, dip=dip, sample_rate=sr, datalogger="Centaur", datalogger_serial="",
                                 vpp=vpp, datalogger_gain=np.nan, sensor=sensor, sensor_serial="",
                                 sensor_V_per_unit={"TCP": TRILLIUM_V_PER_MPS, "infraBSU": INFRABSU_V_PER_PA,
                                                    "Chaparral": AUDIT["chaparral_V_per_Pa"]}[sensor],
                                 sensitivity_correction=1.0, units="m/s" if sensor == "TCP" else "Pa",
                                 polarity="normal", status="ok", include=True, response_source=src,
                                 change="added (2026)", evidence=ev, notes=notes, source_row="2026"))
    # Gems and SmartSolos
    for (sta, loc, cha), (d0, d1, sr) in sorted(ext.items()):
        if loc == "00":
            continue
        if cha.startswith("HD"):
            sid = f"1R.{sta}.{'' if loc == '--' else loc}.{cha}"
            ser = gem_serial.get(sid, "")
            la, lo = gem_xy.get(sid, (np.nan, np.nan))
            note = ""
            if np.isnan(la):
                same = [v for k, v in gem_xy.items() if k.startswith(f"1R.{sta}.")]
                la, lo = same[0] if same else (a2.loc[sta, "lat"], a2.loc[sta, "lon"]) if sta in a2.index else \
                    gem_xy["1R.B20..HDF"]
                note = "coordinates of the co-located Gem/station (own GPS not in sheet)"
            if sta == "UNK":
                note = ("Gem 363, not yet assigned to a station by the ingest mapping; ~8 m from B20 per its GPS "
                        "log (used in the B20 array); coordinates of B20 HDF Gem")
            rows.append(dict(network="1R", station=sta, location=loc, channel=cha, start=doy(d0),
                             end=doy(d1, end=True), latitude=la, longitude=lo, elevation=0.0, depth=0.0,
                             azimuth=0.0, dip=0.0, sample_rate=sr, datalogger="Gem", datalogger_serial=ser,
                             vpp=np.nan, datalogger_gain=np.nan, sensor="Gem", sensor_serial=ser,
                             sensor_V_per_unit=np.nan, sensitivity_correction=1.0, units="Pa", polarity="normal",
                             status="ok", include=True, response_source="gemlog.get_gem_response(gain='high')",
                             change="added (2026)",
                             evidence="2026_ingest gem_mapping_artemis2_example.csv; SDS day range",
                             notes=("16-bit overflow above ~100-140 Pa: repair with flovopy.ingest.gem_overflow "
                                    "before response removal; " + note).strip("; "), source_row="2026"))
        elif cha.startswith("DP"):
            ser = solo_serial.get(sta, "")
            xy = gem_xy.get(f"1R.{sta}..HDF") or ((a2.loc[sta, "lat"], a2.loc[sta, "lon"]) if sta in a2.index
                                                  else (np.nan, np.nan))
            az, dip = orient(cha)
            pol = "normal"
            if cha == "DPZ":
                dip, pol = 90.0, "reversed"
            rows.append(dict(network="1R", station=sta, location=loc, channel=cha, start=doy(d0),
                             end=doy(d1, end=True), latitude=xy[0], longitude=xy[1], elevation=0.0, depth=0.0,
                             azimuth=az, dip=dip, sample_rate=sr, datalogger="SmartSolo", datalogger_serial=ser,
                             vpp=np.nan, datalogger_gain=1000.0, sensor="SmartSolo", sensor_serial=ser,
                             sensor_V_per_unit=SMARTSOLO_V_PER_MPS, sensitivity_correction=1.0, units="m/s",
                             polarity=pol, status="ok", include=True,
                             response_source="paz:f0=5 Hz, h=0.7, 76.7 V/(m/s), 1000 counts(mV)/V",
                             change="added (2026)",
                             evidence="smartsolo_mapping_artemis2.csv; SDS day range; ensemble.yaml smartsolo_geophone; "
                                      "vertical polarity reversed (Artemis II coupling sign vs Trillium) -> dip +90",
                             notes="harvested data are geophone output in mV (FLOAT32), not velocity",
                             source_row="2026"))
    # DG.B12, DG.B07: MSFC Guralp Certimus (SDS location 1L). Response from the Certimus-written
    # StationXML downloaded at B12 on 2026-03-10; user: same for B07, config unchanged since Jan 2026.
    certimus_xml = "/Volumes/classdata/KSC/20260310_service/Guralp_day1/Sensor1.xml"
    for sta, chans, sr, t0, t1, la, lo, note in (
            ("B12", ("CHE", "CHN", "CHZ"), 250.0, "2026-01-10T00:00:00", "2026-04-02T00:00:00", 28.621725, -80.647263,
             "SDS has 250 sps under location 1L, which Sensor1.xml defines at 500 sps; the 250 sps response "
             "(Sensor1.xml location 1N, same sensitivity) is used. Coordinates from Sensor1.xml"),
            ("B07", ("CHZ",), 500.0, "2026-03-30T00:00:00", "2026-04-05T00:00:00", 28.60727, -80.59418,
             "B07 has its own Certimus but its StationXML was not downloaded; B12's response (per-axis factory "
             "calibration differs by <1% between units) is used, per the user. SDS has only CHZ. Coordinates of "
             "the B07 Gem/SmartSolo")):
        for cha in chans:
            az, dip = {"CHE": (90.0, 0.0), "CHN": (0.0, 0.0), "CHZ": (0.0, -90.0)}[cha]
            rows.append(dict(network="DG", station=sta, location="1L", channel=cha, start=t0, end=t1,
                             latitude=la, longitude=lo, elevation=0.0, depth=0.0, azimuth=az, dip=dip,
                             sample_rate=sr, datalogger="Certimus", datalogger_serial="", vpp=np.nan,
                             datalogger_gain=np.nan, sensor="Certimus", sensor_serial="",
                             sensor_V_per_unit=np.nan, sensitivity_correction=1.0, units="m/s",
                             polarity="normal", status="ok", include=True,
                             response_source=f"certimus:{certimus_xml}", change="added (2026)",
                             evidence="Certimus-written Sensor1.xml (20260310_service Guralp_day1); SDS day range",
                             notes=note, source_row="2026"))
    # DG.B23: MSFC Silicon Audio accelerometer on a Kelunji-format recorder (DG SDS, location 01)
    for cha, az, dip in (("CLE", 90.0, 0.0), ("CLN", 0.0, 0.0), ("CLZ", 0.0, -90.0)):
        rows.append(dict(network="DG", station="B23", location="01", channel=cha,
                         start="2026-01-10T21:42:00", end="2026-09-24T19:32:00",
                         latitude=28.57879, longitude=-80.60780, elevation=0.0, depth=0.0,
                         azimuth=az, dip=dip, sample_rate=500.0, datalogger="SiliconAudio",
                         datalogger_serial="02000160", vpp=np.nan, datalogger_gain=8.0,
                         sensor="SiliconAudio", sensor_serial="", sensor_V_per_unit=SILICON_AUDIO_V_PER_MPS2,
                         sensitivity_correction=1.0, units="m/s**2", polarity="normal", status="ok",
                         include=True, response_source=f"flat: 15 V/g x {KELUNJI_COUNTS_PER_V} counts/V x gain",
                         change="added (2026)",
                         evidence=("settings.ss (20260922_service SiliconAudio/B23): gain x8, 500 sps, "
                                   "network DG, location 01, serial 02000160; calibrated against the B23 "
                                   "SmartSolo on Artemis II: 1.51 (Z), 1.57 (N) V/(m/s^2); SDS 2026.069-094. "
                                   "Extended 2026-11-27 to the raw minute files (tachyon_backup KSC_DATA: "
                                   "Artemis2/00_download 2026-01-10 21:42 - 03-10, 202609_service/day3 "
                                   "2026-06-12 - 09-24 19:31): every settings.ss in that span has serial "
                                   "02000160, DG/B23/01, gain x8, 500 sps and the same GPS; launches recorded "
                                   "throughout (rms ratio 100-350, onset 30-40 s after liftoff). No data in hand "
                                   "for 2026-04-05 - 06-12: the Marshall team (Paul, Aiden) downloaded the "
                                   "station around 06-12 and has not shared it (Glenn, 2026-11-28); the "
                                   "metadata are assumed unchanged across the gap. Before 21:42 on 01-10 the unit ran as XA.MTEGL "
                                   "(800 sps, gain x1): off site, not included"),
                         notes=("settings.ss names the sensor 'LE-3Dlite MKII' (400 V/(m/s)), but the output is "
                                "proportional to acceleration, so that preset is wrong; GPS from the recorder "
                                "histogram. CLE is poorly coherent with the SmartSolo (orientation unknown)"),
                         source_row="2026"))
    return pd.DataFrame(rows, columns=COLUMNS)


README = [
    ("row", "one NSLC channel epoch; start inclusive, end exclusive, UTC; blank end = open"),
    ("location", "'--' = empty location code (2026 Gems and SmartSolos)"),
    ("vpp", "Centaur input range for this channel's sensor port: 40 (preamp x1, 18.4 counts/Pa for infraBSU) "
            "or 1 (preamp x40, 736 counts/Pa). Required for every included Centaur row"),
    ("datalogger_gain", "RT130 preamp gain (32) / SmartSolo counts per V (1000: harvested in mV)"),
    ("sensor_V_per_unit", "sensor sensitivity before any correction (V/Pa or V/(m/s))"),
    ("sensitivity_correction", "measured factor applied to the sensor stage (infraBSU 295 in 2016)"),
    ("polarity", "'reversed': SmartSolo vertical, encoded as dip +90"),
    ("status", "ok / dead (kept, flagged in a channel comment) / no_data / no_response"),
    ("include", "False rows are documented here but not written to the StationXML"),
    ("response_source", "template:KSC.xml = 2016-2022 Centaur/RT130 FIR stages from the 2025 KSC.xml; "
                        "centaur:<file> = 2026 Centaur-written response; nominal:<file> = no file for that station; "
                        "copy:KSC.xml = Raspberry Shake channel copied; gemlog; paz"),
    ("change", "difference from KSC.xml (2025) / master v2"),
    ("sds_channel", "channel code in the archived MiniSEED (Centaur D?? names) until the archives are renamed"),
    ("evidence", "why; audit tables in 03_stationxml/audit/"),
]

def seed_band_codes(df):
    """SEED band codes for the Centaur broadband channels (user, 2026-11-26).

    The Centaur names its channels with band code D at 250/500 sps, but D is for sensors with a corner
    period < 10 s. The Trillium Compact (120 s), infraBSU (-3 dB at ~0.035 Hz, ~28 s) and Chaparral M25
    are broadband, so the SEED band code is C at 250-999 sps and H at 80-249 sps (B20 2026-04-04..06-14
    and the B24 huddle on 2026-01-08 ran at 100 sps under the D names). SmartSolo DP? (5 Hz geophone,
    500 sps) is correctly D and is unchanged. `sds_channel` keeps the code the archived MiniSEED uses until
    03_stationxml/archive_fix/rename_band_codes.py has been run on the archives.
    """
    df = df.copy()
    df["sds_channel"] = df.channel
    m = (df.datalogger == "Centaur") & df.channel.str.startswith("D") & df.sensor.isin(["TCP", "infraBSU", "Chaparral"])
    sr = df.sample_rate.astype(float)
    band = np.where(sr >= 250, "C", np.where(sr >= 80, "H", "D"))
    new = pd.Series(band, index=df.index) + df.channel.str[1:]
    for i in df.index[m & (new != df.channel)]:
        df.loc[i, "channel"] = new[i]
        note = f"SEED band code {df.sds_channel[i]} -> {new[i]} ({int(sr[i])} sps, broadband sensor); archive still {df.sds_channel[i]}"
        prev = df.change[i] if isinstance(df.change[i], str) else ""
        df.loc[i, "change"] = (prev + "; " if prev else "") + note
    return df


if __name__ == "__main__":
    old = rows_2016_2022()
    new = rows_2026()
    df = pd.concat([old, new], ignore_index=True)
    df = df.sort_values(["network", "station", "location", "start", "channel"]).reset_index(drop=True)
    df = seed_band_codes(df)
    changes = df[df.change.astype(str) != ""]
    with pd.ExcelWriter(OUT) as xw:
        df.to_excel(xw, sheet_name="channel_epochs", index=False)
        changes.to_excel(xw, sheet_name="changes", index=False)
        pd.DataFrame(README, columns=["column", "meaning"]).to_excel(xw, sheet_name="README", index=False)
    print(f"{OUT}: {len(df)} channel epochs ({int(df.include.sum())} included), {len(changes)} changed")
