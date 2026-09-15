from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timezone
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import urllib.parse
import urllib.request

import pandas as pd

EVENT_TYPES = (
    "orbital_launch", "launch_failure", "pad_explosion", "static_fire",
    "aborted_launch", "booster_landing", "aircraft_sonic_boom",
)

SOURCE_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS event_time_sources (
    source_time_id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_event_id TEXT,
    time_utc TEXT NOT NULL,
    precision TEXT,
    time_definition TEXT,
    quality TEXT,
    source_url TEXT,
    retrieved_at TEXT,
    notes TEXT,
    UNIQUE(event_id, source_name, source_event_id, time_utc)
);
CREATE INDEX IF NOT EXISTS idx_event_time_sources_event ON event_time_sources(event_id);
CREATE INDEX IF NOT EXISTS idx_event_time_sources_time ON event_time_sources(time_utc);

CREATE TABLE IF NOT EXISTS event_aliases (
    alias_id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_event_id TEXT,
    source_name_value TEXT,
    UNIQUE(event_id, source_name, source_event_id)
);

CREATE TABLE IF NOT EXISTS event_observations (
    observation_id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    observation_type TEXT NOT NULL,
    station TEXT,
    channel TEXT,
    time_utc TEXT,
    value_text TEXT,
    source TEXT,
    notes TEXT
);
"""


def iso_utc(value) -> str | None:
    if value is None or value == "" or pd.isna(value):
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat().replace("+00:00", "Z")


def stable_event_id(event_type: str, time_utc: str, name: str = "", pad: str = "") -> str:
    # Time is used only when initially assigning a new manual event. Once written to
    # curated/manual_events.csv, event_id is persistent and should never be regenerated.
    key = f"{event_type}|{time_utc}|{name}|{pad}"
    return "ksc-" + hashlib.sha1(key.encode()).hexdigest()[:12]


def normalize_event_type(value: str, status: str = "") -> str:
    s = f"{value or ''} {status or ''}".lower()
    if "sonic" in s and ("air" in s or "sonicbat" in s or "f-" in s): return "aircraft_sonic_boom"
    if "landing" in s or "return" in s: return "booster_landing"
    if "static" in s or "hot fire" in s: return "static_fire"
    if "abort" in s or "scrub" in s: return "aborted_launch"
    if "explosion" in s or "pad explosion" in s: return "pad_explosion"
    if "fail" in s: return "launch_failure"
    return "orbital_launch"


def ensure_source_tables(db_path: str | Path) -> None:
    with sqlite3.connect(db_path) as con:
        con.executescript(SOURCE_SCHEMA)


def _combine_excel_datetime(d, t):
    if pd.isna(d): return None
    if isinstance(d, pd.Timestamp): d = d.to_pydatetime()
    if isinstance(d, datetime): day = d.date()
    elif isinstance(d, date): day = d
    else: day = pd.Timestamp(d).date()
    if pd.isna(t) or t is None: clock = time(0, 0)
    elif isinstance(t, time): clock = t
    else: clock = pd.to_datetime(str(t)).time()
    return datetime.combine(day, clock, tzinfo=timezone.utc)


def read_manual_excel(path: str | Path) -> pd.DataFrame:
    """Read Glenn's hand-curated launches + non_launches sheets as candidate events."""
    path = Path(path)
    frames = []
    for sheet in ("launches", "non_launches"):
        df = pd.read_excel(path, sheet_name=sheet)
        df = df[df["Date"].notna()].copy()
        rows = []
        for _, r in df.iterrows():
            dt = _combine_excel_datetime(r.get("Date"), r.get("Time"))
            raw_type = str(r.get("Event type", "") or "")
            etype = normalize_event_type(raw_type)
            # The launches sheet labels ordinary launches simply 'launch'.
            if sheet == "launches" and etype == "orbital_launch": etype = "orbital_launch"
            rows.append({
                "source_name": "manual_excel",
                "source_event_id": "",
                "source_name_value": str(r.get("Rocket_Payload", "") or ""),
                "event_type": etype,
                "time_utc": iso_utc(dt),
                "precision": "second" if getattr(r.get("Time"), "second", 0) else "minute",
                "time_definition": "manual_compilation_liftoff_or_event_time",
                "quality": "curated_manual",
                "pad": str(r.get("SLC", "") or ""),
                "vehicle_mission": str(r.get("Rocket_Payload", "") or ""),
                "stations_recorded": str(r.get("Stations Recorded", "") or ""),
                "notes": str(r.get("Notes", "") or ""),
                "source_url": "",
                "source_file": path.name,
            })
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


