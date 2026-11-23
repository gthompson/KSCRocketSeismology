"""New Glenn explosion configuration for the notebooks in this folder.

A thin wrapper over the shared `ksclib` package: all event-specific settings live in
newglenn.yaml (edit that, not the notebooks, when a drive or folder moves), and the code
lives in ksclib and flovopy. Names follow artemis2_config.py where they apply.
"""
from __future__ import annotations

from pathlib import Path

import ksclib
from ksclib import centaur
from flovopy.ingest import gem_overflow as _gem

PAPER_DIR = Path(__file__).resolve().parent
EVENT = ksclib.load_event(PAPER_DIR / "newglenn.yaml")

ORIGIN = EVENT.origin_time            # provisional; see 22_data_overview.ipynb
PAD = EVENT.site_name
STARTTIME, ENDTIME = EVENT.starttime, EVENT.endtime
STARTTRIM, ENDTRIM = EVENT.starttrim, EVENT.endtrim
MASTER_SDS = EVENT.master_sds
OUT_DIR = EVENT.out_dir

POLARITY_REVERSED = set(EVENT.raw.get("polarity_reversed", []))

# Faulty channels, excluded from figures (B03's Centaur channels are faulty).
EXCLUDE_STATIONS_CENTAUR = {"B03"}


def station_table():
    return ksclib.station_table(EVENT)


def event_stream_raw(client=None, starttime=None, endtime=None):
    """Raw stream (USF Centaur, Gem and SmartSolo groups; only Centaur recorded on day 149)."""
    return ksclib.event_stream_raw(EVENT, client, starttime=starttime, endtime=endtime)


def instrument_correct(st, pre_filt_low=(0.01, 0.02), fix_polarity=True):
    """Centaur channels via ksclib.centaur (response fallback + Chaparral), others via ksclib.

    With `fix_polarity`, channels in newglenn.yaml `polarity_reversed` are sign-flipped.
    """
    out = centaur.instrument_correct_centaur(st, EVENT, pre_filt_low)
    other = st.select(channel="HD?") + st.select(channel="DP?")
    if len(other):
        out += ksclib.instrument_correct(other, EVENT, pre_filt_low)
    if fix_polarity:
        for tr in out:
            if tr.id in POLARITY_REVERSED:
                tr.data = -tr.data
    return out


def weather_at_origin():
    """Per-station means of the surface observations within weather.window_s of the origin,
    and their mean over weather.stations (temperature_c, rh, u, v, pressure_pa)."""
    from ksclib import weather
    w = EVENT.raw["weather"]
    wx = weather.load_iem_asos_csv(Path(str(w["file"]).replace("{base_dir}", str(PAPER_DIR))))
    sub = weather.event_weather_window(wx, EVENT, w.get("window_s", 1800), w.get("window_s", 1800))
    per = sub.groupby("station").agg(temperature_c=("temperature_c", "mean"),
                                     rh=("relative_humidity_percent", "mean"),
                                     u=("wind_u_east_mps", "mean"), v=("wind_v_north_mps", "mean"),
                                     pressure_pa=("sea_level_pressure_pa", "mean"),
                                     n=("temperature_c", "count"))
    return sub, per, per.loc[list(w["stations"])].mean()


def airwave_speeds(mean=None, wind=True):
    """Predicted airwave speed and travel time to every station (ksclib.physics.event_airwave_speeds)."""
    from ksclib import physics
    m = weather_at_origin()[2] if mean is None else mean
    return physics.event_airwave_speeds(EVENT, m["temperature_c"], m["rh"], m["u"] if wind else 0.0,
                                        m["v"] if wind else 0.0, stations=station_table(),
                                        pressure_pa=m["pressure_pa"])


def output_dir(name):
    d = OUT_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# Gem 16-bit overflow (flovopy.ingest.gem_overflow)
stream_clip_intervals = _gem.stream_clip_intervals
clip_mask = _gem.clip_mask
