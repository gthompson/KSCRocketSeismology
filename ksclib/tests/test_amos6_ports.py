"""Tests for the modules copied from the AMOS-6 paper: physics, weather, pressure, kml."""
import numpy as np
import pandas as pd
import pytest
from obspy import Stream, Trace, UTCDateTime

from ksclib import physics, pressure, weather
from ksclib.kml import read_kml_points


def test_sound_speed():
    assert physics.compute_speed_of_sound(20.0) == pytest.approx(343.42, abs=0.01)
    assert physics.fahrenheit_to_celsius(212.0) == pytest.approx(100.0)
    # Cramer (1993): dry air at 20 C, 1 atm, 400 ppm CO2 is ~343.2 m/s
    c = physics.compute_speed_of_sound_cramer(20.0, 0.0, 101325.0, 400.0)
    assert 342.8 < c < 343.6
    with pytest.raises(ValueError):
        physics.compute_speed_of_sound_cramer(40.0, 50.0, 101325.0, 400.0)


def test_shock_speed():
    assert physics.shock_mach_number(0.0) == pytest.approx(1.0)
    m = physics.shock_mach_number(1000.0)
    assert 1.0 < m < 1.005                         # 1 kPa is a weak shock
    r = physics.mach_vs_overpressure(reference_distance=1000.0, reference_overpressure=100.0)
    assert r["path_average_speed_mps"] > r["local_speed_at_array_mps"] > 348.8
    with pytest.raises(ValueError):
        physics.shock_mach_number(-1.0)


def test_wind_along_ray():
    # wind FROM the south (180) blows north: full tailwind on a northward ray
    out = physics.effective_sound_speed_along_ray(68.0, wind_direction_from_deg=180.0,
                                                  wind_speed_knots=10.0, ray_azimuth_deg=0.0)
    assert out["wind_along_ray_mps"] == pytest.approx(5.14444, rel=1e-4)
    assert out["acoustic_speed_with_wind_mps"] == pytest.approx(out["speed_of_sound_still_air_mps"] + 5.14444,
                                                                rel=1e-6)
    spd, frm = weather.wind_from_uv(0.0, 5.0)    # blowing north = from the south
    assert spd == pytest.approx(5.0) and frm == pytest.approx(180.0)
    assert weather.along_ray_wind_component(3.0, 4.0, 90.0) == pytest.approx(3.0)


def _weather_frame():
    t = pd.date_range("2026-05-29 00:30", periods=6, freq="10min", tz="UTC")
    rows = []
    for ti in t:
        for h in (6.0, 54.0, 204.0):
            rows.append({"datetime_utc": ti, "height_m": h * 0.3048, "wind_speed_knots": 10.0,
                         "wind_direction_from_deg": 90.0, "temperature_c": 25.0, "temperature_f": 77.0,
                         "relative_humidity_percent": 80.0})
    df = pd.DataFrame(rows)
    df["wind_speed_mps"] = df.wind_speed_knots * weather.KNOT_TO_MPS
    d = np.deg2rad(df.wind_direction_from_deg)
    df["wind_u_east_mps"] = -df.wind_speed_mps * np.sin(d)
    df["wind_v_north_mps"] = -df.wind_speed_mps * np.cos(d)
    return df


class _Ev:
    name = "test"
    origin_time = UTCDateTime(2026, 5, 29, 1, 0, 30)


def test_weather_profiles():
    df = _weather_frame()
    sub = weather.event_weather_window(df, _Ev(), before_s=600, after_s=600)
    assert sub.datetime_utc.min() >= pd.Timestamp("2026-05-29 00:50:30", tz="UTC")
    s = weather.summarize_wind(df)
    assert s.vector_mean_direction_from_deg == pytest.approx(90.0)
    prof = weather.make_height_profile(df)
    summ = weather.calculate_acoustic_summary(df, height_profile=prof, maximum_path_height_m=50.0,
                                              ray_azimuth_deg=270.0, propagation_distance_m=10000.0)
    # easterly wind is a tailwind on a westward ray
    assert summ["wind_along_ray_mps"] == pytest.approx(10 * weather.KNOT_TO_MPS, rel=1e-6)
    assert summ["wind_corrected_travel_time_s"] < summ["still_air_travel_time_s"]


