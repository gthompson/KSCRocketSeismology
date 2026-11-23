"""Centaur-only correction with a response-file fallback and the Chaparral M25 infrasound sensor.

`ksclib.responses.centaur_response_file` needs a response XML written before the event.
Some stations have none (e.g. B14 for the New Glenn explosion: its first file is dated
two weeks later), so `centaur_response_file_nearest` falls back to the earliest file
after the event, with a warning. `instrument_correct_centaur` corrects Trillium (DH?),
infraBSU and Chaparral channels using that fallback; use `ksclib.instrument_correct`
for Gems and SmartSolos.

The Chaparral sensitivity is set in the event YAML::

    responses:
      chaparral: {channels: [DDF], V_per_Pa: 0.4}

and modelled as a flat stage (the M25 passband is far wider than the band studied).
"""
from __future__ import annotations

import copy
import re
import warnings
from pathlib import Path

from obspy import Stream, UTCDateTime, read_inventory
from obspy.core.inventory.response import PolesZerosResponseStage



def _response_files(event, station):
    out = []
    for d in event.centaur_response_dirs:
        for p in Path(d).glob(f"1R.{station}_*Z.xml"):
            m = re.match(rf"1R\.{station}_(\d{{8}}T\d{{6}})Z\.xml$", p.name)
            if m:
                out.append((UTCDateTime(m.group(1)), p))
    return sorted(out)


def centaur_response_file_nearest(event, station, when=None):
    """Latest Centaur response file at or before `when`; else the earliest after it (warns)."""
    when = when or event.origin_time
    files = _response_files(event, station)
    if not files:
        raise FileNotFoundError(f"No Centaur response files for {station}")
    before = [f for f in files if f[0] <= when]
    if before:
        return before[-1][1]
    t, p = files[0]
    warnings.warn(f"{station}: no Centaur response before {when}; using {p.name} "
                  f"({(t - when) / 86400:.1f} days later)")
    return p


def chaparral_config(event):
    c = (event.raw.get("responses", {}) or {}).get("chaparral", {}) or {}
    return dict(channels=tuple(c.get("channels", ("DDF",))), V_per_Pa=float(c.get("V_per_Pa", 0.4)))


def _flat_sensor_stage(gain, input_units="Pa"):
    return PolesZerosResponseStage(
        stage_sequence_number=1, stage_gain=gain, stage_gain_frequency=1.0,
        input_units=input_units, output_units="V", pz_transfer_function_type="LAPLACE (RADIANS/SECOND)",
        normalization_frequency=1.0, zeros=[], poles=[], normalization_factor=1.0)


def centaur_inventory_nearest(event, station, when=None):
    """Centaur inventory (nearest file) with infraBSU and Chaparral sensor stages prepended.

    infraBSU channels get the stage from event.infrabsu_xml (as ksclib.centaur_inventory);
    Chaparral channels get a flat stage of chaparral V_per_Pa.
    """
    when = when or event.origin_time
    path = centaur_response_file_nearest(event, station, when)
    inv = read_inventory(str(path))
    # a fallback file written after `when` has epochs starting after it: backdate them
    for obj in [n for n in inv] + [s for n in inv for s in n] + [c for n in inv for s in n for c in s]:
        if obj.start_date is not None and obj.start_date > when - 86400:
            obj.start_date = when - 86400
    bsu = read_inventory(str(event.infrabsu_xml))[0][0][0].response.response_stages[0]
    chap = chaparral_config(event)
    for net in inv:
        for sta in net:
            for cha in sta:
                if cha.code in event.infrabsu_channels:
                    stage = copy.deepcopy(bsu)
                elif cha.code in chap["channels"]:
                    stage = _flat_sensor_stage(chap["V_per_Pa"])
                else:
                    continue
                resp = cha.response
                resp.response_stages.insert(0, stage)
                for i, s in enumerate(resp.response_stages, 1):
                    s.stage_sequence_number = i
                resp.response_stages[1].input_units = "V"
                resp.instrument_sensitivity.input_units = "Pa"
                resp.instrument_sensitivity.value *= stage.stage_gain
                resp.recalculate_overall_sensitivity(1.0)
    return inv


def instrument_correct_centaur(st, event, pre_filt_low=(0.01, 0.02)):
    """Copy of the 1R Centaur traces in `st` in m/s (DH?) and Pa (infraBSU and Chaparral).

    Same processing as ksclib.instrument_correct for Centaur channels, but uses
    `centaur_inventory_nearest` and also corrects the Chaparral channels. Other
    channels are dropped; channels that cannot be corrected are dropped with a warning.
    """
    chap = chaparral_config(event)["channels"]
    out, inventories = Stream(), {}
    for tr in st:
        cha, sta = tr.stats.channel, tr.stats.station
        is_p = cha in event.infrabsu_channels or cha in chap
        if tr.stats.network != "1R" or not (cha.startswith("DH") or is_p):
            continue
        t = tr.copy()
        nyq = 0.5 * t.stats.sampling_rate
        try:
            if sta not in inventories:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    inventories[sta] = centaur_inventory_nearest(event, sta)
                for m in w:
                    warnings.warn(str(m.message))
            t.detrend("linear")
            t.remove_response(inventory=inventories[sta], output="DEF" if is_p else "VEL",
                              pre_filt=(*pre_filt_low, 0.94 * nyq, 0.98 * nyq), zero_mean=True, taper=True)
        except Exception as exc:
            warnings.warn(f"{tr.id}: not corrected ({type(exc).__name__}: {exc})")
            continue
        out.append(t)
    return out

