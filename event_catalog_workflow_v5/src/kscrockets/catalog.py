from __future__ import annotations
from pathlib import Path
import hashlib
import re
import pandas as pd

CANONICAL_COLUMNS = [
    "event_id", "event_type", "launch_designator", "event_time_utc", "time_utc",
    "event_time_source", "event_time_quality", "window_start", "window_end",
    "name", "mission", "vehicle", "pad", "provider", "launch_success",
    "landing_attempt", "landing_success", "landing_pad", "landing_type", "source", "notes"
]


def normalize_pad(value) -> str:
    if pd.isna(value) or not str(value).strip(): return "Unknown"
    s = str(value).strip().upper().replace("SLC-", "").replace("LC-", "")
    s = re.sub(r"\s+", " ", s)
    aliases = {"39A":"SLC-39A","39B":"SLC-39B","40":"SLC-40","41":"SLC-41",
               "37A":"SLC-37A","37B":"SLC-37B","46":"SLC-46"}
    return aliases.get(s, str(value).strip())


def classify_vehicle(text) -> str:
    if pd.isna(text): return "Unknown"
    s = str(text).lower()
    rules = [
        (r"falcon\s*heavy", "Falcon Heavy"), (r"falcon\s*9|falcon 9 full thrust", "Falcon 9"),
        (r"atlas\s*v", "Atlas V"), (r"delta\s*iv", "Delta IV"), (r"delta\s*ii", "Delta II"),
        (r"\bsls\b|artemis", "SLS"), (r"vulcan", "Vulcan"), (r"new\s*glenn", "New Glenn"),
        (r"minotaur", "Minotaur"), (r"astra", "Astra"), (r"electron", "Electron"),
    ]
    for pattern, label in rules:
        if re.search(pattern, s): return label
    return str(text).split("|")[0].strip() or "Unknown"


def classify_event_type(mission) -> str:
    s = str(mission or "").lower()
    if "failure before launch" in s or "explosion" in s: return "explosion"
    if "static fire" in s: return "static_fire"
    if "abort" in s: return "aborted_launch"
    return "launch"


def _legacy_event_id(row: pd.Series) -> str:
    """Fallback only. Existing IDs are frozen in event_id_registry.csv."""
    designator = str(row.get("launch_designator", "") or "").strip()
    identity = designator or f"{row.get('mission','')}|{row.get('pad','')}"
    return "ksc-" + hashlib.sha1(identity.encode()).hexdigest()[:12]


def _load_registry(path: str | Path | None) -> pd.DataFrame:
    if not path or not Path(path).exists(): return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def _assign_registered_ids(out: pd.DataFrame, registry: pd.DataFrame) -> pd.Series:
    if registry.empty: return out.apply(_legacy_event_id, axis=1)
    lookup = {}
    for _, r in registry.iterrows():
        key=(r.get("launch_designator", ""), r.get("mission", ""), r.get("pad", ""))
        lookup[key]=r["event_id"]
    ids=[]
    for _, r in out.iterrows():
        key=(str(r.get("launch_designator", "") or ""), str(r.get("mission", "") or ""), str(r.get("pad", "") or ""))
        ids.append(lookup.get(key) or _legacy_event_id(r))
    return pd.Series(ids, index=out.index)


def apply_event_overrides(out: pd.DataFrame, overrides_path: str | Path | None) -> pd.DataFrame:
    if not overrides_path or not Path(overrides_path).exists(): return out
    overrides=pd.read_csv(overrides_path, dtype=str).fillna("")
    for _, ov in overrides.iterrows():
        mission=ov.get("match_mission", "")
        if not mission: continue
        mask=out["mission"].fillna("").astype(str).eq(mission)
        if not mask.any():
            raise ValueError(f"Curated override did not match catalog mission: {mission}")
        for col in ["event_type","event_time_utc","window_start","window_end",
                    "event_time_source","event_time_quality","notes"]:
            val=ov.get(col, "")
            if val != "": out.loc[mask, col]=val
    return out


