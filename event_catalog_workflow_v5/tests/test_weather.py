"""kscrockets.weather: legacy tower format, surface summary, airport choice (no network)."""
import pandas as pd

from kscrockets.weather import airport_summary, file_time, load_ksc_tower_legacy, tower_summary

LEGACY = """USE CAUTION: ENSURE DATA IS REASONABLE
======= Start data file number ==>  1
WT010951559                                                     2019095 1600
CCAFS/KSC WIND TOWER DATA     1559Z  05 APR 19
                   01 MIN  01 MIN  10 MIN
                   AVERAGE PEAK    PEAK                TMP
TOWER       HGT AV DIR SPD DIR SPD DIR SPD DEV   TMP   DIF    DP  RH    PRE
            FT MIN DEG KTS DEG KTS DEG KTS DEG     F     F     F   %     MB
39 B NW     459 01 192  16 191  18 197  22 002  73.4        65.7  77
0002 NW  SE  54 01 160  10 166  12 168  14 007  80.0    .2  76.8  90
0002 SE  SE  54 01 175  12 163  14 176  16 008  80.0    .1  77.5  92
0002 SE  SE  12 01 184   4 158   6 161   8 015
0002 SE  SE  06 01                              80.2
0108         54 01 999 999 999 999 999 999 999   999         999 999
======= Start data file number ==>  2
CCAFS/KSC WIND TOWER DATA     1558Z  05 APR 19
TOWER       HGT AV DIR SPD DIR SPD DIR SPD DEV   TMP   DIF    DP  RH    PRE
0002 SE  SE  54 01 170  11 163  14 176  16 008  79.9    .1  77.5  92
"""
COORDS = pd.DataFrame(dict(tower=["0002SE", "0108", "LC39BNW"], lat=[28.4443, 28.5359, 28.6272],
                           lon=[-80.5620, -80.6466, -80.6208]))


def test_legacy_tower_file(tmp_path):
    f = tmp_path / "T104051601.dat"
    f.write_text(LEGACY)
    d = load_ksc_tower_legacy([f], COORDS)
    assert sorted(d.datetime_utc.dt.strftime("%H%M").unique()) == ["1558", "1559"]
    x = d[d.datetime_utc == pd.Timestamp("2019-04-05T15:59Z")].set_index(["station", "height_ft"])
    assert ("0002", 54) in x.index and len(x.loc[("0002", 54)].shape) == 1     # NW side dropped (prevailing SE)
    assert x.loc[("0002", 54), "relative_humidity_percent"] == 92
    assert abs(x.loc[("0002", 54), "wind_speed_knots"] - 12) < 1e-9 and x.loc[("0002", 54), "tower_latitude"] == 28.4443
    assert x.loc[("LC39B", 459), "temperature_f"] == 73.4
    assert pd.isna(x.loc[("0108", 54), "wind_speed_knots"])                    # 999 = missing
    s = tower_summary(d[d.datetime_utc == pd.Timestamp("2019-04-05T15:59Z")], 28.4467, -80.5602)
    assert s["near_tower"] == "0002" and s["tower_temp_height_ft"] == "6"


def test_file_time_both_namings():
    assert file_time("WT_1MIN_202603141238.dat", "/midds/WINDS_TOWER/2026/03/14") == pd.Timestamp("2026-03-14T12:38Z")
    assert file_time("T104051601.dat", "/midds/WINDS_TOWER/2019/04/05") == pd.Timestamp("2019-04-05T16:01Z")


def test_airport_closest_in_time_among_cape_airports():
    t = pd.Timestamp("2026-03-14T12:37Z")
    a = pd.DataFrame(dict(station=["XMR", "TTS", "MLB"],
                          datetime_utc=pd.to_datetime(["2026-03-14T11:55Z", "2026-03-14T12:35Z", "2026-03-14T12:37Z"]),
                          tower_latitude=[28.47, 28.61, 28.10], tower_longitude=[-80.57, -80.69, -80.65],
                          temperature_c=[22.0, 22.5, 23.0], relative_humidity_percent=[80, 78, 70],
                          wind_speed_mps=[2.0, 2.5, 3.0], wind_direction_from_deg=[90, 100, 110]))
    s = airport_summary(a, t)
    assert s["airport"] == "TTS" and s["airport_offset_s"] == -120               # MLB is closer in time but 40 km away
