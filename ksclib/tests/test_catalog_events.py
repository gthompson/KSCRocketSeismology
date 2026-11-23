"""Tests for ksclib.catalog_events (launch-catalog rows -> Events).

The unit tests build a small StationXML, pad table, sqlite catalog and ensemble file in a temporary
folder, so they need no drives. The integration test at the end reads a 2016 launch from the
2016–2022 SDS archive and is skipped when that drive is not mounted.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from obspy import Stream, Trace, UTCDateTime
from obspy.core.inventory import Channel, Inventory, Network, Response, Station

from ksclib import catalog_events as ce

REPO = Path(__file__).resolve().parents[2]
ENSEMBLE_YAML = REPO / "07_ensemble_paper" / "ensemble.yaml"
PRESSURE_GAIN = 736.0         # counts/Pa
VELOCITY_GAIN = 3.0e8         # counts/(m/s)
FS = 100.0


def _channel(code, gain, units, start, end):
    resp = Response.from_paz([], [], gain, input_units=units, output_units="COUNTS")
    return Channel(code, "00", 28.57, -80.57, 0.0, 0.0, sample_rate=FS, response=resp,
                   start_date=UTCDateTime(start), end_date=UTCDateTime(end))


@pytest.fixture()
def setup(tmp_path):
    sta_a = Station("STA1", 28.5735, -80.5724, 0.0, start_date=UTCDateTime(2016, 1, 1),
                    end_date=UTCDateTime(2017, 1, 1),
                    channels=[_channel("HDF", PRESSURE_GAIN, "PA", "2016-01-01", "2017-01-01"),
                              _channel("HHZ", VELOCITY_GAIN, "M/S", "2016-01-01", "2017-01-01")])
    sta_old = Station("OLD1", 28.60, -80.60, 0.0, start_date=UTCDateTime(2014, 1, 1),
                      end_date=UTCDateTime(2015, 1, 1),
                      channels=[_channel("HDF", PRESSURE_GAIN, "PA", "2014-01-01", "2015-01-01")])
    inv = Inventory([Network("1R", stations=[sta_a, sta_old])], source="test")
    xml = tmp_path / "KSC_test.xml"
    inv.write(str(xml), format="STATIONXML")

    pd.DataFrame(dict(pad=["LC40", "LC39A"], lat=[28.562106, 28.608172],
                      lon=[-80.57718, -80.604336])).to_csv(tmp_path / "pads.csv", index=False)
    db = tmp_path / "cat.sqlite"
    with sqlite3.connect(db) as con:
        pd.DataFrame([
            dict(event_id="ksc-a", event_type="orbital_launch", event_time_utc="2016-03-04T23:35:00Z",
                 name="Falcon 9 1.2|F9-22 SES-9", pad="40", vehicle=""),
            dict(event_id="ksc-b", event_type="pad_explosion", event_time_utc="2016-09-01T13:07:00Z",
                 name="Falcon 9", pad="40", vehicle=""),
        ]).to_sql("events", con, index=False)
    (tmp_path / "sds").mkdir()
    (tmp_path / "ens.yaml").write_text(f"""
catalog: {{sqlite: "{{base_dir}}/cat.sqlite"}}
pads:
  files: ["{{base_dir}}/pads.csv"]
  extra: {{LC36: [28.470556, -80.5422]}}
window: {{pretrigger: 600, duration: 600, posttrigger: 0, trim_before: 30, trim_after: 300}}
output: {{dir: "{{base_dir}}/out"}}
eras:
  - name: early
    kind: stationxml
    start: 2016-01-01
    end: 2023-01-01
    sds: "{{base_dir}}/sds"
    stationxml: "{{base_dir}}/KSC_test.xml"
    channel_groups: {{USF: ["1R", "*", "*", "H??"]}}
    gem_channel_prefix: null
extra_events:
  - {{event_id: x-2026, event_type: orbital_launch, event_time_utc: 2026-04-01T22:35:12Z,
      name: "SLS Block 1 | Artemis II", pad: LC39B}}