def test_reduced_pressures():
    t0 = _Ev.origin_time
    st = Stream()
    for sta, dist, amp in (("A", 1000.0, 10.0), ("B", 2000.0, 5.0)):
        data = np.zeros(1000) + 3.0             # 3 Pa offset removed by the baseline
        data[600] += amp
        data[610] -= amp / 2
        st += Trace(data, header=dict(network="XX", station=sta, channel="DD0", sampling_rate=10.0,
                                      starttime=t0 - 30))
    stations = pd.DataFrame({"distance_km": [1.0, 2.0]}, index=["A", "B"])
    res = pressure.event_reduced_pressures(st, _Ev(), stations=stations, baseline=(-20, -1))
    assert list(res.station) == ["A", "B"]
    assert np.allclose(res.positive_peak_pa, [10.0, 5.0])
    assert np.allclose(res.positive_reduced_pa, [10.0, 10.0])   # 1/r spreading undone
    assert np.allclose(res.positive_peak_time_s, [30.0, 30.0])
    # channel keyed, as in AMOS-6
    res2 = pressure.measure_reduced_pressures(st.select(station="A"), {"DD0": 500.0},
                                              baseline_start_s=0, baseline_end_s=5)
    assert res2.iloc[0].positive_reduced_pa == pytest.approx(5.0)


def test_kml(tmp_path):
    p = tmp_path / "pts.kml"
    p.write_text('<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
                 '<Placemark><name>LC36</name><Point><coordinates>-80.5422,28.470556,0</coordinates>'
                 '</Point></Placemark></Document></kml>')
    pts = read_kml_points(p)
    assert pts["LC36"]["lat"] == pytest.approx(28.470556) and pts["LC36"]["lon"] == pytest.approx(-80.5422)


def test_iem_asos(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("station,valid,lon,lat,tmpf,dwpf,relh,drct,sknt,mslp,alti\n"
                 "XMR,2026-05-29 00:55,-80.5668,28.4677,81.00,75.70,84.01,300.00,9.00,1013.50,29.92\n"
                 "TTS,2026-05-29 01:00,-80.6944,28.6149,78.80,75.20,88.78,0.00,0.00,1014.30,29.94\n")
    df = weather.load_iem_asos_csv(p)
    assert df.temperature_c.iloc[0] == pytest.approx(27.222, abs=1e-3)
    assert df.wind_u_east_mps.iloc[0] > 0 and df.wind_v_north_mps.iloc[0] < 0   # from WNW -> toward ESE
    assert df.wind_speed_mps.iloc[1] == 0
    assert df.sea_level_pressure_pa.iloc[0] == pytest.approx(101350.0)


def test_event_airwave_speeds():
    stations = pd.DataFrame({"distance_km": [10.0, 10.0], "azimuth_deg": [0.0, 180.0]}, index=["N", "S"])
    out = physics.event_airwave_speeds(None, 20.0, 0.0, wind_v_north_mps=5.0, stations=stations)
    assert out.loc["N", "wind_along_ray_mps"] == pytest.approx(5.0)
    assert out.loc["S", "c_eff_mps"] == pytest.approx(out.loc["S", "c0_mps"] - 5.0)
    assert out.loc["N", "travel_time_s"] < out.loc["S", "travel_time_s"]
    c = physics.event_airwave_speeds(None, 20.0, 0.0, stations=stations, pressure_pa=101325.0).c0_mps.iloc[0]
    assert 342.8 < c < 343.6


def test_reference_clipping():
    from ksclib import clipping
    t0 = UTCDateTime(2026, 5, 29)
    rng = np.random.default_rng(0)
    ref = np.sin(np.linspace(0, 40 * np.pi, 4000)) * np.r_[np.ones(2000) * 50, np.ones(2000)] \
        + 0.01 * rng.standard_normal(4000)
    clipped = np.clip(0.05 * ref, -1.5, 1.5)                    # sensor at 1/20 the scale, clips at 1.5
    hdr = dict(sampling_rate=100.0, starttime=t0)
    a, b = Trace(clipped, header=hdr), Trace(ref, header=hdr)
    g, lag, r = clipping.fit_reference_gain(a, b, t0 + 25, t0 + 39)
    assert g == pytest.approx(0.05, rel=0.02) and lag == 0 and r > 0.99
    iv = clipping.reference_clip_intervals(a, b, g, (t0 + 25, t0 + 39))
    assert iv and all(s >= t0 and e <= t0 + 20.01 for s, e in iv)       # only the large first half
    raw = Trace(np.clip(ref * 1e5, -2e6, 2e6), header=hdr)
    assert clipping.count_saturation_intervals(raw, full_scale=2e6)


def test_atmospheric_absorption():
    # ISO 9613-1 tabulated values at 20 C, 70% RH, 101.325 kPa: 250 Hz 1.13, 1 kHz 4.98, 4 kHz 22.9 dB/km
    a = physics.atmospheric_absorption_db_per_m([250.0, 1000.0, 4000.0], 20.0, 70.0) * 1000
    assert a == pytest.approx([1.13, 4.98, 22.9], rel=0.02)
    assert np.all(np.diff(physics.atmospheric_absorption_db_per_m([10, 50, 100, 500], 26.0, 87.0)) > 0)