def read_manual_events_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists(): return pd.DataFrame()
    df = pd.read_csv(path, dtype=str).fillna("")
    if df.empty: return df
    bad = sorted(set(df.event_type) - set(EVENT_TYPES))
    if bad: raise ValueError(f"Unsupported manual event_type values: {bad}")
    return df


def add_manual_event(path: str | Path, event_type: str, time_utc: str, name: str,
                     pad: str = "", source: str = "waveform_review", notes: str = "",
                     precision: str = "second", event_id: str | None = None) -> str:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"event_type must be one of {EVENT_TYPES}")
    t = iso_utc(time_utc)
    event_id = event_id or stable_event_id(event_type, t, name, pad)
    row = pd.DataFrame([{
        "event_id": event_id, "event_type": event_type, "event_time_utc": t,
        "event_time_source": source, "event_time_quality": "manual_verified",
        "event_time_precision": precision, "time_definition": "observed_event_time",
        "name": name, "mission": name, "vehicle": "", "pad": pad, "provider": "",
        "source": source, "notes": notes,
    }])
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = pd.read_csv(path, dtype=str).fillna("")
        if event_id in set(old.get("event_id", [])):
            raise ValueError(f"event_id already exists in {path}: {event_id}")
        row = pd.concat([old, row], ignore_index=True)
    row.to_csv(path, index=False)
    return event_id


def fetch_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "KSCRocketSeismology/0.2 research catalog"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_ll2(start: str, end: str, location_ids: list[int] | None = None,
              base_url: str = "https://ll.thespacedevs.com/2.3.0/launches/") -> pd.DataFrame:
    """Fetch LL2 launch candidates. Caller can supply LL2 location IDs once verified."""
    params = {"format":"json", "mode":"normal", "limit":100,
              "net__gte":iso_utc(start), "net__lte":iso_utc(end), "ordering":"net"}
    if location_ids: params["pad__location"] = ",".join(map(str, location_ids))
    url = base_url + "?" + urllib.parse.urlencode(params)
    rows=[]
    while url:
        payload=fetch_json(url)
        for x in payload.get("results", []):
            status=(x.get("status") or {}).get("name", "")
            mission=(x.get("mission") or {}).get("name", "")
            rocket=((x.get("rocket") or {}).get("configuration") or {}).get("full_name", "")
            pad=x.get("pad") or {}
            loc=pad.get("location") or {}
            precision=(x.get("net_precision") or {}).get("name", "")
            rows.append({
                "source_name":"launch_library_2", "source_event_id":x.get("id", ""),
                "source_name_value":x.get("name", ""), "event_type":normalize_event_type(x.get("name", ""), status),
                "time_utc":x.get("net"), "precision":precision.lower(),
                "time_definition":"LL2 NET/T-0", "quality":status,
                "pad":pad.get("name", ""), "location":loc.get("name", ""),
                "vehicle_mission":" | ".join(v for v in (rocket, mission) if v),
                "status":status, "source_url":x.get("url", ""), "notes":"",
            })
        url=payload.get("next")
    return pd.DataFrame(rows)


def _tokens(s: str) -> set[str]:
    stop={"the","mission","launch","full","thrust","block","flight","of","and"}
    return {x for x in re.findall(r"[a-z0-9]+", str(s).lower()) if len(x)>1 and x not in stop}


