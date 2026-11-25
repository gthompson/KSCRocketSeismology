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


def test_reconciliation_matches_against_all_cluster_members_and_uses_consensus_time():
    manual=pd.DataFrame([dict(source_name='manual_excel',source_event_id='',source_name_value='Falcon 9|F9-085 Spx-DM2 Endeavor',event_type='orbital_launch',time_utc='2020-05-30T08:53:00Z',precision='minute',time_definition='manual',quality='curated_manual',pad='39A',vehicle_mission='Falcon 9|F9-085 Spx-DM2 Endeavor',notes='',source_url='')])
    ll2=pd.DataFrame([dict(source_name='launch_library_2',source_event_id='dm2',source_name_value='Falcon 9 Block 5 | SpX-DM2 (Demonstration Mission 2)',event_type='orbital_launch',time_utc='2020-05-30T19:22:45Z',precision='second',time_definition='LL2 NET/T-0',quality='success',pad='Launch Complex 39A',vehicle_mission='Falcon 9 Block 5 | SpX-DM2 (Demonstration Mission 2)',notes='',source_url='')])
    gcat=pd.DataFrame([dict(source_name='gcat',source_event_id='2020-041',source_name_value='Dragon DM-2',event_type='orbital_launch',time_utc='2020-05-30T19:22:45Z',precision='second',time_definition='GCAT first motion',quality='OS',pad='LC39A',vehicle_mission='Falcon 9 FT5 | Dragon DM-2 | Dragon C206',notes='',source_url='')])
    ev,src=reconcile_sources([manual,ll2,gcat])
    assert len(ev)==1
    assert ev.iloc[0].source_count == 3
    assert ev.iloc[0].event_time_utc.startswith('2020-05-30T19:22:45')
    assert ev.iloc[0].event_time_source in {'launch_library_2','gcat'}
    assert bool(ev.iloc[0].time_conflict)


# ---------------------------------------------------------------------------
# 2016-present extension: LL2 detailed parsing, landings, ids, normalization
# ---------------------------------------------------------------------------
def _ll2_launch(id_, net, name, pad='Space Launch Complex 40', landing=None, timeline=None, location='Cape Canaveral SFS, FL, USA'):
    stages = []
    if landing:
        stages = [{'landing': {'attempt': True, 'success': True,
                               'landing_location': {'abbrev': landing[0]}, 'type': {'abbrev': landing[1]}}}]
    return {'id': id_, 'name': name, 'net': net, 'status': {'name': 'Launch Successful'},
            'launch_designator': '2024-001', 'launch_service_provider': {'name': 'SpaceX'},
            'mission': {'name': name.split('|')[-1].strip()},
            'rocket': {'configuration': {'full_name': name.split('|')[0].strip()}, 'launcher_stage': stages},
            'pad': {'name': pad, 'location': {'name': location}}, 'timeline': timeline or [], 'url': ''}


def test_ll2_rows_add_rtls_landing_and_skip_droneship():
    from kscrockets.event_catalog import ll2_rows_from_payloads
    launches = [
        _ll2_launch('a', '2024-01-01T00:00:00Z', 'Falcon 9 Block 5 | Crew-9', landing=('LZ-1', 'RTLS'),
                    timeline=[{'type': {'abbrev': 'Stage 1 Landing'}, 'relative_time': 'PT7M40S'}]),
        _ll2_launch('b', '2024-01-02T00:00:00Z', 'Falcon 9 Block 5 | Starlink Group 6-1', landing=('ASOG', 'ASDS')),
        _ll2_launch('c', '2024-01-03T00:00:00Z', 'Falcon 9 Block 5 | Starlink Group 7-1', pad='SLC-4E',
                    location='Vandenberg SFB, CA, USA'),
    ]
    events = [{'id': 7, 'type': {'id': 5}, 'name': 'Falcon 9 Static Fire', 'date': '2024-01-04T10:00:00Z',
               'location': 'LC-39A, KSC'},
              {'id': 8, 'type': {'id': 5}, 'name': 'Booster Static Fire', 'date': '2024-01-05T10:00:00Z',
               'location': 'Starbase, TX'}]
    df = ll2_rows_from_payloads(launches, events)
    assert sorted(df.event_type) == ['booster_landing', 'orbital_launch', 'orbital_launch', 'static_fire']
    land = df[df.event_type == 'booster_landing'].iloc[0]
    assert land.time_utc == '2024-01-01T00:07:40Z' and land.pad == 'LZ-1' and land.precision == 'second'
    assert land.source_event_id == 'a:landing'
    sf = df[df.event_type == 'static_fire'].iloc[0]
    assert sf.pad == 'LC39A' and sf.precision == 'approximate'
    assert df[df.source_event_id == 'b'].iloc[0].landing_type == 'ASDS'


