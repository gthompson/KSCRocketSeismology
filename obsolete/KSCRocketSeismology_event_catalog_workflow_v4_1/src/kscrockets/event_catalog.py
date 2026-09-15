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
import urllib.error
import time as time_module

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
    time_role TEXT DEFAULT 'actual_event_time',
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
        cols = {r[1] for r in con.execute("PRAGMA table_info(event_time_sources)")}
        if "time_role" not in cols:
            con.execute("ALTER TABLE event_time_sources ADD COLUMN time_role TEXT DEFAULT 'actual_event_time'")


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
                "time_role": "actual_event_time",
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
    req = urllib.request.Request(url, headers={"User-Agent": "KSCRocketSeismology/0.3 research catalog"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_ll2(start: str, end: str, location_ids: list[int] | None = None,
              base_url: str = "https://ll.thespacedevs.com/2.3.0/launches/",
              max_retries: int = 2, progress: bool = True) -> pd.DataFrame:
    """Fetch LL2 launch candidates with visible page/retry progress.

    LL2 is paginated and unauthenticated requests can be rate limited.  Progress
    messages are flushed immediately so a long request never looks hung.
    """
    params = {"format":"json", "mode":"normal", "limit":100,
              "net__gte":iso_utc(start), "net__lte":iso_utc(end), "ordering":"net"}
    if location_ids: params["pad__location"] = ",".join(map(str, location_ids))
    url = base_url + "?" + urllib.parse.urlencode(params)
    rows=[]; page=0
    if progress:
        print(f"LL2: requesting {start} through {end}", flush=True)
        if location_ids:
            print(f"LL2: restricting request to location id(s): {location_ids}", flush=True)
        else:
            print("LL2: no server-side location filter; KSC/Cape filtering will occur after download", flush=True)
    while url:
        page += 1
        payload=None
        if progress:
            print(f"LL2: page {page}: requesting up to 100 records (collected {len(rows)} so far)...", flush=True)
        for attempt in range(max_retries + 1):
            try:
                payload=fetch_json(url)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt >= max_retries:
                    if progress:
                        print(f"LL2: page {page}: HTTP {exc.code}; giving up on refresh", flush=True)
                    raise
                retry_after=exc.headers.get("Retry-After") if exc.headers else None
                wait=int(retry_after) if retry_after and str(retry_after).isdigit() else min(60, 5 * (2 ** attempt))
                if progress:
                    print(f"LL2: page {page}: HTTP 429 rate limit; waiting {wait} s before retry {attempt+2}/{max_retries+1}", flush=True)
                time_module.sleep(wait)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if progress:
                    print(f"LL2: page {page}: network error: {exc}", flush=True)
                raise
        results=payload.get("results", [])
        total=payload.get("count")
        if progress:
            suffix=f" of {total} total LL2 candidates" if total is not None else ""
            print(f"LL2: page {page}: received {len(results)} records{suffix}", flush=True)
        for x in results:
            status=(x.get("status") or {}).get("name", "")
            mission=(x.get("mission") or {}).get("name", "")
            rocket=((x.get("rocket") or {}).get("configuration") or {}).get("full_name", "")
            pad=x.get("pad") or {}; loc=pad.get("location") or {}
            precision=(x.get("net_precision") or {}).get("name", "")
            rows.append({
                "source_name":"launch_library_2", "source_event_id":x.get("id", ""),
                "source_name_value":x.get("name", ""), "event_type":normalize_event_type(x.get("name", ""), status),
                "time_utc":x.get("net"), "precision":precision.lower(),
                "time_definition":"LL2 NET/T-0", "quality":status,
                "pad":pad.get("name", ""), "location":loc.get("name", ""),
                "vehicle_mission":" | ".join(v for v in (rocket, mission) if v),
                "status":status, "source_url":x.get("url", ""), "notes":"",
                "time_role": ("scheduled_launch_time" if
                    ("failure before launch" in str(x.get("name", "")).lower())
                    else "actual_event_time"),
            })
        if progress:
            print(f"LL2: page {page}: accumulated {len(rows)} records; next page: {'yes' if payload.get('next') else 'no'}", flush=True)
        url=payload.get("next")
    if progress:
        print(f"LL2: download complete: {len(rows)} candidate records across {page} page(s)", flush=True)
    return pd.DataFrame(rows)


def filter_ll2_ksc(df: pd.DataFrame) -> pd.DataFrame:
    """Keep Cape Canaveral/KSC records from a broader LL2 response."""
    if df is None or df.empty:
        return pd.DataFrame()
    location=df["location"].astype(str) if "location" in df else pd.Series("", index=df.index)
    pad=df["pad"].astype(str) if "pad" in df else pd.Series("", index=df.index)
    mask=(location.str.contains("Kennedy|Cape Canaveral",case=False,regex=True,na=False) |
          pad.str.contains("39A|39B|SLC-40|SLC-41|SLC-37|SLC-46",case=False,regex=True,na=False))
    return df[mask].copy()


def write_source_cache(df: pd.DataFrame, path: str | Path, source_name: str) -> Path:
    """Persist an external-source snapshot so catalog rebuilds are reproducible/offline."""
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    out=df.copy()
    out["retrieved_at"] = iso_utc(pd.Timestamp.now(tz="UTC"))
    out["cache_source"] = source_name
    out.to_csv(path, index=False)
    return path


def read_source_cache(path: str | Path) -> pd.DataFrame:
    path=Path(path)
    if not path.exists(): return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def refresh_ll2_cache(start: str, end: str, cache_path: str | Path,
                      location_ids: list[int] | None = None) -> tuple[pd.DataFrame, str]:
    """Refresh LL2 cache. On 429/network failure, retain and return an existing cache."""
    cache_path=Path(cache_path)
    print(f"LL2 cache target: {cache_path}", flush=True)
    if cache_path.exists():
        old=read_source_cache(cache_path)
        print(f"LL2: existing cache found with {len(old)} record(s); it will be preserved unless refresh completes", flush=True)
    else:
        print("LL2: no existing cache found", flush=True)
    try:
        raw=fetch_ll2(start, end, location_ids=location_ids, progress=True)
        print(f"LL2: filtering {len(raw)} downloaded candidates to Kennedy/Cape Canaveral...", flush=True)
        df=filter_ll2_ksc(raw)
        print(f"LL2: retained {len(df)} KSC/Cape record(s)", flush=True)
        write_source_cache(df, cache_path, "launch_library_2")
        print(f"LL2: cache written successfully: {cache_path}", flush=True)
        return df, "refreshed"
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        cached=read_source_cache(cache_path)
        if not cached.empty:
            code=getattr(exc, "code", None)
            reason=f"HTTP {code}" if code else exc.__class__.__name__
            print(f"LL2: refresh failed ({reason}); retaining existing cache with {len(cached)} record(s)", flush=True)
            return cached, f"cache retained ({reason})"
        raise RuntimeError(
            f"LL2 refresh failed and no cache exists at {cache_path}. "
            "Wait for the service/rate limit to recover, then run `ksc-rockets fetch-ll2`."
        ) from exc

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
                      min_score: float = 0.45, scheduled_match_hours: float = 72.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Conservative pairwise clustering. Ambiguous candidates remain separate for manual review."""
    records=[]
    for df in sources:
        if df is not None and not df.empty:
            for rec in df.to_dict("records"):
                rec.setdefault("time_role", "actual_event_time")
                records.append(rec)

    # Only physical/observed times create research events. Scheduled launch times
    # are provenance metadata and are attached in a second pass. This prevents
    # AMOS-6's planned 2016-09-03 launch from becoming a false waveform event.
    actual=[r for r in records if r.get("time_role", "actual_event_time") == "actual_event_time"]
    scheduled=[r for r in records if r.get("time_role") != "actual_event_time"]
    actual=sorted(actual, key=lambda r: pd.Timestamp(r["time_utc"]))
    clusters=[]
    for rec in actual:
        r=pd.Series(rec); best=None
        for i,c in enumerate(clusters):
            rep=pd.Series(c[0]); score,dt=match_score(r,rep)
            if dt <= max_hours*3600 and score >= min_score and (best is None or score>best[0]):
                best=(score,i)
        if best is None: clusters.append([rec])
        else: clusters[best[1]].append(rec)

    # Attach scheduled-time records to an existing physical event when mission/name
    # evidence is strong, allowing a wider time separation. Do not create an event
    # from a schedule alone. Unmatched schedule records are returned with blank event_id
    # so they remain inspectable in event_time_sources.csv.
    unmatched_scheduled=[]
    for rec in scheduled:
        r=pd.Series(rec); best=None
        for i,c in enumerate(clusters):
            rep=pd.Series(c[0]); score,dt=match_score(r,rep)
            # Require substantial name overlap; time contributes only weakly here.
            ta=_tokens(r.get("vehicle_mission", r.get("source_name_value", "")))
            tb=_tokens(rep.get("vehicle_mission", rep.get("source_name_value", "")))
            union=ta|tb; sim=len(ta&tb)/len(union) if union else 0.0
            if dt <= scheduled_match_hours*3600 and sim >= 0.40 and (best is None or sim>best[0]):
                best=(sim,i)
        if best is None: unmatched_scheduled.append(rec)
        else: clusters[best[1]].append(rec)

    events=[]; source_rows=[]
    for cluster in clusters:
        actual_cluster=[r for r in cluster if r.get("time_role", "actual_event_time") == "actual_event_time"]
        def rank(r):
            return (0 if r.get("source_name")=="manual_excel" else 1,
                    0 if str(r.get("precision","")).lower()=="second" else 1)
        preferred=sorted(actual_cluster,key=rank)[0]
        eid=next((r.get("persistent_event_id") for r in actual_cluster if r.get("persistent_event_id")), None) or stable_event_id(preferred["event_type"], preferred["time_utc"], preferred.get("source_name_value",""), preferred.get("pad",""))
        times=[pd.Timestamp(r["time_utc"]) for r in actual_cluster]
        spread=(max(times)-min(times)).total_seconds() if len(times)>1 else 0.0
        events.append({
            "event_id":eid, "event_type":preferred["event_type"], "event_time_utc":iso_utc(preferred["time_utc"]),
            "event_time_source":preferred.get("source_name",""), "event_time_quality":preferred.get("quality",""),
            "event_time_precision":preferred.get("precision",""), "time_definition":preferred.get("time_definition",""),
            "name":preferred.get("source_name_value",""), "mission":preferred.get("vehicle_mission",""),
            "vehicle":"", "pad":preferred.get("pad",""), "provider":"", "source":"reconciled_sources",
            "notes":preferred.get("notes",""), "time_spread_s":spread,
            "time_conflict":bool(spread>60), "source_count":len(actual_cluster),
            "scheduled_time_count":len(cluster)-len(actual_cluster),
        })
        for r in cluster:
            source_rows.append({"event_id":eid, **r})
    for r in unmatched_scheduled:
        source_rows.append({"event_id":"", **r})
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
        "time_role": "actual_event_time",
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
            if not str(r.get("event_id", "")).strip():
                continue
            con.execute("""INSERT OR IGNORE INTO event_time_sources
                (event_id,source_name,source_event_id,time_utc,precision,time_definition,quality,source_url,retrieved_at,notes,time_role)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (r.event_id,r.get("source_name",""),r.get("source_event_id",""),iso_utc(r.time_utc),r.get("precision",""),
                 r.get("time_definition",""),r.get("quality",""),r.get("source_url",""),now,r.get("notes",""),r.get("time_role","actual_event_time")))
            con.execute("""INSERT OR IGNORE INTO event_aliases(event_id,source_name,source_event_id,source_name_value)
                VALUES (?,?,?,?)""",(r.event_id,r.get("source_name",""),r.get("source_event_id",""),r.get("source_name_value","")))

GCAT_LAUNCH_URL = "https://planet4589.org/space/gcat/tsv/launch/launch.tsv"


def _gcat_precision(value: str) -> str:
    s = str(value or "").strip()
    # GCAT VagueDate examples include HHMM:SS as well as HH:MM:SS.
    if re.search(r"(?:\d{2}:\d{2}:\d{2}|\d{4}:\d{2})", s): return "second"
    if re.search(r"(?:\d{2}:\d{2}|\b\d{4}\b)", s): return "minute"
    return "day"


def _parse_gcat_date(value: str) -> str | None:
    """Parse a GCAT VagueDate conservatively."""
    s = str(value or "").strip()
    if not s or s.lower() == "nan": return None
    clean = re.sub(r"[?~]", "", s).strip()
    # GCAT commonly uses 'YYYY Mon DD HHMM:SS'. Normalize that first.
    m = re.match(r"^(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})(?:\s+(\d{2})(\d{2})(?::(\d{2}))?)?$", clean)
    if m:
        hh=m.group(4) or "00"; mm=m.group(5) or "00"; ss=m.group(6) or "00"
        try: return iso_utc(pd.to_datetime(f"{m.group(1)} {m.group(2)} {m.group(3)} {hh}:{mm}:{ss}", utc=True))
        except Exception: pass
    try: return iso_utc(pd.to_datetime(clean, utc=True))
    except Exception: return None


def _first_present(row, *names):
    for name in names:
        if name in row.index:
            v=str(row.get(name, "")).strip()
            if v: return v
    return ""


def read_gcat_launch_tsv_bytes(data: bytes, source_url: str = "", progress: bool = False) -> pd.DataFrame:
    """Parse GCAT's canonical full launch list (launch.tsv).

    GCAT's ldes/O,F,E files are *designation lists*, not the launch tables themselves.
    The canonical launch.tsv contains Launch_Date, site/pad, vehicle and launch-code
    fields and is therefore the appropriate input for this research catalog.
    """
    import io
    text=data.decode("utf-8", errors="replace")
    if not text.strip(): raise ValueError("GCAT returned an empty launch.tsv")
    df=pd.read_csv(io.StringIO(text), sep="\t", dtype=str, keep_default_na=False, comment="#")
    df.columns=[str(c).strip() for c in df.columns]
    if progress:
        print(f"GCAT: downloaded {len(data):,} bytes; detected {len(df)} row(s)", flush=True)
        print("GCAT: columns: " + ", ".join(df.columns), flush=True)
    # Be tolerant of documented/current spelling changes, but fail loudly if the
    # essential field is absent instead of silently producing a zero-row cache.
    date_col=next((c for c in ("Launch_Date","LaunchDate","Date") if c in df.columns), None)
    if not date_col:
        preview=" | ".join(text.splitlines()[:3])[:1000]
        raise ValueError(f"GCAT launch.tsv has no Launch_Date column. Columns={df.columns.tolist()}; preview={preview!r}")
    rows=[]; rejected_dates=0
    for _,r in df.iterrows():
        raw_date=str(r.get(date_col,""))
        t=_parse_gcat_date(raw_date)
        if not t:
            rejected_dates += 1; continue
        launch_code=_first_present(r,"Launch_Code","LaunchCode","Launch_Code1","Laun")
        # GCAT documentation: E denotes a pad explosion/no launch; F in the
        # success/failure portion identifies a failed orbital launch attempt.
        lc=launch_code.upper()
        if lc.startswith("E") or lc == "E": etype="pad_explosion"
        elif "F" in lc[:3]: etype="launch_failure"
        else: etype="orbital_launch"
        name=" | ".join(x for x in [
            _first_present(r,"Flight_ID","FlightID"),
            _first_present(r,"Flight"),
            _first_present(r,"Mission"),
            _first_present(r,"FlightCode","Flight_Code")
        ] if x)
        vehicle=" ".join(x for x in [
            _first_present(r,"LV_Type","LVType"), _first_present(r,"Variant","LV_Variant")
        ] if x)
        pad=_first_present(r,"Launch_Pad","LaunchPad","Pad")
        site=_first_present(r,"Launch_Site","LaunchSite","Site")
        tag=_first_present(r,"Launch_Tag","LaunchTag")
        rows.append({
            "source_name":"gcat", "source_event_id":tag,
            "source_name_value":name or tag, "event_type":etype,
            "time_utc":t, "precision":_gcat_precision(raw_date),
            "time_definition":"GCAT Launch_Date (UTC; first motion)", "quality":launch_code,
            "pad":pad, "location":site, "vehicle_mission":" | ".join(x for x in (vehicle,name) if x),
            "status":launch_code, "source_url":source_url,
            "notes":_first_present(r,"Notes"), "time_role":"actual_event_time",
        })
    out=pd.DataFrame(rows)
    if progress:
        print(f"GCAT: parsed {len(out):,} dated launch record(s); rejected {rejected_dates:,} rows without usable dates", flush=True)
        if not out.empty:
            sample=out.iloc[-1]
            print(f"GCAT: sample parsed record: {sample.get('time_utc')} | {sample.get('location')} | {sample.get('pad')} | {sample.get('vehicle_mission')}", flush=True)
    if len(df) and out.empty:
        raise ValueError(f"GCAT parser read {len(df)} rows but produced zero dated launch records")
    return out



def read_gcat_tsv_bytes(data: bytes, list_code: str = "", source_url: str = "") -> pd.DataFrame:
    """Backward-compatible wrapper; list_code is ignored for canonical launch.tsv rows."""
    return read_gcat_launch_tsv_bytes(data, source_url=source_url, progress=False)

def filter_gcat_ksc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    site=df.get("location", pd.Series("", index=df.index)).astype(str)
    pad=df.get("pad", pd.Series("", index=df.index)).astype(str)
    mask=(site.str.contains(r"(^|\b)(CC|CCAFS|CCSFS|KSC)(\b|$)|Cape|Kennedy",case=False,regex=True,na=False) |
          pad.str.contains(r"LC[- ]?39A|LC[- ]?39B|SLC[- ]?(37|40|41|46)|LC[- ]?(17|19|26|34)",case=False,regex=True,na=False))
    return df[mask].copy()


def fetch_gcat(progress: bool = True) -> pd.DataFrame:
    """Fetch and filter GCAT's canonical full launch list."""
    url=GCAT_LAUNCH_URL
    if progress: print(f"GCAT: fetching canonical full launch list: {url}", flush=True)
    req=urllib.request.Request(url, headers={"User-Agent":"KSCRocketSeismology/0.4.1 research catalog"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data=resp.read()
        if progress: print(f"GCAT: HTTP {getattr(resp,'status','?')}; content-type={resp.headers.get('Content-Type','?')}", flush=True)
    raw=read_gcat_launch_tsv_bytes(data, url, progress=progress)
    if progress: print(f"GCAT: filtering {len(raw):,} dated records to Kennedy/Cape Canaveral...", flush=True)
    out=filter_gcat_ksc(raw)
    if progress: print(f"GCAT: retained {len(out):,} KSC/Cape record(s)", flush=True)
    if raw.shape[0] > 0 and out.shape[0] == 0:
        sites=raw.get("location",pd.Series(dtype=str)).value_counts().head(20).to_dict()
        raise ValueError(f"GCAT full launch list parsed correctly but KSC/Cape filter retained zero records. Top sites={sites}")
    return out

def refresh_gcat_cache(cache_path: str | Path) -> tuple[pd.DataFrame, str]:
    cache_path=Path(cache_path)
    print(f"GCAT cache target: {cache_path}", flush=True)
    if cache_path.exists():
        old=read_source_cache(cache_path)
        print(f"GCAT: existing cache found with {len(old)} record(s); preserving unless refresh completes", flush=True)
    else: print("GCAT: no existing cache found", flush=True)
    try:
        df=fetch_gcat(progress=True)
        write_source_cache(df, cache_path, "gcat")
        print(f"GCAT: cache written successfully: {cache_path}", flush=True)
        return df,"refreshed"
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        cached=read_source_cache(cache_path)
        if not cached.empty:
            print(f"GCAT: refresh failed ({exc}); retaining existing cache with {len(cached)} record(s)", flush=True)
            return cached,"cache retained"
        raise RuntimeError(f"GCAT refresh failed and no cache exists at {cache_path}") from exc
