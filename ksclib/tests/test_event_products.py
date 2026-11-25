"""ksclib.event_products on synthetic traces (no archive needed)."""
import numpy as np
import pandas as pd
from obspy import Trace, UTCDateTime

from ksclib import event_products as ep

T0 = UTCDateTime("2026-01-01T00:00:00")


def _trace(arrival_s=20.0, amp=50.0, fs=100.0, start=-600.0, length=1200.0, units="Pa", cha="HDF", seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(length * fs)) / fs + start
    x = rng.normal(0, 0.5, t.size)
    burst = (t >= arrival_s) & (t < arrival_s + 30)
    x[burst] += amp * np.sin(2 * np.pi * 8.0 * t[burst]) * np.exp(-(t[burst] - arrival_s) / 10)
    tr = Trace(x, header=dict(network="1R", station="S1", location="00", channel=cha,
                              sampling_rate=fs, starttime=T0 + start))
    tr.stats.units = units
    return tr


def test_channel_metrics_finds_burst():
    tr = _trace()
    m = ep.channel_metrics(tr, T0, signal=(-30, 300), noise=(-330, -30), fc=0.5)
    assert 30 < m["peak"] < 60
    assert 20 <= m["t_peak_s"] < 25
    assert m["snr_peak"] > 10
    assert abs(m["f_dominant_hz"] - 8.0) < 0.5
    assert 0 < m["duration_5_95_s"] < 40
    assert m["spl_peak_db"] > 120


def test_stalta_takes_strongest_arrival_not_first_blip():
    tr = _trace(arrival_s=40.0)
    i = int((-200 + 600) * 100)
    tr.data[i:i + 30] += 4.0                     # small earlier blip
    onset, ratio = ep.stalta_onset(tr, T0, (-300, 600), fc=0.5)
    assert 39 < onset < 41.5 and ratio > 8


def test_detected_origin_prefers_pressure():
    on = pd.DataFrame([
        dict(kind="pressure", station="A", origin_est_s=-1.0, max_ratio=20),
        dict(kind="pressure", station="B", origin_est_s=-0.5, max_ratio=15),
        dict(kind="pressure", station="C", origin_est_s=90.0, max_ratio=5),      # below min_ratio
        dict(kind="seismic_Z", station="A", origin_est_s=-4.0, max_ratio=30),
    ])
    d = ep.detected_origin(on)
    assert d["n_stations"] == 2 and abs(d["offset_s"] + 0.75) < 1e-9 and "_pressure_" in d["method"]
    # two picks that disagree by 130 s: the stronger one wins, not their median
    on2 = pd.DataFrame([dict(kind="pressure", station="A", origin_est_s=-133.0, max_ratio=9, distance_km=4.7),
                        dict(kind="pressure", station="A", origin_est_s=-1.6, max_ratio=10, distance_km=4.7)])
    d2 = ep.detected_origin(on2)
    assert d2["offset_s"] == -1.6 and d2["n_channels_disagree"] == 1


def test_standard_metrics_and_vector_pgv():
    from obspy import Stream
    p = ep.channel_metrics(_trace(), T0, signal=(-30, 300), noise=(-330, -30), fc=0.5)
    for k in ("peak_positive", "peak_negative", "peak_to_peak", "sel_db", "leq_db", "dpdt_kurtosis",
              "band_2_8hz_mean_square", "band_low_hz", "band_high_hz"):
        assert k in p
    assert p["sel_db"] > p["leq_db"]                     # 330 s window: SEL = Leq + 10 log10(330)
    z = _trace(units="m/s", cha="HHZ", amp=1e-3, seed=1)
    n = _trace(units="m/s", cha="HHN", amp=2e-3, seed=2)
    e = _trace(units="m/s", cha="HHE", amp=2e-3, seed=3)
    s = ep.channel_metrics(z, T0, signal=(-30, 300), noise=(-330, -30), fc=1.0)
    assert s["pgv"] == s["peak"] and s["pga"] > s["pgv"] and s["pgd"] < s["pgv"]
    v = ep.vector_metrics(Stream([z, n, e]), T0, (-30, 300), 1.0)
    assert v["pgv_3c_vector"] >= v["pgv_horizontal_vector"] > 0 and v["vector_channels"] == "00.HH?"


def test_catalog_usable_only_for_pad_sources_near_the_pad():
    near = dict(nearest_km=1.4)
    assert ep.catalog_usable("orbital_launch", near)[0]
    assert not ep.catalog_usable("booster_landing", near)[0]
    assert not ep.catalog_usable("aborted_launch", dict(nearest_km=13.5))[0]
    assert not ep.catalog_usable("static_fire", {})[0]
    assert ep.catalog_usable("pad_explosion", dict(nearest_km=11.8))[0]      # stationary source


def test_detected_origin_strong_pick_beats_colocated_noise():
    on = pd.DataFrame([dict(kind="pressure", station="B2", origin_est_s=-585.0, max_ratio=15, distance_km=4.9),
                       dict(kind="pressure", station="B2", origin_est_s=-585.0, max_ratio=15, distance_km=4.9),
                       dict(kind="pressure", station="B2", origin_est_s=-1.5, max_ratio=29, distance_km=4.9)])
    d = ep.detected_origin(on)
    assert d["offset_s"] == -1.5 and d["rival_ratio"] == 15 / 29
    on.loc[0:1, "max_ratio"] = 27                 # rival nearly as strong: one station is ambiguous
    d = ep.detected_origin(on)
    assert not ep.catalog_usable("static_fire", d)[0]
