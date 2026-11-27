"""kscrockets.products: CSV upsert and sqlite load, with fake per-event results."""
import sqlite3
from dataclasses import dataclass, field
import pandas as pd
from kscrockets.products import save_results, load_products


@dataclass
class R:
    event_id: str
    status: str = "ok"; error: str = ""; data_source: str = "local_sds:/x"
    n_raw: int = 1; n_corrected: int = 1
    metrics: pd.DataFrame = field(default_factory=pd.DataFrame)
    onsets: pd.DataFrame = field(default_factory=pd.DataFrame)
    detected: dict = field(default_factory=dict)
    products: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _res(eid, peak, detected=True):
    m = pd.DataFrame([dict(event_id=eid, seed_id="1R.A.00.HDF", metric="peak", value=peak)])
    d = dict(detected_time_utc="2026-01-01T00:00:01Z", method="m", offset_s=1.0, mad_s=0.1,
             n_stations=2, n_channels=3) if detected else {}
    return R(eid, metrics=m, detected=d, products=[dict(product_type="manifest", path="/x/manifest.json")])


def test_rerun_replaces_rows_and_loads_sqlite(tmp_path):
    (tmp_path / "data/curated").mkdir(parents=True)
    t = tmp_path / "out/tables"
    save_results(tmp_path, t, dict(run_id="r1"), [_res("e1", 1.0), _res("e2", 2.0)])
    save_results(tmp_path, t, dict(run_id="r2"), [_res("e1", 5.0, detected=False), R("e3", status="no_data")])
    m = pd.read_csv(t / "measurements.csv")
    assert sorted(zip(m.event_id, m.value)) == [("e1", 5.0), ("e2", 2.0)]
    det = pd.read_csv(tmp_path / "data/curated/detected_times.csv")
    assert list(det.event_id) == ["e2"]                       # e1 lost its old detection
    st = pd.read_csv(t / "event_processing.csv")
    assert set(zip(st.event_id, st.run_id)) == {("e1", "r2"), ("e2", "r1"), ("e3", "r2")}
    db = tmp_path / "x.sqlite"
    assert not (tmp_path / "data/products").exists()          # nothing written into the repo
    assert "measurements" in load_products(tmp_path, t, db)
    with sqlite3.connect(db) as con:
        assert con.execute("select value from measurements where event_id='e1'").fetchone()[0] == 5.0