""")
    ens = ce.load_ensemble(tmp_path / "ens.yaml")
    return ens, tmp_path


@pytest.mark.parametrize("value, code", [
    ("40", "LC40"), ("SLC-40", "LC40"), ("LC-39A", "LC39A"), ("LC39A", "LC39A"), ("39b", "LC39B"),
    ("Space Launch Complex 46", "LC46"), ("37B", "LC37B"), ("SLF", "SLF"), ("L1011", "L1011"),
    (None, ""), (float("nan"), ""),
])
def test_normalize_pad(value, code):
    assert ce.normalize_pad(value) == code


def test_load_ensemble(setup):
    ens, tmp = setup
    assert [e.name for e in ens.eras] == ["early"]
    assert set(ens.pads.index) == {"LC40", "LC39A", "LC36"}
    assert ce.pad_location(ens, "SLC-40") == pytest.approx((28.562106, -80.57718))
    with pytest.raises(KeyError):
        ce.pad_location(ens, "SLF")
    with pytest.raises(LookupError):
        ens.era_for("2024-06-01")


def test_load_catalog(setup):
    ens, _ = setup
    cat = ce.load_catalog(ens)
    assert list(cat.event_id) == ["ksc-a", "ksc-b", "x-2026"]
    assert list(cat.vehicle) == ["Falcon 9", "Falcon 9", "SLS"]
    assert list(cat.pad_code) == ["LC40", "LC40", "LC39B"]
    assert list(cat.era[:2]) == ["early", "early"] and pd.isna(cat.era[2])
    assert cat.event_time_utc.iloc[2] == "2026-04-01T22:35:12Z"
    assert len(ce.load_catalog(ens, event_types=["pad_explosion"])) == 1
    assert len(ce.load_catalog(ens, start="2016-06-01", extra=False)) == 1


def test_event_from_row(setup):
    ens, tmp = setup
    cat = ce.load_catalog(ens, extra=False)
    ev = ce.event_from_row(cat.iloc[0], ens)
    assert ev.origin_time == UTCDateTime("2016-03-04T23:35:00")
    assert ev.kind == "launch" and ev.site_name == "LC40"
    assert ev.site_lat == pytest.approx(28.562106)
    assert ev.starttime == ev.origin_time - 600 and ev.endtime == ev.origin_time + 600
    assert ev.master_sds == tmp / "sds"
    assert ev.raw["era"] == "early" and ev.raw["event_id"] == "ksc-a"
    assert ce.is_stationxml_event(ev)
    assert ev.out_dir == tmp / "out" / "ksc-a"
    assert ce.event_from_row(cat.iloc[1], ens).kind == "static"          # pad explosion
    ev2 = ce.event_from_row(cat.iloc[0], ens, launch_azimuth_deg=45.0)
    assert ev2.launch_azimuth_deg == 45.0
    with pytest.raises(AttributeError):
        ce.event_from_row(cat.iloc[0], ens, not_a_field=1)


def test_station_table_uses_active_epochs(setup):
    ens, _ = setup
    ev = ce.event_from_row(ce.load_catalog(ens, extra=False).iloc[0], ens)
    tab = ce.station_table(ev)
    assert list(tab.index) == ["STA1"]                  # OLD1 epoch ended in 2015
    assert tab.loc["STA1", "distance_km"] == pytest.approx(1.35, abs=0.02)


def _synthetic(ev, amp_pa=200.0, amp_v=1e-3):
    t0 = ev.origin_time - 300
    n = int(600 * FS)
    t = np.arange(n) / FS - 300.0                      # seconds after origin
    rng = np.random.default_rng(0)
    pulse = np.exp(-0.5 * ((t - 20.0) / 0.3) ** 2) * np.sin(2 * np.pi * 3.0 * (t - 20.0))
    pulse /= np.abs(pulse).max()
    noise_p = 0.5 * rng.standard_normal(n)
    noise_v = 1e-6 * rng.standard_normal(n)
    st = Stream()
    for cha, gain, sig in (("HDF", PRESSURE_GAIN, amp_pa * pulse + noise_p),
                           ("HHZ", VELOCITY_GAIN, amp_v * pulse + noise_v)):
        st += Trace((sig * gain).astype(np.int32).astype(float),
                    header=dict(network="1R", station="STA1", location="00", channel=cha,
                                sampling_rate=FS, starttime=t0))
    return st


def test_correct_and_peaks(setup):
    ens, _ = setup
    ev = ce.event_from_row(ce.load_catalog(ens, extra=False).iloc[0], ens)
    raw = _synthetic(ev)
    assert ce.clip_intervals(raw, ev) == {}                     # no Gems in this era
    st = ce.correct(raw, ev)
    assert {tr.stats.units for tr in st} == {"Pa", "m/s"}
    pk = ce.peak_amplitudes(st, ev, ce.station_table(ev), signal=(-30, 120)).set_index("channel")
    assert pk.loc["HDF", "kind"] == "pressure" and pk.loc["HHZ", "kind"] == "seismic_Z"
    assert pk.loc["HDF", "peak"] == pytest.approx(200.0, rel=0.1)
    assert pk.loc["HHZ", "peak"] == pytest.approx(1e-3, rel=0.1)
    assert pk.loc["HDF", "t_peak_s"] == pytest.approx(20.0, abs=0.3)
    assert pk.loc["HDF", "snr"] > 50
    assert pk.loc["HDF", "distance_km"] == pytest.approx(1.35, abs=0.02)
    assert not pk.lower_bound.any()

    # Mask the pulse as if a Gem overflowed: the peak drops and becomes a lower bound.
    sid = st.select(channel="HDF")[0].id
    clips = {sid: [(ev.origin_time + 19.0, ev.origin_time + 21.0)]}
    pk2 = ce.peak_amplitudes(st, ev, None, clips, signal=(-30, 120)).set_index("channel")
    assert pk2.loc["HDF", "lower_bound"] and pk2.loc["HDF", "peak"] < 20
    assert not pk2.loc["HHZ", "lower_bound"]


def test_correct_drops_channels_without_response(setup):
    ens, _ = setup
    ev = ce.event_from_row(ce.load_catalog(ens, extra=False).iloc[0], ens)
    raw = _synthetic(ev)
    raw[0].stats.station = "NOPE"
    with pytest.warns(UserWarning, match="no response"):
        st = ce.correct(raw, ev)
    assert [tr.stats.channel for tr in st] == ["HHZ"]


def test_gaps_are_split_and_peaks_combined(setup):
    ens, _ = setup
    ev = ce.event_from_row(ce.load_catalog(ens, extra=False).iloc[0], ens)
    raw = _synthetic(ev).select(channel="HDF")
    tr = raw[0]
    a = tr.slice(tr.stats.starttime, ev.origin_time + 10)
    b = tr.slice(ev.origin_time + 12, tr.stats.endtime)
    st = ce.correct(Stream([a, b]), ev)
    assert len(st) == 2
    pk = ce.peak_amplitudes(st, ev, signal=(-30, 120))
    assert len(pk) == 1 and pk.peak.iloc[0] == pytest.approx(200.0, rel=0.1)
    assert pk.coverage.iloc[0] < 1.0


# ---------------------------------------------------------------------------
# Integration: a real 2016 launch (skipped without the 2016–2022 SDS drive)
# ---------------------------------------------------------------------------
def test_real_2016_launch():
    ens = ce.load_ensemble(ENSEMBLE_YAML)
    era = ens.eras[0]
    if not (era.sds and era.sds.is_dir()):
        pytest.skip(f"{era.sds} not mounted")
    cat = ce.load_catalog(ens)
    row = cat[cat.event_id == "ksc-4d8977e0556d"].iloc[0]           # Falcon 9 SES-9, SLC-40
    ev = ce.event_from_row(row, ens)
    assert ev.site_name == "LC40" and ev.raw["era"] == "campaigns_2016_2022"
    tab = ce.station_table(ev)
    assert {"BCHH", "FIRE", "TANK"} <= set(tab.index)
    raw = ce.read_raw(ev, starttime=ev.origin_time - 120, endtime=ev.origin_time + 180)
    st = ce.correct(raw.select(station="BCHH"), ev)
    pk = ce.peak_amplitudes(st, ev, tab, signal=(-30, 150), noise=(-120, -30)).set_index("channel")
    assert pk.loc["DD1", "peak"] > 50 and pk.loc["DD1", "snr"] > 10      # Pa
    assert 1e-5 < pk.loc["DHZ", "peak"] < 1e-1                         # m/s
