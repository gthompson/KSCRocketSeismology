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
