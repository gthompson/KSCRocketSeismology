"""Build the KSC StationXML (2016-2026) from ksc_stations_master_v3.xlsx.

    python 03_stationxml/build_ksc_stationxml.py [--sheet ...xlsx] [--out 03_stationxml/KSC.xml]

Strict where flovopy's builder is lenient (flovopy/stationmetadata/build.py maps any vpp other than
1/40 to 40): every included Centaur row must say vpp 1 or 40, every RT130 row its gain, every sensor
its sensitivity; otherwise this script stops with the offending rows. Overlapping epochs of one
NSLC are also an error.

Responses
  Centaur 2016-2022  stages from the 2025 KSC.xml (haldata, read-only) for the same sample rate and
                     sensor port, with the sensor stage and the preamplifier (x1 at 40 Vpp, x40 at 1 Vpp;
                     Trillium x0.9925 as the Centaurs write it) set from the sheet
  Centaur 2026       the Centaur-written response named in response_source, with the infraBSU /
                     Chaparral sensor stage in place of the Centaur's unity Sensor B stage
  RT130 + L-22       KSC.xml template with the RT130 preamp gain from the sheet
  Gem                gemlog.get_gem_response('high')
  SmartSolo          5 Hz, h=0.7 geophone, 76.7 V/(m/s), 1000 counts(mV)/V; vertical dip +90 (reversed)
  Raspberry Shake    channel copied from the 2025 KSC.xml

Each channel carries datalogger and sensor descriptions (with the input range), serials, and
comments for status, change and evidence.
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read_inventory
from obspy.core.inventory import (Channel, Comment, Equipment, Inventory, Network, Site, Station)
from obspy.core.inventory.response import (CoefficientsTypeResponseStage, InstrumentSensitivity,
                                           PolesZerosResponseStage, Response)

HERE = Path(__file__).resolve().parent
OLD_XML = "/Volumes/haldata/KSC/station_metadata/KSC.xml"      # 2025 build, read-only: stage templates
INFRABSU_XML = "/Volumes/haldata/KSC/station_metadata/infraBSU_21s_0.5inch.xml"
TRILLIUM_PREAMP_40VPP = 0.9925                                   # as written by the Centaurs


class SheetError(ValueError):
    pass


def _s(x):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else str(x)


def load_sheet(path):
    df = pd.read_excel(path, sheet_name="channel_epochs", dtype={"location": str, "datalogger_serial": str,
                                                                  "sensor_serial": str})
    df["location"] = df.location.fillna("--").replace({"--": ""})
    for c in ("datalogger_serial", "sensor_serial", "sensor", "notes", "change", "evidence", "response_source", "end"):
        df[c] = df[c].map(_s)
    return df[df.include.astype(bool)].reset_index(drop=True)


def check(df):
    errs = []
    cen = df[df.datalogger == "Centaur"]
    bad = cen[~cen.vpp.isin([1.0, 40.0])]
    if len(bad):
        errs.append("Centaur rows without vpp 1 or 40 (blank is an error, not 40):\n"
                    + bad[["station", "location", "channel", "start", "vpp", "sensor"]].to_string())
    rt = df[df.datalogger == "RT130"]
    if rt.datalogger_gain.isna().any():
        errs.append("RT130 rows without datalogger_gain:\n" + rt[rt.datalogger_gain.isna()].to_string())
    sa = df[df.datalogger == "SiliconAudio"]
    if sa.datalogger_gain.isna().any():
        errs.append("SiliconAudio rows without recorder gain:\n" + sa[sa.datalogger_gain.isna()].to_string())
    need = df[df.datalogger.isin(["Centaur", "RT130", "SmartSolo", "SiliconAudio"])]
    if need.sensor_V_per_unit.isna().any():
        errs.append("rows without sensor sensitivity:\n"
                    + need[need.sensor_V_per_unit.isna()][["station", "channel", "start", "sensor"]].to_string())
    for key, g in df.groupby(["network", "station", "location", "channel"]):
        g = g.sort_values("start")
        s = list(g.start)
        e = [x or "2599-12-31T23:59:59" for x in g.end]
        for i in range(len(s)):
            if e[i] <= s[i]:
                errs.append(f"{'.'.join(key)}: end {e[i]} <= start {s[i]}")
            if i and s[i] < e[i - 1]:
                errs.append(f"{'.'.join(key)}: epochs overlap ({s[i - 1]}..{e[i - 1]} and {s[i]}..{e[i]})")
    if errs:
        raise SheetError("\n\n".join(errs))


# ---------------------------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------------------------
class Templates:
    def __init__(self):
        self.old = read_inventory(OLD_XML)
        self.infrabsu = read_inventory(INFRABSU_XML)[0][0][0].response.response_stages[0]
        self._centaur = {}

    def old_response(self, sid, t):
        return copy.deepcopy(self.old.get_response(sid, t))

    def centaur_2016(self, kind, sr):
        """Centaur FIR template for (kind 'D' pressure | 'H' Trillium, sample rate) from the 2025 KSC.xml."""
        key = {("D", 250.0): ("1R.BCHH.00.DD1", "2016-03-01"), ("D", 100.0): ("1R.BCHH2.00.HD4", "2022-06-01"),
               ("H", 250.0): ("1R.BCHH.00.DHZ", "2016-03-01"), ("H", 100.0): ("1R.BCHH3.00.HHZ", "2022-04-15")}
        if (kind, sr) not in key:
            raise SheetError(f"no Centaur template for {kind} at {sr} sps")
        return self.old_response(*key[(kind, sr)])

    def certimus(self, path, sr, cha):
        """Guralp Certimus response for channel code cha at sample rate sr from a Certimus StationXML."""
        if path not in self._centaur:
            self._centaur[path] = read_inventory(path)
        c = [c for n in self._centaur[path] for st in n for c in st if c.code == cha and c.sample_rate == sr]
        if not c:
            raise SheetError(f"no {cha} at {sr} sps in {path}")
        return copy.deepcopy(c[0].response), c[0].location_code

    def centaur_file(self, path, cha):
        if path not in self._centaur:
            self._centaur[path] = read_inventory(path)
        return copy.deepcopy(self._centaur[path].select(channel=cha)[0][0][0].response)


def pressure_sensor_stage(r, tpl):
    if r.sensor == "infraBSU":
        st = copy.deepcopy(tpl.infrabsu)
        st.stage_gain = float(r.sensor_V_per_unit) * float(r.sensitivity_correction)
        st.description = f"infraBSU 0.5in s/n {r.sensor_serial or '?'}"
    elif r.sensor == "Chaparral":
        st = PolesZerosResponseStage(1, float(r.sensor_V_per_unit) * float(r.sensitivity_correction), 1.0, "PA", "V",
                                     "LAPLACE (RADIANS/SECOND)", 1.0, [], [], normalization_factor=1.0,
                                     description="Chaparral M25 low gain (flat)")
    else:
        raise SheetError(f"unknown pressure sensor {r.sensor}")
    st.input_units, st.output_units = "PA", "V"
    return st


def finish(resp, units, freq):
    for i, s in enumerate(resp.response_stages, 1):
        s.stage_sequence_number = i
    resp.instrument_sensitivity = InstrumentSensitivity(1.0, freq, units, "COUNTS")
    resp.recalculate_overall_sensitivity(freq)
    return resp


def build_response(r, tpl):
    t = UTCDateTime(r.start) + 1
    src = r.response_source
    if r.datalogger == "Centaur":
        pre = (40.0 if r.vpp == 1 else 1.0) if r.sensor != "TCP" else TRILLIUM_PREAMP_40VPP
        if src.startswith(("centaur:", "nominal:")):
            resp = tpl.centaur_file(src.split(":", 1)[1], r.channel)
        else:
            resp = tpl.centaur_2016("H" if r.sensor == "TCP" else "D", float(r.sample_rate))
        stages = resp.response_stages
        if r.sensor == "TCP":
            stages[0].stage_gain = float(r.sensor_V_per_unit)
            stages[1].stage_gain = pre
            return finish(resp, "M/S", 1.0)
        stages[0] = pressure_sensor_stage(r, tpl)
        stages[1].stage_gain = pre
        stages[1].input_units = stages[1].output_units = "V"
        return finish(resp, "PA", 1.0)
    if r.datalogger == "RT130":
        resp = tpl.old_response("1R.BHP1.00.EHZ", "2019-01-01")
        resp.response_stages[0].stage_gain = float(r.sensor_V_per_unit)
        resp.response_stages[1].stage_gain = float(r.datalogger_gain)
        return finish(resp, "M/S", 10.0)
    if r.datalogger == "Gem":
        import gemlog
        resp = gemlog.get_gem_response(gain="high")
        resp.instrument_sensitivity.input_units = "PA"
        return resp
    if r.datalogger == "SmartSolo":
        w0, h = 2 * np.pi * 5.0, 0.7
        poles = list(np.roots([1, 2 * h * w0, w0 ** 2]))
        f = 20.0
        s = 2j * np.pi * f
        a0 = 1.0 / abs(s ** 2 / ((s - poles[0]) * (s - poles[1])))
        st1 = PolesZerosResponseStage(1, float(r.sensor_V_per_unit), f, "M/S", "V", "LAPLACE (RADIANS/SECOND)", f,
                                      [0j, 0j], poles, normalization_factor=a0, description="SmartSolo 5 Hz geophone")
        st2 = CoefficientsTypeResponseStage(2, float(r.datalogger_gain), f, "V", "COUNTS", "DIGITAL",
                                            numerator=[1.0], denominator=[], decimation_input_sample_rate=float(r.sample_rate),
                                            decimation_factor=1, decimation_offset=0, decimation_delay=0.0,
                                            decimation_correction=0.0, description="harvested output in mV (1 count = 1 mV)")
        return finish(Response(response_stages=[st1, st2]), "M/S", f)
    if r.datalogger == "Certimus":
        resp, _ = tpl.certimus(src.split(":", 1)[1], float(r.sample_rate), r.channel)
        return resp
    if r.datalogger == "SiliconAudio":
        # flat accelerometer (V per m/s^2) into a Kelunji-format recorder (419430.4 counts/V x gain)
        st1 = PolesZerosResponseStage(1, float(r.sensor_V_per_unit), 1.0, "M/S**2", "V",
                                      "LAPLACE (RADIANS/SECOND)", 1.0, [], [], normalization_factor=1.0,
                                      description="Silicon Audio accelerometer, 15 V/g (flat)")
        st2 = CoefficientsTypeResponseStage(2, 419430.4 * float(r.datalogger_gain), 1.0, "V", "COUNTS", "DIGITAL",
                                            numerator=[1.0], denominator=[],
                                            decimation_input_sample_rate=float(r.sample_rate), decimation_factor=1,
                                            decimation_offset=0, decimation_delay=0.0, decimation_correction=0.0,
                                            description=f"Kelunji-format recorder, 419430.4 counts/V x gain {r.datalogger_gain:g}")
        return finish(Response(response_stages=[st1, st2]), "M/S**2", 1.0)
    raise SheetError(f"no response rule for datalogger {r.datalogger}")


# ---------------------------------------------------------------------------------------------
# Equipment and comments
# ---------------------------------------------------------------------------------------------
DATALOGGER = {"Centaur": ("Nanometrics", "Centaur"), "RT130": ("Reftek", "RT130"), "Gem": ("Anderson", "Gem v1"),
              "SmartSolo": ("DTCC", "SmartSolo IGU-16HR"),
              "SiliconAudio": ("", "Kelunji-format recorder (MSFC)"),
              "Certimus": ("Guralp", "Certimus")}
SENSOR = {"infraBSU": ("Boise State University", 'infraBSU 0.5"'), "Chaparral": ("Chaparral Physics", "Model 25"),
          "TCP": ("Nanometrics", "Trillium Compact Posthole 120 s"), "L-22": ("Sercel/Mark Products", "L-22D 2 Hz"),
          "Gem": ("Anderson", "Gem v1 MEMS pressure sensor"), "SmartSolo": ("DTCC", "5 Hz geophone"),
          "SiliconAudio": ("Silicon Audio", "accelerometer, 15 V/g"),
          "Certimus": ("Guralp", "Certimus broadband seismometer")}


def describe(r):
    if r.datalogger == "Centaur":
        if r.sensor == "TCP":
            dl = "Centaur, Sensor A, input range 40 Vpp (preamp x0.9925)"
        else:
            dl = f"Centaur, Sensor B, input range {r.vpp:g} Vpp (preamp x{40 if r.vpp == 1 else 1})"
    elif r.datalogger == "RT130":
        dl = f"RT130, preamp gain x{r.datalogger_gain:g}"
    elif r.datalogger == "Gem":
        dl = "Gem infrasound logger, high gain, 16-bit"
    elif r.datalogger == "SmartSolo":
        dl = "SmartSolo node, harvested in mV"
    elif r.datalogger == "Certimus":
        dl = f"Guralp Certimus integrated digitizer, {r.sample_rate:g} sps (response from {r.response_source.rsplit('/', 1)[-1]})"
    elif r.datalogger == "SiliconAudio":
        dl = f"Kelunji-format recorder, gain x{r.datalogger_gain:g} (419430.4 counts/V at x1)"
    else:
        dl = r.datalogger
    sens = SENSOR.get(r.sensor, ("", r.sensor))[1]
    if r.sensor in ("infraBSU", "Chaparral", "TCP", "L-22", "SmartSolo"):
        corr = f" x{r.sensitivity_correction:.4g} measured" if r.sensitivity_correction != 1 else ""
        sens += f", {r.sensor_V_per_unit:g} V/{'Pa' if r.units == 'Pa' else '(m/s)'}{corr}"
    if r.polarity == "reversed":
        sens += ", polarity reversed"
    return dl, sens


def make_channel(r, tpl):
    dl, sens = describe(r)
    if r.datalogger == "Centaur":
        dl_serial = r.datalogger_serial or None
    else:
        dl_serial = r.datalogger_serial or None
    if str(r.response_source).startswith("copy:"):
        old = tpl.old.select(network=r.network, station=r.station, channel=r.channel)
        cands = [c for n in old for s in n for c in s]
        ch = copy.deepcopy(cands[0])
        ch.start_date, ch.end_date = UTCDateTime(r.start), (UTCDateTime(r.end) if r.end else None)
        ch.latitude, ch.longitude = float(r.latitude), float(r.longitude)
        ch.data_logger = Equipment(type="datalogger", description=f"Raspberry Shake/Boom {r.datalogger}")
        ch.sensor = Equipment(type="sensor", description=f"Raspberry Shake/Boom {r.datalogger} ({r.channel})")
    else:
        ch = Channel(code=r.channel, location_code=r.location, latitude=float(r.latitude),
                     longitude=float(r.longitude), elevation=float(r.elevation), depth=float(r.depth),
                     azimuth=float(r.azimuth), dip=float(r.dip), sample_rate=float(r.sample_rate),
                     start_date=UTCDateTime(r.start), end_date=UTCDateTime(r.end) if r.end else None)
        ch.response = build_response(r, tpl)
        man, model = DATALOGGER.get(r.datalogger, ("", r.datalogger))
        ch.data_logger = Equipment(type="datalogger", description=dl, manufacturer=man, model=model,
                                   serial_number=dl_serial)
        sman, smodel = SENSOR.get(r.sensor, ("", r.sensor))
        ch.sensor = Equipment(type="sensor", description=sens, manufacturer=sman, model=smodel,
                              serial_number=r.sensor_serial or None)
    ch.description = f"{ch.sensor.description} | {ch.data_logger.description}"
    for label, text in (("status", "" if r.status == "ok" else r.status), ("change", r.change),
                        ("evidence", r.evidence), ("notes", r.notes)):
        if text:
            ch.comments.append(Comment(f"{label}: {text}"))
    return ch


def build(sheet, out):
    df = load_sheet(sheet)
    check(df)
    tpl = Templates()
    nets = {}
    for (net, sta), g in df.groupby(["network", "station"]):
        g = g.sort_values("start")
        # station epochs: union of channel epochs; a gap longer than one day starts a new epoch
        groups, cur, cur_end = [], [], None
        for _, r in g.iterrows():
            end = r.end or "2599-12-31T23:59:59"
            if cur and r.start > (UTCDateTime(cur_end) + 86400).isoformat()[:19]:
                groups.append(cur)
                cur, cur_end = [], None
            cur.append(r)
            cur_end = max(cur_end or end, end)
        groups.append(cur)
        for rows in groups:
            first = rows[0]
            ends = [r.end for r in rows]
            st = Station(code=sta, latitude=float(first.latitude), longitude=float(first.longitude),
                         elevation=float(first.elevation), start_date=UTCDateTime(min(r.start for r in rows)),
                         end_date=None if "" in ends else UTCDateTime(max(ends)),
                         site=Site(name=sta, description="; ".join(sorted({
                             f"{r.datalogger} {r.datalogger_serial}".strip() + " + " + r.sensor for r in rows}))),
                         creation_date=UTCDateTime(min(r.start for r in rows)))
            for r in rows:
                st.channels.append(make_channel(r, tpl))
            nets.setdefault(net, []).append(st)
    inv = Inventory(networks=[Network(code=n, stations=s, description={
        "1R": "USF / KSC rocket seismo-acoustic network", "AM": "Raspberry Shake",
        "XA": "MSFC accelerometer (temporary, 2022)", "DG": "MSFC instruments co-located with the KSC network"}.get(n, ""))
        for n, s in sorted(nets.items())], source="build_ksc_stationxml.py (ksc_stations_master_v3.xlsx)")
    inv.write(str(out), format="STATIONXML", validate=True)
    n = sum(len(s.channels) for net in inv for s in net)
    print(f"wrote {out}: {len(inv.networks)} networks, {sum(len(x) for x in inv)} station epochs, {n} channel epochs")
    return inv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=str(HERE / "ksc_stations_master_v3.xlsx"))
    ap.add_argument("--out", default=str(HERE / "KSC.xml"))
    a = ap.parse_args()
    try:
        build(a.sheet, a.out)
    except SheetError as e:
        sys.exit(f"[sheet error]\n{e}")