def test_landing_without_timeline_uses_median_offset():
    from kscrockets.event_catalog import ll2_rows_from_payloads
    launches = [
        _ll2_launch('a', '2024-01-01T00:00:00Z', 'Falcon 9 Block 5 | A', landing=('LZ-1', 'RTLS'),
                    timeline=[{'type': {'abbrev': 'Stage 1 Landing'}, 'relative_time': 'PT8M'}]),
        _ll2_launch('b', '2024-02-01T00:00:00Z', 'Falcon 9 Block 5 | B', landing=('LZ-2', 'RTLS')),
    ]
    df = ll2_rows_from_payloads(launches)
    b = df[df.source_event_id == 'b:landing'].iloc[0]
    assert b.time_utc == '2024-02-01T00:08:00Z' and b.precision == 'estimated'


def test_launches_hours_apart_from_same_source_stay_separate():
    rows = [dict(source_name=s, source_event_id=f'{s}{i}', source_name_value=f'Falcon 9 Block 5 | Starlink Group 6-{i}',
                 event_type='orbital_launch', time_utc=t, precision='second', time_definition='', quality='',
                 pad='LC40', vehicle_mission=f'Falcon 9 Block 5 | Starlink Group 6-{i}', notes='', source_url='')
            for s in ('launch_library_2', 'gcat') for i, t in ((1, '2024-11-11T17:22:00Z'), (2, '2024-11-11T21:28:00Z'))]
    ev, src = reconcile_sources([pd.DataFrame(rows)])
    assert len(ev) == 2
    assert (src.groupby('event_id').source_name.nunique() == 2).all()


def test_booster_landing_does_not_merge_into_its_launch():
    launch = dict(source_name='launch_library_2', source_event_id='a', source_name_value='Falcon 9 | Crew-9',
                  event_type='orbital_launch', time_utc='2024-01-01T00:00:00Z', pad='Space Launch Complex 40',
                  vehicle_mission='Falcon 9 Block 5 | Crew-9')
    landing = dict(launch, source_event_id='a:landing', event_type='booster_landing',
                   time_utc='2024-01-01T00:07:40Z', pad='LZ-1')
    ev, _ = reconcile_sources([pd.DataFrame([launch, landing])])
    assert sorted(ev.event_type) == ['booster_landing', 'orbital_launch']
    assert set(ev.pad) == {'LC40', 'LZ1'}
    assert set(ev.vehicle) == {'Falcon 9'}


def test_curated_manual_event_wins_time_and_name_over_gcat():
    gcat = dict(source_name='gcat', source_event_id='2026-E01', source_name_value='NG3 7E03 | - | - | -',
                event_type='pad_explosion', time_utc='2026-05-29T01:00:00Z', precision='minute', pad='LC36',
                vehicle_mission='New Glenn 7x2 2 | NG3 7E03')
    manual = dict(source_name='waveform_review', source_event_id='ksc-ng', source_name_value='New Glenn static-fire explosion',
                  event_type='pad_explosion', time_utc='2026-05-29T01:00:02Z', precision='second', pad='LC36',
                  vehicle_mission='New Glenn | static fire explosion', persistent_event_id='ksc-ng')
    ev, _ = reconcile_sources([pd.DataFrame([gcat]), pd.DataFrame([manual])])
    assert len(ev) == 1
    e = ev.iloc[0]
    assert e.event_id == 'ksc-ng' and e.event_time_utc == '2026-05-29T01:00:02Z'
    assert e['name'] == 'New Glenn static-fire explosion' and e.vehicle == 'New Glenn' and e.pad == 'LC36'


