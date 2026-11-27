import sqlite3
from kscrockets.waveforms import select_events

def test_select_events(tmp_path):
    db=tmp_path/'test.sqlite'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE events (event_id TEXT,event_type TEXT,event_time_utc TEXT)')
        con.executemany('INSERT INTO events VALUES (?,?,?)', [('a','orbital_launch','2016-01-01T00:00:00Z'),('b','pad_explosion','2016-02-01T00:00:00Z')])
    assert [r['event_id'] for r in select_events(db,event_types=['pad_explosion'])]==['b']
    assert [r['event_id'] for r in select_events(db,event_id='a')]==['a']

from kscrockets.waveforms import discover_channels

def test_discovery_crosses_midnight_and_caches():
    import pytest
    UTCDateTime = pytest.importorskip("obspy").UTCDateTime
    class FakeClient:
        def __init__(self): self.calls=[]
        def get_all_nslc(self, datetime=None):
            self.calls.append(str(datetime.date))
            return [('1R','BCHH','10','DD3')] if datetime.date == UTCDateTime('2016-09-01').date else [('1R','BCHH','10','DHZ')]
    client=FakeClient(); cache={}
    a=UTCDateTime('2016-09-01T23:59:50'); b=a+20
    expected=['1R.BCHH.10.DD3','1R.BCHH.10.DHZ']
    assert discover_channels(client,a,b,cache)==expected
    assert discover_channels(client,a,b,cache)==expected
    assert len(client.calls)==2

def test_discovery_filters_station_and_low_rate():
    import pytest
    UTCDateTime = pytest.importorskip("obspy").UTCDateTime
    class FakeClient:
        def get_all_nslc(self, datetime=None):
            return [('1R','BCHH','10','DD3'),('1R','BCHH','10','LHZ'),('1R','OTHER','10','DD3')]
    t=UTCDateTime('2016-09-01')
    assert discover_channels(FakeClient(),t,t+10,station='BCHH',skip_low_rate=True)==['1R.BCHH.10.DD3']


def test_sds_availability_and_gaps(tmp_path):
    import pandas as pd
    from kscrockets.availability import Archive, sds_day_index, event_availability, coverage_gaps
    for sta, doy in (("BCHH", "036"), ("BCHH", "037"), ("FIRE", "036")):
        d = tmp_path / "2016" / "1R" / sta / "DHZ.D"; d.mkdir(parents=True, exist_ok=True)
        (d / f"1R.{sta}.00.DHZ.D.2016.{doy}").touch()
    idx = {str(tmp_path): sds_day_index(tmp_path)}
    arch = [Archive.parse(f"2016-01-01:2017-01-01:{tmp_path}")]
    ev = pd.DataFrame([dict(event_id="a", event_time_utc="2016-02-05T13:38:00Z", event_type="orbital_launch", name="x"),
                       dict(event_id="b", event_time_utc="2016-02-05T23:55:00Z", event_type="orbital_launch", name="y"),
                       dict(event_id="c", event_time_utc="2023-02-05T00:00:00Z", event_type="orbital_launch", name="z")])
    t = event_availability(ev, arch, idx).set_index("event_id")
    assert t.loc["a", "stations"] == "1R.BCHH;1R.FIRE"
    assert t.loc["b", "stations"] == "1R.BCHH"          # window crosses midnight; FIRE lacks day 037
    assert t.loc["c", "archive"] == "" and t.loc["c", "n_stations"] == 0
    gaps = coverage_gaps(idx, "2016-02-01", "2016-02-10")
    assert gaps.to_dict("records") == [dict(first_day="2016-02-01", last_day="2016-02-04", n_days=4),
                                       dict(first_day="2016-02-07", last_day="2016-02-09", n_days=3)]


def test_availability_counts_stored_as_integers(tmp_path):
    """A CSV re-attached as strings must still give numeric counts: '0' > 0 is true in sqlite."""
    import sqlite3
    import pandas as pd
    from kscrockets.availability import write_availability_table
    t = pd.DataFrame(dict(event_id=["a", "b"], n_stations=["0", "3"], n_channels=["", "9"]))
    db = tmp_path / "c.sqlite"
    write_availability_table(db, t)
    with sqlite3.connect(db) as con:
        assert con.execute("select count(*) from event_waveform_availability where n_stations > 0").fetchone()[0] == 1
