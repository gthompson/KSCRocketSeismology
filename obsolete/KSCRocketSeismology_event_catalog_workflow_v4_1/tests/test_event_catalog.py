from pathlib import Path
import pandas as pd
from kscrockets.event_catalog import normalize_event_type, add_manual_event, read_manual_events_csv, reconcile_sources


def test_event_types():
    assert normalize_event_type("static test") == "static_fire"
    assert normalize_event_type("abort") == "aborted_launch"
    assert normalize_event_type("pad explosion") == "pad_explosion"
    assert normalize_event_type("SonicBAT aircraft sonic boom") == "aircraft_sonic_boom"


def test_add_manual_event(tmp_path):
    p=tmp_path/'manual.csv'
    eid=add_manual_event(p,'aircraft_sonic_boom','2017-08-22T18:34:12.4Z','boom 1')
    df=read_manual_events_csv(p)
    assert df.iloc[0].event_id == eid
    assert df.iloc[0].event_type == 'aircraft_sonic_boom'


def test_reconciliation_flags_time_conflict():
    a=pd.DataFrame([dict(source_name='manual_excel',source_event_id='',source_name_value='AFSPC-6',event_type='orbital_launch',time_utc='2016-08-19T04:52:00Z',precision='minute',time_definition='manual',quality='curated_manual',pad='40',vehicle_mission='Delta IV AFSPC-6',notes='',source_url='')])
    b=pd.DataFrame([dict(source_name='api',source_event_id='x',source_name_value='Delta IV AFSPC-6',event_type='orbital_launch',time_utc='2016-08-19T04:47:00Z',precision='minute',time_definition='net',quality='success',pad='40',vehicle_mission='Delta IV AFSPC-6',notes='',source_url='')])
    ev,src=reconcile_sources([a,b])
    assert len(ev)==1
    assert bool(ev.iloc[0].time_conflict)
    assert ev.iloc[0].time_spread_s == 300


def test_scheduled_ll2_time_attaches_but_does_not_create_event():
    manual=pd.DataFrame([dict(source_name='manual_excel',source_event_id='',source_name_value='Falcon 9 AMOS-6',event_type='pad_explosion',time_utc='2016-09-01T13:07:15Z',precision='second',time_definition='observed explosion',quality='curated_manual',pad='40',vehicle_mission='Falcon 9 AMOS-6',notes='',source_url='',time_role='actual_event_time')])
    ll2=pd.DataFrame([dict(source_name='launch_library_2',source_event_id='amos6',source_name_value='Falcon 9 Full Thrust | Amos 6 (Failure before launch)',event_type='launch_failure',time_utc='2016-09-03T07:00:00Z',precision='minute',time_definition='LL2 NET/T-0',quality='Launch Failure',pad='Space Launch Complex 40',vehicle_mission='Falcon 9 Full Thrust | Amos 6',notes='',source_url='',time_role='scheduled_launch_time')])
    ev,src=reconcile_sources([manual,ll2])
    assert len(ev)==1
    assert ev.iloc[0].event_type == 'pad_explosion'
    assert ev.iloc[0].event_time_utc.startswith('2016-09-01T13:07:15')
    assert ev.iloc[0].source_count == 1
    assert ev.iloc[0].scheduled_time_count == 1
    assert set(src.time_role)=={'actual_event_time','scheduled_launch_time'}


def test_source_cache_roundtrip(tmp_path):
    from kscrockets.event_catalog import write_source_cache, read_source_cache
    p=tmp_path/'ll2.csv'
    original=pd.DataFrame([{'source_name':'launch_library_2','source_event_id':'abc','time_utc':'2016-08-14T05:26:00Z'}])
    write_source_cache(original,p,'launch_library_2')
    got=read_source_cache(p)
    assert got.iloc[0].source_event_id == 'abc'
    assert got.iloc[0].cache_source == 'launch_library_2'


def test_refresh_ll2_uses_existing_cache_on_429(tmp_path, monkeypatch):
    import urllib.error
    import kscrockets.event_catalog as ec
    p=tmp_path/'ll2.csv'
    cached=pd.DataFrame([{'source_name':'launch_library_2','source_event_id':'old','time_utc':'2016-08-14T05:26:00Z'}])
    ec.write_source_cache(cached,p,'launch_library_2')
    def fail(*args, **kwargs):
        raise urllib.error.HTTPError('x',429,'Too Many Requests',{},None)
    monkeypatch.setattr(ec,'fetch_ll2',fail)
    got,status=ec.refresh_ll2_cache('2016-01-01','2016-12-31',p)
    assert got.iloc[0].source_event_id == 'old'
    assert '429' in status