def test_persistent_ids_survive_a_changed_preferred_record():
    from kscrockets.event_catalog import assign_persistent_ids, id_registry_from_sources
    a = dict(source_name='manual_excel', source_event_id='', source_name_value='Atlas V GPS', event_type='orbital_launch',
             time_utc='2016-02-05T13:38:00Z', pad='41', vehicle_mission='Atlas V GPS')
    ev1, src1 = reconcile_sources([pd.DataFrame([a])])
    registry = id_registry_from_sources(src1)
    # A new external record with another time now wins the consensus -> new hashed id ...
    b = dict(a, source_name='launch_library_2', source_event_id='x', time_utc='2016-02-05T13:38:30Z')
    c = dict(a, source_name='gcat', source_event_id='2016-007', time_utc='2016-02-05T13:38:30Z')
    ev2, src2 = reconcile_sources([pd.DataFrame([a, b, c])])
    assert ev2.iloc[0].event_id != ev1.iloc[0].event_id
    # ... but the registry restores the original one.
    ev3, src3, report = assign_persistent_ids(ev2, src2, registry)
    assert ev3.iloc[0].event_id == ev1.iloc[0].event_id
    assert set(src3.event_id) == {ev1.iloc[0].event_id}
    assert report['kept'] == 1 and report['new'] == 0


def test_gcat_E_tag_is_pad_explosion():
    from kscrockets.event_catalog import read_gcat_tsv_bytes
    header = ("#Launch_Tag\tLaunch_JD\tLaunch_Date\tLV_Type\tVariant\tFairing\tFlight_ID\tFlight\tMission\tFlightCode\tPlatform\t"
              "Launch_Site\tLaunch_Pad\tAscent_Site\tAscent_Pad\tPerigee\tApogee\tApoflag\tInc\tAzimuth\tRange\tRangeFlag\tDest\t"
              "OrbMass\tOrbPay\tAgency\tLaunchCode\tFailCode\tGroup\tCategory\tLTCite\tCite\tNotes\n")
    row = "2026-E01\t0\t2026 May 29 0100\tNew Glenn\t7x2 2\t-\tNG3 7E03\t-\t-\t-\t-\tCC\tLC36" + "\t-" * 13 + "\tOE\t-\t-\t-\t-\t-\t-\n"
    df = read_gcat_tsv_bytes((header + row).encode())
    assert df.iloc[0].event_type == 'pad_explosion'


# --- expansion: new event types, LL2 events/updates, time fields -------------------------------

def _rec(**kw):
    base = dict(source_name='x', source_event_id='', source_name_value='', event_type='orbital_launch',
                time_utc='2022-08-29T12:33:00Z', precision='minute', time_definition='', quality='', pad='LC39B',
                vehicle_mission='', notes='', source_url='', time_role='actual_event_time')
    base.update(kw); return base


def test_scrub_does_not_cluster_with_launch_but_pad_abort_does_with_scrub():
    launch = pd.DataFrame([_rec(source_name='launch_library_2', source_event_id='L', source_name_value='SLS Block 1 | Artemis I',
                                vehicle_mission='SLS Block 1 | Artemis I', time_utc='2022-08-29T12:33:00Z')])
    scrub = pd.DataFrame([_rec(source_name='launch_library_2', source_event_id='L:update:1', event_type='scrub',
                               source_name_value='SLS Block 1 | Artemis I scrub', vehicle_mission='SLS Block 1 | Artemis I',
                               time_utc='2022-08-29T12:36:27Z')])
    curated = pd.DataFrame([_rec(source_name='nasa_blog', source_event_id='m1', event_type='pad_abort',
                                 source_name_value='SLS Artemis I scrub', vehicle_mission='SLS Block 1 | Artemis I',
                                 time_utc='2022-08-29T12:35:00Z')])
    ev, _ = reconcile_sources([launch, scrub, curated])
    assert sorted(ev.event_type) == ['orbital_launch', 'pad_abort']   # ignition reported by one source wins
    assert int(ev.loc[ev.event_type == 'pad_abort', 'source_count'].iloc[0]) == 2


