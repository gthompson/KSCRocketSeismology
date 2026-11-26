"""Instrument correction for the KSC instrument mix."""
from __future__ import annotations

import warnings

from obspy import Stream

from flovopy.ingest.gem_overflow import repair_gem_overflow
from .responses import centaur_inventory, smartsolo_paz
from .seedcodes import is_centaur, same_code


def instrument_correct(st, event, pre_filt_low=(0.01, 0.02)):
    """Copy of `st` in physical units: Centaur C/D/H H? m/s and infraBSU ?D? Pa, Gem HD? Pa, SmartSolo DP? m/s.

    Gem overflow intervals are repaired (bridged, baseline step removed) before the
    Gem correction; mask them afterwards with flovopy.ingest.gem_overflow.clip_mask.
    SmartSolo polarity is left as recorded (the vertical is reversed). Channels without
    a usable response are dropped. `pre_filt_low` sets the two low Centaur pre-filter corners.
    """
    import gemlog
    out = Stream()
    inventories = {}
    for tr in st:
        t = tr.copy()
        cha, sta = t.stats.channel, t.stats.station
        nyq = 0.5 * t.stats.sampling_rate
        try:
            seismic = is_centaur(t) and cha[1] == "H"
            infrabsu = is_centaur(t) and any(same_code(cha, c) for c in event.infrabsu_channels)
            if t.stats.network == "1R" and (seismic or infrabsu):
                inv = inventories.setdefault(sta, centaur_inventory(event, sta))
                t.detrend("linear")
                t.remove_response(inventory=inv, output="VEL" if seismic else "DEF",
                                  pre_filt=(*pre_filt_low, 0.94 * nyq, 0.98 * nyq), zero_mean=True, taper=True)
            elif cha.startswith("HD") and not is_centaur(t):
                t = repair_gem_overflow(t)
                t.detrend("demean")
                t.filter("highpass", freq=0.05)
                t = gemlog.deconvolve_gem_response(t, gain="high")
            elif cha.startswith("DP"):
                t.detrend("linear")
                t.simulate(paz_remove=smartsolo_paz(event), paz_simulate=None, remove_sensitivity=True,
                           pre_filt=(0.5, 1.0, 0.8 * nyq, 0.9 * nyq), taper=True)
            else:
                continue
        except Exception as exc:
            warnings.warn(f"{tr.id}: not corrected ({type(exc).__name__}: {exc})")
            continue
        out.append(t)
    return out
