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
    req = urllib.request.Request(url, headers={"User-Agent": "KSCRocketSeismology/0.5 research catalog"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


# Launch Library 2 location ids: 12 = Cape Canaveral SFS, 27 = Kennedy Space Center.
LL2_CAPE_LOCATION_IDS = (12, 27)
LL2_STATIC_FIRE_EVENT_TYPE = 5
# Booster landing zones on the Cape (return-to-launch-site landings make local sonic booms).
CAPE_LANDING_ZONES = {"LZ-1", "LZ-2", "LZ-40", "LZ-39A"}


def _ll2_offset_seconds(value) -> float | None:
    """'PT7M42S' / '-PT3S' -> seconds."""
    if not value: return None
    try: return pd.Timedelta(str(value)).total_seconds()
    except Exception:
        m = re.fullmatch(r"(-)?P(?:T)?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", str(value))
        if not m: return None
        sec = int(m.group(2) or 0)*3600 + int(m.group(3) or 0)*60 + float(m.group(4) or 0)
        return -sec if m.group(1) else sec


def parse_ll2_launch(x: dict) -> dict:
    """One LL2 2.3.0 launch (mode=normal or detailed) -> source row, with landing metadata."""
    status = (x.get("status") or {}).get("name", "")
    mission = (x.get("mission") or {}).get("name", "")
    rocket = ((x.get("rocket") or {}).get("configuration") or {}).get("full_name", "")
    pad = x.get("pad") or {}; loc = pad.get("location") or {}
    precision = (x.get("net_precision") or {}).get("name", "")
    stages = (x.get("rocket") or {}).get("launcher_stage") or []
    landings = [st.get("landing") or {} for st in stages if st.get("landing")]
    attempted = [l for l in landings if l.get("attempt")]
    zones = sorted({(l.get("landing_location") or {}).get("abbrev", "") for l in attempted} - {""})
    ltypes = sorted({(l.get("type") or {}).get("abbrev", "") for l in attempted} - {""})
    offsets = [_ll2_offset_seconds(t.get("relative_time")) for t in (x.get("timeline") or [])
               if (t.get("type") or {}).get("abbrev") in {"Stage 1 Landing", "Boosters Landing"}]
    offsets = [o for o in offsets if o is not None and o > 0]
    return {
        "source_name": "launch_library_2", "source_event_id": x.get("id", ""),
        "source_name_value": x.get("name", ""),
        "event_type": normalize_event_type(x.get("name", ""), status),
        "time_utc": x.get("net"), "precision": precision.lower(),
        "time_definition": "LL2 NET/T-0", "quality": status,
        "pad": pad.get("name", ""), "location": loc.get("name", ""),
        "vehicle_mission": " | ".join(v for v in (rocket, mission) if v),
        "vehicle": rocket, "launch_designator": x.get("launch_designator") or "",
        "provider": (x.get("launch_service_provider") or {}).get("name", ""),
        "landing_attempt": bool(attempted) if landings else "",
        "landing_success": (all(bool(l.get("success")) for l in attempted) if attempted else ""),
        "landing_pad": ",".join(zones), "landing_type": ",".join(ltypes),
        "landing_offset_s": min(offsets) if offsets else "",
        "status": status, "source_url": x.get("url", ""), "notes": "",
        "time_role": ("scheduled_launch_time" if "failure before launch" in str(x.get("name", "")).lower()
                      else "actual_event_time"),
    }


def ll2_landing_rows(launches: pd.DataFrame, default_offset_s: float | None = None) -> pd.DataFrame:
    """Booster-landing source rows for LL2 launches with a return-to-launch-site landing on the Cape.

    Time = LL2 NET + the 'Stage 1 Landing'/'Boosters Landing' timeline offset when LL2 has one
    (precision 'second'), otherwise + the median offset of the other RTLS landings
    (precision 'estimated'). Landings at sea (droneships) make no local event and are not rows.
    """
    if launches is None or launches.empty or "landing_pad" not in launches: return pd.DataFrame()
    df = launches.copy()
    zones = df["landing_pad"].fillna("").astype(str)
    mask = zones.map(lambda z: bool(set(filter(None, z.split(","))) & CAPE_LANDING_ZONES))
    mask &= df.get("time_role", pd.Series("actual_event_time", index=df.index)).fillna("actual_event_time").eq("actual_event_time")
    df = df[mask]
    if df.empty: return pd.DataFrame()
    off = pd.to_numeric(df["landing_offset_s"], errors="coerce")
    if default_offset_s is None:
        default_offset_s = float(off.median()) if off.notna().any() else 480.0
    rows = []
    for (_, r), o in zip(df.iterrows(), off):
        known = pd.notna(o)
        t = pd.Timestamp(r["time_utc"]) + pd.Timedelta(seconds=float(o if known else default_offset_s))
        cape = [z for z in str(r["landing_pad"]).split(",") if z in CAPE_LANDING_ZONES]
        rows.append({
            "source_name": "launch_library_2", "source_event_id": f"{r['source_event_id']}:landing",
            "source_name_value": f"{r['source_name_value']} booster landing ({', '.join(cape)})",
            "event_type": "booster_landing", "time_utc": iso_utc(t),
            "precision": "second" if known else "estimated",
            "time_definition": ("LL2 NET + LL2 timeline landing offset" if known else
                                f"LL2 NET + median RTLS landing offset ({default_offset_s:.0f} s)"),
            "quality": r.get("landing_success", ""), "pad": cape[0],
            "location": r.get("location", ""), "vehicle_mission": r.get("vehicle_mission", ""),
            "vehicle": r.get("vehicle", ""), "launch_designator": r.get("launch_designator", ""),
            "provider": r.get("provider", ""), "landing_attempt": True,
            "landing_success": r.get("landing_success", ""), "landing_pad": ",".join(cape),
            "landing_type": "RTLS", "landing_offset_s": o if known else "",
            "status": r.get("status", ""), "source_url": r.get("source_url", ""),
            "notes": "Booster landing on the Cape: sonic boom; time not observed, from launch time + offset.",
            "time_role": "actual_event_time",
        })
    return pd.DataFrame(rows)


def parse_ll2_event(x: dict) -> dict | None:
    """LL2 /events/ record -> static_fire source row, if it is a static fire on the Cape/KSC."""
    loc = str(x.get("location") or "")
    if (x.get("type") or {}).get("id") != LL2_STATIC_FIRE_EVENT_TYPE: return None
    if not re.search(r"Kennedy|Cape Canaveral|\bKSC\b|\bLC-?3\d|\bSLC-?\d", loc, re.I): return None
    m = re.search(r"\b(?:S?LC)-?(\d{2}[AB]?)\b", loc)
    return {
        "source_name": "launch_library_2", "source_event_id": f"event:{x.get('id', '')}",
        "source_name_value": x.get("name", ""), "event_type": "static_fire",
        "time_utc": x.get("date"), "precision": "approximate",
        "time_definition": "LL2 event date (scheduled/approximate)", "quality": "LL2 event",
        "pad": ("LC" + m.group(1)) if m else "", "location": loc,
        "vehicle_mission": x.get("name", ""), "vehicle": "", "launch_designator": "", "provider": "",
        "status": "", "source_url": x.get("url", ""), "notes": x.get("description") or "",
        "time_role": "actual_event_time",
    }


def ll2_rows_from_payloads(launch_results: list[dict], event_results: list[dict] = ()) -> pd.DataFrame:
    """LL2 launch + event results -> cache rows: launches, Cape RTLS landings, Cape static fires."""
    launches = pd.DataFrame([parse_ll2_launch(x) for x in launch_results])
    launches = filter_ll2_ksc(launches)
    landings = ll2_landing_rows(launches)
    events = pd.DataFrame([r for r in (parse_ll2_event(x) for x in event_results) if r])
    out = pd.concat([d for d in (launches, landings, events) if not d.empty], ignore_index=True)
    return out.sort_values("time_utc").reset_index(drop=True)


def _ll2_pages(url: str, label: str, max_retries: int, progress: bool) -> list[dict]:
    results=[]; page=0
    while url:
        page += 1; payload=None
        if progress: print(f"LL2 {label}: page {page}: requesting (collected {len(results)} so far)...", flush=True)
        for attempt in range(max_retries + 1):
            try:
                payload=fetch_json(url); break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt >= max_retries:
                    if progress: print(f"LL2 {label}: page {page}: HTTP {exc.code}; giving up on refresh", flush=True)
                    raise
                retry_after=exc.headers.get("Retry-After") if exc.headers else None
                wait=int(retry_after) if retry_after and str(retry_after).isdigit() else min(60, 5 * (2 ** attempt))
                if progress: print(f"LL2 {label}: page {page}: HTTP 429 rate limit; waiting {wait} s before retry {attempt+2}/{max_retries+1}", flush=True)
                time_module.sleep(wait)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if progress: print(f"LL2 {label}: page {page}: network error: {exc}", flush=True)
                raise
        got=payload.get("results", []); results.extend(got)
        if progress: print(f"LL2 {label}: page {page}: received {len(got)} of {payload.get('count')} records", flush=True)
        url=payload.get("next")
    return results


def fetch_ll2(start: str, end: str, location_ids: list[int] | None = LL2_CAPE_LOCATION_IDS,
              base_url: str = "https://ll.thespacedevs.com/2.3.0/",
              max_retries: int = 2, progress: bool = True, static_fires: bool = True) -> pd.DataFrame:
    """Fetch Cape/KSC launches (mode=detailed: landings, timeline) and static fires from LL2.

    LL2 is paginated and unauthenticated use is limited to 15 requests per hour; 2016 to 2026
    takes about 8 requests (100 detailed launches per page, filtered server-side with
    ``location__ids``) plus 2 for the static-fire events.
    """
    if base_url.rstrip("/").endswith("launches"): base_url = base_url.rstrip("/")[:-len("launches")]
    params = {"format":"json", "mode":"detailed", "limit":100,
              "net__gte":iso_utc(start), "net__lte":iso_utc(end), "ordering":"net"}
    if location_ids: params["location__ids"] = ",".join(map(str, location_ids))
    if progress: print(f"LL2: requesting {start} through {end} (location ids {location_ids})", flush=True)
    launches = _ll2_pages(base_url + "launches/?" + urllib.parse.urlencode(params), "launches", max_retries, progress)
    events = []
    if static_fires:
        ep = {"format":"json", "mode":"detailed", "limit":100, "type__ids": LL2_STATIC_FIRE_EVENT_TYPE,
              "date__gte":iso_utc(start), "date__lte":iso_utc(end), "ordering":"date"}
        events = _ll2_pages(base_url + "events/?" + urllib.parse.urlencode(ep), "events", max_retries, progress)
    out = ll2_rows_from_payloads(launches, events)
    if progress: print(f"LL2: download complete: {len(launches)} launches, {len(events)} events -> {len(out)} rows", flush=True)
    return out


def filter_ll2_ksc(df: pd.DataFrame) -> pd.DataFrame:
    """Keep Cape Canaveral/KSC records from a broader LL2 response."""
    if df is None or df.empty:
        return pd.DataFrame()
    location=df["location"].astype(str) if "location" in df else pd.Series("", index=df.index)
    pad=df["pad"].astype(str) if "pad" in df else pd.Series("", index=df.index)
    mask=(location.str.contains("Kennedy|Cape Canaveral",case=False,regex=True,na=False) |
          pad.str.contains("39A|39B|SLC-40|SLC-41|SLC-37|SLC-46|Complex 36",case=False,regex=True,na=False))
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
        df=raw
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


# Event types that are physically distinct from a launch at about the same time: a booster
# landing ~8 min after liftoff, an aircraft boom, a static fire. They only cluster with their own type.
_SEPARATE_TYPE_FAMILIES = {"booster_landing", "aircraft_sonic_boom", "static_fire"}


def _type_family(event_type) -> str:
    t = str(event_type or "")
    return t if t in _SEPARATE_TYPE_FAMILIES else "launch"


def _best_cluster_match(rec: dict, cluster: list[dict], max_hours: float, min_score: float):
    """Match against every source record already in a cluster, not just its first row.

    This is important when one source has a bad time.  For example, a manual Demo-2
    time can be wrong by hours while LL2 and GCAT agree exactly; GCAT must be allowed
    to match the LL2 member of that cluster rather than only the bad manual row.
    """
    r=pd.Series(rec); best=None
    fam=_type_family(rec.get("event_type"))
    # One physical event has at most one record per source: two LL2 (or GCAT) launches a few
    # hours apart are two events however similar their names ('Falcon 9 Block 5 | Starlink ...').
    src=str(rec.get("source_name",""))
    if any(str(m.get("source_name","")) == src and m.get("time_role","actual_event_time") == "actual_event_time"
           for m in cluster):
        return None
    for member in cluster:
        if _type_family(member.get("event_type")) != fam: continue
        score,dt=match_score(r,pd.Series(member))
        if dt <= max_hours*3600 and score >= min_score:
            candidate=(score, -dt)
            if best is None or candidate > best[0]: best=(candidate, member)
    return best


def _preferred_actual_record(actual_cluster: list[dict], consensus_seconds: float = 5.0) -> dict:
    """Choose the preferred event time from independent-source consensus.

    Times are grouped within ``consensus_seconds``.  The group supported by the most
    distinct sources wins.  Manual Excel remains preferred only when support is tied.
    Thus a bad hand-entered time is retained as provenance but does not override two
    independent agreeing sources.
    """
    ordered=sorted(actual_cluster, key=lambda r: pd.Timestamp(r["time_utc"]))
    groups=[]
    for rec in ordered:
        t=pd.Timestamp(rec["time_utc"])
        placed=False
        for g in groups:
            if abs((t-g["anchor"]).total_seconds()) <= consensus_seconds:
                g["records"].append(rec); placed=True; break
        if not placed: groups.append({"anchor":t,"records":[rec]})
    def source_priority(r):
        # Curated manual is a useful tie-breaker, but never beats stronger consensus.
        # Curated sources (the workbook, data/curated/manual_events.csv) rank first.
        order={"gcat":1,"launch_library_2":2}
        return (order.get(str(r.get("source_name","")),0),
                0 if str(r.get("precision","")).lower()=="second" else 1)
    def group_rank(g):
        distinct=len({str(r.get("source_name","")) for r in g["records"]})
        best=min(source_priority(r) for r in g["records"])
        return (-distinct, best, g["anchor"])
    winning=min(groups,key=group_rank)
    return sorted(winning["records"],key=source_priority)[0]


def _clean(v) -> str:
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except (TypeError, ValueError): pass
    v = str(v).strip()
    return "" if v.lower() == "nan" else v


def _cluster_attributes(cluster: list[dict], identity: dict, preferred: dict) -> dict:
    """vehicle, pad, provider, designator and landing fields for one reconciled event.

    Vehicle and pad come from the first source that has them, in the order LL2, GCAT, curated
    (LL2 carries a structured rocket name and pad); both are normalized to one form
    (``classify_vehicle``, ``normalize_pad``). Landing fields come from LL2 only.
    """
    from .catalog import classify_vehicle, normalize_pad
    order = {"launch_library_2": 0, "gcat": 1}
    ranked = sorted(cluster, key=lambda r: order.get(str(r.get("source_name")), 2))
    ll2 = next((r for r in ranked if r.get("source_name") == "launch_library_2"), {})
    vehicle = ""
    for r in ranked:
        text = _clean(r.get("vehicle")) or _clean(r.get("vehicle_mission")) or _clean(r.get("source_name_value"))
        if text:
            v = classify_vehicle(text)
            if v and v != "Unknown": vehicle = v; break
    pad = "Unknown"
    for r in [identity] + ranked:
        p = normalize_pad(r.get("pad"))
        if p != "Unknown": pad = p; break
    designator = next((_clean(r.get("launch_designator")) for r in ranked if _clean(r.get("launch_designator"))), "")
    if not designator:   # GCAT tags of orbital launches are COSPAR launch designators (YYYY-NNN)
        designator = next((_clean(r.get("source_event_id")) for r in ranked if r.get("source_name") == "gcat"
                           and re.fullmatch(r"\d{4}-\d{3}", _clean(r.get("source_event_id")))), "")
    provider = _clean(ll2.get("provider")) or next((_clean(r.get("provider")) for r in ranked if _clean(r.get("provider"))), "")
    if not provider and vehicle in {"Falcon 9", "Falcon Heavy"}: provider = "SpaceX"
    return {
        "vehicle": vehicle or "Unknown", "pad": pad, "provider": provider, "launch_designator": designator,
        "launch_success": ({"Launch Successful": "True", "Launch Failure": "False", "Partial Failure": "Partial"}
                           .get(_clean(ll2.get("status")), "") if identity.get("event_type") != "booster_landing" else ""),
        "landing_attempt": _clean(ll2.get("landing_attempt")), "landing_success": _clean(ll2.get("landing_success")),
        "landing_pad": _clean(ll2.get("landing_pad")), "landing_type": _clean(ll2.get("landing_type")),
    }


def reconcile_sources(sources: list[pd.DataFrame], max_hours: float = 12.0,
                      min_score: float = 0.45, scheduled_match_hours: float = 72.0,
                      progress: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Conservative source clustering with independent-time consensus.

    Each new record is compared with *all* members of an existing cluster.  This
    prevents a bad time in the first/manual record from blocking two agreeing external
    sources.  Ambiguous candidates remain separate for manual review.
    """
    records=[]
    for df in sources:
        if df is not None and not df.empty:
            for rec in df.to_dict("records"):
                rec.setdefault("time_role", "actual_event_time")
                records.append(rec)
    actual=[r for r in records if r.get("time_role", "actual_event_time") == "actual_event_time"]
    scheduled=[r for r in records if r.get("time_role") != "actual_event_time"]
    actual=sorted(actual, key=lambda r: pd.Timestamp(r["time_utc"]))
    if progress:
        print(f"Reconciliation: {len(actual)} actual-time + {len(scheduled)} scheduled-time source records", flush=True)
    clusters=[]
    for nrec,rec in enumerate(actual, 1):
        best=None
        rt=pd.Timestamp(rec["time_utc"])
        for i,c in enumerate(clusters):
            # Records are processed chronologically. If even the newest member of a
            # cluster is outside the time gate, no member can match; avoid expensive
            # token/Series work for the great majority of historical clusters.
            newest=max(pd.Timestamp(x["time_utc"]) for x in c if x.get("time_role","actual_event_time")=="actual_event_time")
            if (rt-newest).total_seconds() > max_hours*3600: continue
            hit=_best_cluster_match(rec,c,max_hours,min_score)
            if hit is not None and (best is None or hit[0] > best[0]): best=(hit[0],i)
        if best is None: clusters.append([rec])
        else: clusters[best[1]].append(rec)
        if progress and (nrec % 100 == 0 or nrec == len(actual)):
            print(f"Reconciliation: processed {nrec}/{len(actual)} actual-time records; {len(clusters)} candidate events", flush=True)

    unmatched_scheduled=[]
    for rec in scheduled:
        r=pd.Series(rec); best=None
        rt=pd.Timestamp(rec["time_utc"])
        for i,c in enumerate(clusters):
            physical=[x for x in c if x.get("time_role","actual_event_time")=="actual_event_time"]
            if physical:
                nearest=min(abs((rt-pd.Timestamp(x["time_utc"])).total_seconds()) for x in physical)
                if nearest > scheduled_match_hours*3600: continue
            for member in c:
                if _type_family(member.get("event_type")) != _type_family(rec.get("event_type")): continue
                rep=pd.Series(member); _,dt=match_score(r,rep)
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
        preferred=_preferred_actual_record(actual_cluster)
        # Preserve a persistent curated ID if present, otherwise use a stable ID based
        # on the preferred consensus record.
        eid=next((r.get("persistent_event_id") for r in actual_cluster if r.get("persistent_event_id")), None) or stable_event_id(preferred["event_type"], preferred["time_utc"], preferred.get("source_name_value",""), preferred.get("pad",""))
        times=[pd.Timestamp(r["time_utc"]) for r in actual_cluster]
        spread=(max(times)-min(times)).total_seconds() if len(times)>1 else 0.0
        # Keep the most human-readable curated identity fields when available, even if
        # an external-source consensus supplies the preferred timestamp.
        identity=(next((r for r in actual_cluster if r.get("source_name")=="manual_excel"), None)
                  or next((r for r in actual_cluster if r.get("source_name") not in {"gcat","launch_library_2"}), None)
                  or next((r for r in actual_cluster if r.get("source_name")=="launch_library_2"), None)
                  or preferred)
        events.append({
            "event_id":eid, "event_type":identity.get("event_type",preferred["event_type"]), "event_time_utc":iso_utc(preferred["time_utc"]),
            "event_time_source":preferred.get("source_name",""), "event_time_quality":preferred.get("quality",""),
            "event_time_precision":preferred.get("precision",""), "time_definition":preferred.get("time_definition",""),
            "name":identity.get("source_name_value",""), "mission":identity.get("vehicle_mission",""),
            **_cluster_attributes(actual_cluster, identity, preferred),
            "source":"reconciled_sources",
            "notes":identity.get("notes",""), "time_spread_s":spread,
            "time_conflict":bool(spread>60), "source_count":len(actual_cluster),
            "scheduled_time_count":len(cluster)-len(actual_cluster),
        })
        for r in cluster: source_rows.append({"event_id":eid, **r})
    for r in unmatched_scheduled: source_rows.append({"event_id":"", **r})
    return pd.DataFrame(events).sort_values("event_time_utc"), pd.DataFrame(source_rows)

# ---------------------------------------------------------------------------
# Persistent reconciled event ids
# ---------------------------------------------------------------------------
# Reconciliation names a new event from a hash of its preferred source record, which would change
# whenever a source's time or name changes. data/curated/reconciled_event_ids.csv freezes ids:
# it maps each source alias (source_name + source_event_id, or source_name + time for sources
# without ids, e.g. the hand-curated workbook) to the event id it was reconciled into.
ID_REGISTRY_COLUMNS = ["event_id", "source_name", "source_event_id", "time_utc"]


def _alias_key(source_name, source_event_id, time_utc) -> tuple[str, str]:
    sid = _clean(source_event_id)
    return (_clean(source_name), sid if sid else "@" + (iso_utc(time_utc) or ""))


def read_id_registry(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists(): return pd.DataFrame(columns=ID_REGISTRY_COLUMNS)
    return pd.read_csv(path, dtype=str).fillna("")


def assign_persistent_ids(events: pd.DataFrame, source_rows: pd.DataFrame,
                          registry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Rename reconciled events to the ids their source aliases had in `registry`.

    Each event takes the registered id most of its source aliases point to. If two events claim
    the same id, the one with more supporting aliases keeps it and the other keeps its new id.
    Returns (events, source_rows, report) with report counts of kept and new ids.
    """
    if events.empty or registry is None or registry.empty:
        return events, source_rows, {"kept": 0, "new": len(events), "contested": []}
    lookup = {_alias_key(r.source_name, r.source_event_id, r.time_utc): r.event_id
              for r in registry.itertuples() if _clean(r.event_id)}
    from collections import Counter
    votes = {}
    for r in source_rows.itertuples():
        eid = _clean(getattr(r, "event_id", ""))
        if not eid: continue
        old = lookup.get(_alias_key(r.source_name, getattr(r, "source_event_id", ""), r.time_utc))
        if old: votes.setdefault(eid, Counter())[old] += 1
    ranked = sorted(((c.most_common(1)[0][1], eid, c.most_common(1)[0][0]) for eid, c in votes.items()), reverse=True)
    rename, taken, contested = {}, set(), []
    for n, eid, old in ranked:
        if old in taken: contested.append((eid, old)); continue
        rename[eid] = old; taken.add(old)
    # A new hashed id must not collide with a registered id kept by another event.
    for eid in events.event_id:
        if eid not in rename and eid in taken:
            raise ValueError(f"New event id {eid} collides with a registered id")
    events = events.copy(); source_rows = source_rows.copy()
    events["event_id"] = events["event_id"].map(lambda e: rename.get(e, e))
    source_rows["event_id"] = source_rows["event_id"].map(lambda e: rename.get(e, e) if _clean(e) else e)
    if events.event_id.duplicated().any():
        raise ValueError("Duplicate event ids after applying the id registry")
    return events, source_rows, {"kept": len(rename), "new": len(events) - len(rename), "contested": contested}


def id_registry_from_sources(source_rows: pd.DataFrame, previous: pd.DataFrame | None = None) -> pd.DataFrame:
    """Registry rows for every source alias in `source_rows`, plus earlier rows not superseded."""
    cur = source_rows[source_rows["event_id"].map(_clean) != ""].copy()
    cur = pd.DataFrame({"event_id": cur["event_id"], "source_name": cur["source_name"].map(_clean),
                        "source_event_id": cur.get("source_event_id", pd.Series("", index=cur.index)).map(_clean),
                        "time_utc": cur["time_utc"].map(iso_utc)})
    frames = [cur]
    if previous is not None and not previous.empty: frames.append(previous[ID_REGISTRY_COLUMNS])
    out = pd.concat(frames, ignore_index=True).fillna("")
    out["_key"] = [_alias_key(a, b, c) for a, b, c in zip(out.source_name, out.source_event_id, out.time_utc)]
    out = out.drop_duplicates("_key", keep="first").drop(columns="_key")
    return out.sort_values(["time_utc", "source_name", "source_event_id"]).reset_index(drop=True)


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
        "vehicle": df.get("vehicle", ""),
        "provider": df.get("provider", ""),
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

    # GCAT's canonical TSV is unusual: the real column header is itself a
    # comment line ("#Launch_Tag\tLaunch_JD\tLaunch_Date...") and is followed
    # by other # metadata/comment lines.  pandas(comment="#") therefore drops
    # the header and promotes the first data row to column names.  Extract the
    # #Launch_Tag header explicitly, then parse only non-comment data rows.
    lines=text.splitlines()
    header_line=next((line for line in lines if line.startswith("#Launch_Tag\t")), None)
    if header_line is None:
        preview=" | ".join(lines[:5])[:1500]
        raise ValueError(f"GCAT launch.tsv has no #Launch_Tag header; preview={preview!r}")
    columns=[c.strip() for c in header_line[1:].split("\t")]
    data_lines=[line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not data_lines:
        raise ValueError("GCAT launch.tsv contains a header but no data rows")
    df=pd.read_csv(
        io.StringIO("\n".join(data_lines)), sep="\t", header=None, names=columns,
        dtype=str, keep_default_na=False, on_bad_lines="warn"
    )
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
        tag=_first_present(r,"Launch_Tag","LaunchTag")
        # GCAT gives pad explosions (no launch) 'E' tags (2026-E01) and an 'E' outcome code ('OE').
        if lc.startswith("E") or lc[1:2] == "E" or re.search(r"-E\d", tag): etype="pad_explosion"
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
    """Return GCAT records whose *Launch_Site* is Cape Canaveral or KSC.

    GCAT uses the site codes ``CC`` and ``KSC`` for these two launch sites.
    Do not infer geography from Launch_Pad: pad identifiers/numbers are not
    globally unique and previously admitted records from unrelated sites.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    site = df.get("location", pd.Series("", index=df.index)).astype(str).str.strip().str.upper()
    return df[site.isin({"CC", "KSC"})].copy()

def _count_gcat_project_interval(df: pd.DataFrame, start: str = "2016-02-24", end: str = "2022-12-02") -> int:
    """Diagnostic count for the historical USF deployment interval, inclusive."""
    if df is None or df.empty:
        return 0
    t = pd.to_datetime(df.get("time_utc"), utc=True, errors="coerce")
    start_ts = pd.Timestamp(start, tz="UTC")
    # Include the entire end date rather than only midnight.
    end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    return int(((t >= start_ts) & (t < end_exclusive)).sum())


def fetch_gcat(progress: bool = True) -> pd.DataFrame:
    """Fetch and filter GCAT's canonical full launch list."""
    url=GCAT_LAUNCH_URL
    if progress: print(f"GCAT: fetching canonical full launch list: {url}", flush=True)
    req=urllib.request.Request(url, headers={"User-Agent":"KSCRocketSeismology/0.5 research catalog"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data=resp.read()
        if progress: print(f"GCAT: HTTP {getattr(resp,'status','?')}; content-type={resp.headers.get('Content-Type','?')}", flush=True)
    raw=read_gcat_launch_tsv_bytes(data, url, progress=progress)
    if progress: print(f"GCAT: filtering {len(raw):,} dated records to Kennedy/Cape Canaveral...", flush=True)
    out=filter_gcat_ksc(raw)
    if progress:
        print(f"GCAT: retained {len(out):,} KSC/Cape record(s) across all dates", flush=True)
        print(
            "GCAT: KSC/Cape records during USF deployment interval "
            f"2016-02-24 through 2022-12-02: {_count_gcat_project_interval(out):,}",
            flush=True,
        )
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
