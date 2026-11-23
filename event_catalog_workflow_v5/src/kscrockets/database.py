from __future__ import annotations
from pathlib import Path
import sqlite3
import pandas as pd
from .catalog import read_catalog

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    launch_designator TEXT,
    event_time_utc TEXT NOT NULL,
    event_time_source TEXT,
    event_time_quality TEXT,
    event_time_precision TEXT,
    time_definition TEXT,
    window_start TEXT,
    window_end TEXT,
    name TEXT,
    mission TEXT,
    vehicle TEXT,
    pad TEXT,
    provider TEXT,
    launch_success TEXT,
    landing_attempt TEXT,
    landing_success TEXT,
    landing_pad TEXT,
    landing_type TEXT,
    source TEXT,
    notes TEXT,
    time_spread_s REAL,
    time_conflict INTEGER DEFAULT 0,
    source_count INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_vehicle ON events(vehicle);
CREATE INDEX IF NOT EXISTS idx_events_pad ON events(pad);

CREATE TABLE IF NOT EXISTS channel_epochs (
    channel_epoch_id INTEGER PRIMARY KEY,
    network TEXT NOT NULL, station TEXT NOT NULL, location TEXT NOT NULL, channel TEXT NOT NULL,
    starttime TEXT, endtime TEXT, sensor_model TEXT, sensor_serial TEXT,
    datalogger TEXT, response_status TEXT, notes TEXT,
    UNIQUE(network, station, location, channel, starttime)
);
CREATE TABLE IF NOT EXISTS measurements (
    measurement_id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    channel_epoch_id INTEGER REFERENCES channel_epochs(channel_epoch_id),
    metric_name TEXT NOT NULL, value REAL, units TEXT,
    processing_version TEXT, qc_flag TEXT, notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_measurements_event ON measurements(event_id);
CREATE TABLE IF NOT EXISTS qc_intervals (
    qc_id INTEGER PRIMARY KEY,
    channel_epoch_id INTEGER REFERENCES channel_epochs(channel_epoch_id),
    starttime TEXT, endtime TEXT, issue_type TEXT, severity TEXT, notes TEXT, source TEXT
);
"""


def build_database(catalog_csv: str | Path, db_path: str | Path) -> Path:
    db_path=Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    df=read_catalog(catalog_csv).copy()
    if "time_utc" in df: df=df.drop(columns=["time_utc"])
    for c in ("event_time_utc","window_start","window_end"):
        if c in df:
            df[c]=df[c].map(lambda x: x.isoformat().replace('+00:00','Z') if pd.notna(x) else None)
    with sqlite3.connect(db_path) as con:
        con.executescript(SCHEMA)
        con.execute("DELETE FROM events")
        cols=[r[1] for r in con.execute("PRAGMA table_info(events)")]
        df=df[[c for c in cols if c in df.columns]]
        df.to_sql("events", con, if_exists="append", index=False)
    from .event_catalog import ensure_source_tables
    ensure_source_tables(db_path)
    return db_path


def query_events(db_path: str | Path, start=None, end=None, event_types=None) -> pd.DataFrame:
    sql="SELECT * FROM events WHERE 1=1"; params=[]
    if start is not None: sql += " AND event_time_utc >= ?"; params.append(pd.Timestamp(start, tz='UTC').isoformat().replace('+00:00','Z'))
    if end is not None: sql += " AND event_time_utc <= ?"; params.append(pd.Timestamp(end, tz='UTC').isoformat().replace('+00:00','Z'))
    if event_types:
        sql += " AND event_type IN (%s)" % ",".join("?"*len(event_types)); params.extend(event_types)
    sql += " ORDER BY event_time_utc"
    with sqlite3.connect(db_path) as con: return pd.read_sql_query(sql, con, params=params)
