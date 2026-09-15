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
