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
