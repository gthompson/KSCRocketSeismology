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