def match_score(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    ta=pd.Timestamp(a.time_utc); tb=pd.Timestamp(b.time_utc)
    dt=abs((ta-tb).total_seconds())
    tok_a=_tokens(a.get("vehicle_mission", a.get("source_name_value", "")))
    tok_b=_tokens(b.get("vehicle_mission", b.get("source_name_value", "")))
    union=tok_a|tok_b; similarity=len(tok_a&tok_b)/len(union) if union else 0.0
    # time dominates only within a broad 12-hour candidate gate; name protects against bad window times.
    score=similarity + max(0.0, 1.0-dt/(12*3600))*0.5
    return score, dt


def reconcile_sources(sources: list[pd.DataFrame], max_hours: float = 12.0,
                      min_score: float = 0.45) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Conservative pairwise clustering. Ambiguous candidates remain separate for manual review."""
    records=[]
    for df in sources:
        if df is not None and not df.empty:
            records.extend(df.to_dict("records"))
    records=sorted(records, key=lambda r: pd.Timestamp(r["time_utc"]))
    clusters=[]
    for rec in records:
        r=pd.Series(rec); best=None
        for i,c in enumerate(clusters):
            rep=pd.Series(c[0]); score,dt=match_score(r,rep)
            if dt <= max_hours*3600 and score >= min_score and (best is None or score>best[0]):
                best=(score,i)
        if best is None: clusters.append([rec])
        else: clusters[best[1]].append(rec)

    events=[]; source_rows=[]
    for cluster in clusters:
        # Prefer manual curated time; then second-precision LL2; otherwise first source.
        def rank(r):
            return (0 if r.get("source_name")=="manual_excel" else 1,
                    0 if str(r.get("precision","")).lower()=="second" else 1)
        preferred=sorted(cluster,key=rank)[0]
        eid=next((r.get("persistent_event_id") for r in cluster if r.get("persistent_event_id")), None) or stable_event_id(preferred["event_type"], preferred["time_utc"], preferred.get("source_name_value",""), preferred.get("pad",""))
        times=[pd.Timestamp(r["time_utc"]) for r in cluster]
        spread=(max(times)-min(times)).total_seconds() if len(times)>1 else 0.0
        events.append({
            "event_id":eid, "event_type":preferred["event_type"], "event_time_utc":iso_utc(preferred["time_utc"]),
            "event_time_source":preferred.get("source_name",""), "event_time_quality":preferred.get("quality",""),
            "event_time_precision":preferred.get("precision",""), "time_definition":preferred.get("time_definition",""),
            "name":preferred.get("source_name_value",""), "mission":preferred.get("vehicle_mission",""),
            "vehicle":"", "pad":preferred.get("pad",""), "provider":"", "source":"reconciled_sources",
            "notes":preferred.get("notes",""), "time_spread_s":spread,
            "time_conflict":bool(spread>60), "source_count":len(cluster),
        })
        for r in cluster:
            source_rows.append({"event_id":eid, **r})
    return pd.DataFrame(events).sort_values("event_time_utc"), pd.DataFrame(source_rows)


def manual_events_as_source(path: str | Path) -> pd.DataFrame:
    df=read_manual_events_csv(path)
    if df.empty: return pd.DataFrame()
    return pd.DataFrame({
        "source_name": df.get("event_time_source", "manual_events"),
        "source_event_id": df.get("event_id", ""),
        "source_name_value": df.get("name", df.get("mission", "")),
        "event_type": df["event_type"],
        "time_utc": df["event_time_utc"],
        "precision": df.get("event_time_precision", "second"),
        "time_definition": df.get("time_definition", "observed_event_time"),
        "quality": df.get("event_time_quality", "manual_verified"),
        "pad": df.get("pad", ""),
        "vehicle_mission": df.get("mission", df.get("name", "")),
        "notes": df.get("notes", ""),
        "source_url": "",
        "persistent_event_id": df.get("event_id", ""),
    })


def write_reconciliation(db_path: str | Path, events: pd.DataFrame, source_rows: pd.DataFrame,
                         replace_events: bool = False) -> None:
    ensure_source_tables(db_path)
    now=iso_utc(pd.Timestamp.now(tz="UTC"))
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        if replace_events:
            con.execute("DELETE FROM event_time_sources"); con.execute("DELETE FROM event_aliases"); con.execute("DELETE FROM events")
        event_cols={r[1] for r in con.execute("PRAGMA table_info(events)")}
        for _,e in events.iterrows():
            row={k:(None if pd.isna(v) else v) for k,v in e.items() if k in event_cols}
            cols=list(row); q=",".join("?" for _ in cols)
            con.execute(f"INSERT OR REPLACE INTO events ({','.join(cols)}) VALUES ({q})", [row[c] for c in cols])
        for _,r in source_rows.iterrows():
            con.execute("""INSERT OR IGNORE INTO event_time_sources
                (event_id,source_name,source_event_id,time_utc,precision,time_definition,quality,source_url,retrieved_at,notes)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (r.event_id,r.get("source_name",""),r.get("source_event_id",""),iso_utc(r.time_utc),r.get("precision",""),
                 r.get("time_definition",""),r.get("quality",""),r.get("source_url",""),now,r.get("notes","")))
            con.execute("""INSERT OR IGNORE INTO event_aliases(event_id,source_name,source_event_id,source_name_value)
                VALUES (?,?,?,?)""",(r.event_id,r.get("source_name",""),r.get("source_event_id",""),r.get("source_name_value","")))
