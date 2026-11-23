"""Instrument responses: Centaur StationXML (+ infraBSU stage) and the SmartSolo geophone."""
from __future__ import annotations

import copy
import re
from pathlib import Path

import numpy as np
from obspy import UTCDateTime, read_inventory


def centaur_response_file(event, station, when=None):
    """Latest Centaur response XML (1R.<STA>_<YYYYMMDDTHHMMSS>Z.xml) written at or before `when`.

    Centaurs write a new file whenever their configuration changes. Trilliums are on
    Sensor A (40 Vpp, "Analog 1.0 gain"); infrasound sensors on Sensor B (1 Vpp,
    "Analog 40.0 gain").
    """
    when = when or event.origin_time
    best = None
    for d in event.centaur_response_dirs:
        for p in Path(d).glob(f"1R.{station}_*Z.xml"):
            m = re.match(rf"1R\.{station}_(\d{{8}}T\d{{6}})Z\.xml$", p.name)
            if not m:
                continue
            t = UTCDateTime(m.group(1))
            if t <= when and (best is None or t > best[0]):
                best = (t, p)
    if best is None:
        raise FileNotFoundError(f"No Centaur response for {station} before {when}")
    return best[1]


def centaur_inventory(event, station, when=None):
    """Centaur response inventory, with the infraBSU sensor stage prepended on the infraBSU channels.

    Converts DH? counts to m/s and infraBSU DD? counts to Pa (~735 counts/Pa at 1 Vpp).
    """
    inv = read_inventory(str(centaur_response_file(event, station, when)))
    sensor = read_inventory(str(event.infrabsu_xml))[0][0][0].response.response_stages[0]
    for net in inv:
        for sta in net:
            for cha in sta:
                if cha.code not in event.infrabsu_channels:
                    continue
                resp = cha.response
                stage = copy.deepcopy(sensor)
                resp.response_stages.insert(0, stage)
                for i, s in enumerate(resp.response_stages, 1):
                    s.stage_sequence_number = i
                resp.response_stages[1].input_units = "V"
                resp.instrument_sensitivity.input_units = "Pa"
                resp.instrument_sensitivity.value *= stage.stage_gain
                resp.recalculate_overall_sensitivity(1.0)
    return inv


def smartsolo_paz(event):
    """Nominal SmartSolo geophone PAZ (velocity in m/s -> mV); harvested data are geophone mV."""
    g = event.smartsolo_geophone
    w0 = 2 * np.pi * g["f0"]
    poles = list(np.roots([1, 2 * g["damping"] * w0, w0 ** 2]))
    return {"poles": poles, "zeros": [0j, 0j], "gain": 1.0, "sensitivity": g["sensitivity_mV_per_mps"]}