def test_rollout_and_rollback_same_day_from_one_source_stay_apart():
    a = pd.DataFrame([_rec(source_name='nasa_blog', source_event_id='a', event_type='rollout', source_name_value='SLS rollout',
                           vehicle_mission='SLS rollout', time_utc='2022-09-26T03:00:00Z'),
                      _rec(source_name='nasa_blog', source_event_id='b', event_type='rollback', source_name_value='SLS rollback',
                           vehicle_mission='SLS rollback', time_utc='2022-09-26T10:00:00Z')])
    ev, _ = reconcile_sources([a])
    assert len(ev) == 2


def test_ll2_event_types_and_location_filter():
    from kscrockets.event_catalog import parse_ll2_event
    rb = parse_ll2_event({"id": 1, "name": "Artemis I SLS Rollback #2", "type": {"id": 27}, "date": "2022-07-02T08:12:00Z",
                          "location": "Kennedy Space Center", "duration": "PT10H"})
    assert rb["event_type"] == "rollback" and rb["route"] == "LC39B->VAB" and rb["pad"] == "LC39B"
    assert rb["event_end_utc"] == "2022-07-02T18:12:00Z"
    assert parse_ll2_event({"id": 2, "name": "Mengzhou abort", "type": {"id": 10}, "date": "2026-02-11T03:00:00Z",
                            "location": "LC-301, Wenchang Space Launch Site, China"}) is None
    assert parse_ll2_event({"id": 3, "name": "Starship static fire", "type": {"id": 5}, "date": "2024-01-01T00:00:00Z",
                            "location": "Starbase, Texas"}) is None
    gulf = parse_ll2_event({"id": 4, "name": "Crew-1 Splashdown", "type": {"id": 9}, "date": "2021-05-02T06:57:00Z",
                            "location": "Gulf of Mexico, southwest of Pensacola, FL, USA"})
    assert gulf["event_type"] == "reentry_sonic_boom"
    assert parse_ll2_event({"id": 5, "name": "Crew-11 Splashdown", "type": {"id": 9}, "date": "2026-01-15T08:41:00Z",
                            "location": "Pacific Ocean"}) is None


def test_ll2_scrub_rows_from_updates():
    from kscrockets.event_catalog import ll2_scrub_rows
    launch = {"id": "L", "name": "Falcon 9 | Starlink", "net": "2026-08-12T14:00:00Z", "pad": {"name": "Space Launch Complex 40"},
              "updates": [
                  {"id": 1, "comment": "On hold, potentially scrub for the day.", "created_on": "2026-08-10T14:14:00Z"},
                  {"id": 2, "comment": "Scrubbed for the day.", "created_on": "2026-08-10T14:23:00Z"},
                  {"id": 3, "comment": "Launch abort before ignition, next attempt TBD", "created_on": "2026-08-11T12:10:00Z"},
                  {"id": 4, "comment": "Delayed 24 hours following scrub of USSF-52.", "created_on": "2026-08-09T01:00:00Z"},
                  {"id": 5, "comment": "Delayed due to ascent abort contingency weather.", "created_on": "2026-08-08T01:00:00Z"},
                  {"id": 6, "comment": "Hot fire abort at T-0 after ignition.", "created_on": "2026-08-12T13:00:00Z"},
                  {"id": 7, "comment": "Scrubbed for the day.", "created_on": "2026-08-12T14:20:00Z"},   # after NET: ignored
              ]}
    df = ll2_scrub_rows([launch])
    assert df.time_utc.tolist() == ["2026-08-10T14:23:00Z", "2026-08-11T12:10:00Z", "2026-08-12T13:00:00Z"]
    assert df.event_type.tolist() == ["scrub", "scrub", "pad_abort"]


def test_raw_page_key_ignores_offset_and_parameter_order():
    from kscrockets.event_catalog import _raw_page_path
    a = _raw_page_path(Path("r"), "launches", "https://x/2.3.0/launches/?format=json&limit=100&ordering=net")
    b = _raw_page_path(Path("r"), "launches", "https://x/2.3.0/launches/?limit=100&offset=100&ordering=net&format=json")
    assert a.name.split("_")[1] == b.name.split("_")[1]
    assert a.name.endswith("_00000.json.gz") and b.name.endswith("_00100.json.gz")