def build_catalog(raw_csv: str | Path, output_csv: str | Path | None = None,
                  year_min: int | None = None, year_max: int | None = None,
                  overrides_path: str | Path | None = None,
                  id_registry_path: str | Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(raw_csv)
    for c in ("window_start", "window_end"):
        if c in df: df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    df = df.dropna(subset=["window_start"]).copy()

    out = pd.DataFrame(index=df.index)
    out["launch_designator"] = df.get("launch_designator", "").fillna("") if isinstance(df.get("launch_designator", None), pd.Series) else ""
    out["window_start"] = df["window_start"]
    out["window_end"] = df.get("window_end", df["window_start"])
    # Initial event time is source-table window_start; curated overrides can replace it.
    out["event_time_utc"] = out["window_start"]
    out["time_utc"] = out["event_time_utc"]  # backwards-compatible alias; do not use for new code
    out["event_time_source"] = Path(raw_csv).name
    out["event_time_quality"] = "source_table"
    out["name"] = df.get("spacex_name", df.get("name", "")).fillna("") if isinstance(df.get("spacex_name", None), pd.Series) else df.get("name", "")
    out["mission"] = df.get("mission", df.get("name", ""))
    out["vehicle"] = out["mission"].map(classify_vehicle)
    out["event_type"] = out["mission"].map(classify_event_type)
    out["pad"] = df.get("SLC", "Unknown").map(normalize_pad) if isinstance(df.get("SLC", None), pd.Series) else "Unknown"
    mission_lower = out["mission"].fillna("").astype(str).str.lower()
    out["provider"] = ""
    out.loc[mission_lower.str.contains("falcon|spacex|starlink|dragon"), "provider"] = "SpaceX"
    out["launch_success"] = df.get("launch_success", df.get("success", pd.NA))
    out["landing_attempt"] = df.get("landing_attempt", pd.NA)
    out["landing_success"] = df.get("landing_success", pd.NA)
    out["landing_pad"] = df.get("spacex_landingpad", pd.NA)
    out["landing_type"] = df.get("spacex_landingtype", pd.NA)
    out["source"] = Path(raw_csv).name
    out["notes"] = ""

    out = apply_event_overrides(out, overrides_path)
    for c in ("event_time_utc","window_start","window_end"):
        out[c]=pd.to_datetime(out[c], utc=True, errors="coerce")
    out["time_utc"] = out["event_time_utc"]

    # Filter on corrected event time, not extraction-window time.
    if year_min is not None: out = out[out.event_time_utc.dt.year >= year_min]
    if year_max is not None: out = out[out.event_time_utc.dt.year <= year_max]

    out["event_id"] = _assign_registered_ids(out, _load_registry(id_registry_path))
    out = out.drop_duplicates(["event_id"], keep="first")
    out = out.sort_values("event_time_utc").reset_index(drop=True)
    out = out[CANONICAL_COLUMNS]
    if output_csv:
        output_csv = Path(output_csv); output_csv.parent.mkdir(parents=True, exist_ok=True)
        write_df = out.copy()
        for c in ("event_time_utc", "time_utc", "window_start", "window_end"):
            if c in write_df:
                write_df[c] = write_df[c].map(lambda x: x.isoformat().replace("+00:00", "Z") if pd.notna(x) else "")
        write_df.to_csv(output_csv, index=False)
    return out


def read_catalog(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in ("event_time_utc", "time_utc", "window_start", "window_end"):
        if c in df: df[c] = pd.to_datetime(df[c], utc=True, errors="coerce", format="mixed")
    return df


def validate_catalog(df: pd.DataFrame) -> list[str]:
    errors=[]
    missing=[c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing: errors.append("Missing columns: " + ", ".join(missing))
    if "event_id" in df and df.event_id.duplicated().any(): errors.append("Duplicate event_id values")
    if "event_time_utc" in df and pd.to_datetime(df.event_time_utc, utc=True, errors="coerce").isna().any(): errors.append("Invalid event_time_utc values")
    if {"window_start","window_end"}.issubset(df.columns):
        ws=pd.to_datetime(df.window_start, utc=True, errors="coerce"); we=pd.to_datetime(df.window_end, utc=True, errors="coerce")
        if (we < ws).any(): errors.append("One or more extraction windows have end < start")
    return errors
