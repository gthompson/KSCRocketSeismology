from pathlib import Path
from kscrockets.catalog import build_catalog, validate_catalog

def test_catalog_builds():
    root=Path(__file__).parents[1]
    df=build_catalog(root/'data/raw/merged_launches.csv',year_min=2016,year_max=2022)
    assert len(df) > 150
    assert df.event_id.is_unique
    assert not validate_catalog(df)
    assert set(df.time_utc.dt.year.unique()).issubset(set(range(2016,2023)))