def test_time_precedence_known_then_second_consensus_then_detected():
    from kscrockets.event_times import resolve_event_times
    ev = pd.DataFrame([
        dict(event_id='launch', event_time_utc='2020-01-01T00:00:01Z', event_time_source='gcat', event_time_precision='second'),
        dict(event_id='static', event_time_utc='2020-01-02T00:00:00Z', event_time_source='launch_library_2', event_time_precision='day'),
        dict(event_id='known', event_time_utc='2020-01-03T00:00:00Z', event_time_source='gcat', event_time_precision='second'),
        dict(event_id='plain', event_time_utc='2020-01-04T00:00:00Z', event_time_source='gcat', event_time_precision='minute'),
    ])
    known = pd.DataFrame([dict(event_id='known', known_time_utc='2020-01-03T00:00:02.5Z', known_time_source='webcast')])
    det = pd.DataFrame([dict(event_id='launch', detected_time_utc='2020-01-01T00:00:03Z', detected_time_method='sta_lta'),
                        dict(event_id='static', detected_time_utc='2020-01-02T17:01:00Z', detected_time_method='sta_lta'),
                        dict(event_id='known', detected_time_utc='2020-01-03T00:00:09Z', detected_time_method='sta_lta')])
    out = resolve_event_times(ev, known, det).set_index('event_id')
    assert out.loc['launch', 'event_time_basis'] == 'consensus' and out.loc['launch', 'event_time_utc'] == '2020-01-01T00:00:01Z'
    assert out.loc['launch', 'detected_time_utc'] == '2020-01-01T00:00:03Z'
    assert out.loc['static', 'event_time_basis'] == 'detected' and out.loc['static', 'event_time_utc'] == '2020-01-02T17:01:00Z'
    assert out.loc['static', 'consensus_time_utc'] == '2020-01-02T00:00:00Z'
    assert out.loc['known', 'event_time_basis'] == 'known' and out.loc['known', 'event_time_source'] == 'known:webcast'
    assert out.loc['known', 'event_time_utc'] == '2020-01-03T00:00:02.500000Z'
    assert out.loc['plain', 'event_time_basis'] == 'consensus'


def test_time_tables_reject_duplicates_and_unknown_ids(tmp_path):
    import pytest
    from kscrockets.event_times import read_detected_times, resolve_event_times
    p = tmp_path / 'd.csv'
    p.write_text("event_id,detected_time_utc,detected_time_method\na,2020-01-01T00:00:00Z,m\na,2020-01-01T00:00:01Z,m\n")
    with pytest.raises(ValueError): read_detected_times(p)
    p.write_text("event_id,detected_time_utc,detected_time_method\nnope,2020-01-01T00:00:00Z,m\n")
    ev = pd.DataFrame([dict(event_id='a', event_time_utc='2020-01-01T00:00:00Z', event_time_source='s', event_time_precision='day')])
    with pytest.raises(ValueError): resolve_event_times(ev, None, read_detected_times(p), strict=True)


def test_load_times_into_database_and_back(tmp_path):
    import sqlite3
    from kscrockets.event_times import apply_times_to_db
    from kscrockets.event_catalog import ensure_source_tables
    from kscrockets.database import SCHEMA
    db = tmp_path / 'k.sqlite'
    with sqlite3.connect(db) as con:
        con.executescript(SCHEMA)
        con.execute("INSERT INTO events(event_id,event_type,event_time_utc,event_time_source,event_time_precision) "
                    "VALUES ('e','static_fire','2020-01-02T00:00:00Z','launch_library_2','day')")
    ensure_source_tables(db)
    det = pd.DataFrame([dict(event_id='e', detected_time_utc='2020-01-02T17:01:00Z', detected_time_method='sta_lta')])
    assert apply_times_to_db(db, None, det) == {'detected': 1}
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT event_time_utc, consensus_time_utc FROM events").fetchone() == ('2020-01-02T17:01:00Z', '2020-01-02T00:00:00Z')
    assert apply_times_to_db(db, None, None) == {'consensus': 1}   # removing the row restores the source time
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT event_time_utc FROM events").fetchone() == ('2020-01-02T00:00:00Z',)
