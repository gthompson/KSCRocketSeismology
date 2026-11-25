from pathlib import Path
import pandas as pd
from kscrockets.catalog import build_catalog, validate_catalog
from kscrockets.database import build_database, query_events


def test_catalog_builds(tmp_path):
    root=Path(__file__).parents[1]
    df=build_catalog(root/'data/raw/merged_launches.csv',year_min=2016,year_max=2022,
                     overrides_path=root/'data/curated/event_overrides.csv',
                     id_registry_path=root/'data/curated/event_id_registry.csv')
    assert len(df) > 150
    assert df.event_id.is_unique
    assert not validate_catalog(df)
    assert set(df.event_time_utc.dt.year.unique()).issubset(set(range(2016,2023)))
    amos=df[df.mission.str.contains('Amos 6',case=False,na=False)].iloc[0]
    assert amos.event_type == 'explosion'
    assert amos.event_time_utc == pd.Timestamp('2016-09-01T13:07:11.913Z')
    assert amos.event_time_utc != amos.window_start


def test_sqlite_roundtrip(tmp_path):
    root=Path(__file__).parents[1]
    csv=tmp_path/'catalog.csv'; db=tmp_path/'catalog.sqlite'
    build_catalog(root/'data/raw/merged_launches.csv',csv,2016,2022,
                  root/'data/curated/event_overrides.csv',root/'data/curated/event_id_registry.csv')
    build_database(csv,db)
    df=query_events(db,'2016-08-01','2016-09-15')
    assert df.event_type.eq('explosion').any()
    assert df.mission.str.contains('OSIRIS',na=False).any()


def test_normalize_pad_one_form():
    from kscrockets.catalog import normalize_pad
    for raw, want in [('40', 'LC40'), ('SLC-40', 'LC40'), ('Space Launch Complex 40', 'LC40'), ('39A', 'LC39A'),
                      ('LC39A', 'LC39A'), ('Launch Complex 39B', 'LC39B'), ('Space Launch Complex 46', 'LC46'),
                      ('Launch Complex 36A', 'LC36'), ('LC36', 'LC36'), ('LZ-1', 'LZ1'), ('SLF', 'SLF'), ('', 'Unknown')]:
        assert normalize_pad(raw) == want, raw


def test_classify_vehicle_new_vehicles():
    from kscrockets.catalog import classify_vehicle
    assert classify_vehicle('Vulcan VC4S | USSF-106') == 'Vulcan'
    assert classify_vehicle('New Glenn | EscaPADE') == 'New Glenn'
    assert classify_vehicle('SLS Block 1 | Artemis II') == 'SLS'
    assert classify_vehicle('Starship | Flight 12') == 'Starship'
    assert classify_vehicle('Delta IV Heavy | NROL-44') == 'Delta IV Heavy'
    assert classify_vehicle('Falcon 9 Block 5 | Starlink') == 'Falcon 9'
    assert classify_vehicle('F9 B1060 Static Fire') == 'Falcon 9'


def test_reconciled_database_2016_to_present():
    """The committed sqlite: 2016 to 2026, ids of the 2016-2022 catalog kept, key 2026 events present."""
    import sqlite3
    root=Path(__file__).parents[1]
    with sqlite3.connect(root/'data/processed/ksc_rockets.sqlite') as con:
        ev=pd.read_sql('SELECT * FROM events',con)
    assert ev.event_id.is_unique
    assert ev.event_time_utc.min().startswith('2016') and ev.event_time_utc.max() >= '2026-11'
    # ids from the 2016-2022 reconciled catalog are unchanged
    assert ev.set_index('event_id').loc['ksc-14e6273111f1','event_time_utc'] == '2016-02-05T13:38:00Z'
    art=ev[ev.name.str.contains('Artemis II',na=False) & ~ev.name.str.contains('Artemis III',na=False)]
    assert len(art)==1 and art.iloc[0].event_time_utc=='2026-04-01T22:35:12Z' and art.iloc[0].pad=='LC39B'
    ng=ev[ev.event_id=='ksc-newglenn-explosion-20260529'].iloc[0]
    assert ng.event_type=='pad_explosion' and ng.pad=='LC36' and ng.event_time_utc.startswith('2026-05-29T01:00:0')
    assert (ev.vehicle.fillna('')!='').all()
    assert ev.pad.isin(['LC40','LC39A','LC39B','LC41','LC37B','LC46','LC36','LC16','LZ1','LZ2','LZ40',
                        'SLF','L1011','Unknown']).all()


def test_launchpads_cover_catalog_pads_and_kml():
    import sqlite3, xml.etree.ElementTree as ET
    import pandas as pd
    from kscrockets.kml import launchpads_kml
    root = Path(__file__).resolve().parents[1]
    pads = pd.read_csv(root/"data/raw/launchpads.csv")
    assert pads.pad.is_unique
    used = {r[0] for r in sqlite3.connect(root/"data/processed/ksc_rockets.sqlite").execute("select distinct pad from events")}
    assert used - set(pads.pad) <= {"SLF", "L1011", "Unknown"}   # runway/air launch/unknown have no pad point
    doc = ET.fromstring(launchpads_kml(pads))
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    marks = doc.findall(".//k:Placemark", ns)
    assert [m.find("k:name", ns).text for m in marks] == list(pads.pad)
    lon, lat, _ = marks[0].find(".//k:coordinates", ns).text.split(",")
    assert abs(float(lat) - pads.lat[0]) < 1e-6 and abs(float(lon) - pads.lon[0]) < 1e-6
