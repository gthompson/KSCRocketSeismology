from __future__ import annotations
from pathlib import Path
import hashlib
import re
import pandas as pd

CANONICAL_COLUMNS = [
    "event_id", "launch_designator", "time_utc", "window_start", "window_end",
    "name", "mission", "vehicle", "pad", "provider", "launch_success",
    "landing_attempt", "landing_success", "landing_pad", "landing_type", "source"
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


def _event_id(row: pd.Series) -> str:
    designator = str(row.get("launch_designator", "") or "").strip()
    t = pd.to_datetime(row.get("window_start"), utc=True, errors="coerce")
    key = f"{designator}|{t.isoformat() if pd.notna(t) else ''}|{row.get('mission','')}"
    return "ksc-" + hashlib.sha1(key.encode()).hexdigest()[:12]


def build_catalog(raw_csv: str | Path, output_csv: str | Path | None = None,
                  year_min: int | None = None, year_max: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(raw_csv)
    for c in ("window_start", "window_end"):
        if c in df: df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    df = df.dropna(subset=["window_start"]).copy()
    if year_min is not None: df = df[df.window_start.dt.year >= year_min]
    if year_max is not None: df = df[df.window_start.dt.year <= year_max]

    out = pd.DataFrame(index=df.index)
    out["launch_designator"] = df.get("launch_designator", "")
    out["window_start"] = df["window_start"]
    out["window_end"] = df.get("window_end", df["window_start"])
    out["time_utc"] = out["window_start"]
    out["name"] = df.get("spacex_name", df.get("name", "")).fillna("") if isinstance(df.get("spacex_name", None), pd.Series) else df.get("name", "")
    out["mission"] = df.get("mission", df.get("name", ""))
    out["vehicle"] = out["mission"].map(classify_vehicle)
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
    out["event_id"] = out.apply(_event_id, axis=1)

    # Stable de-duplication. The historical merged table contains exact duplicate
    # launch rows, so retain distinct times even if a designator is reused/missing.
    out = out.drop_duplicates(["launch_designator", "time_utc", "mission", "pad"], keep="first")
    out = out.sort_values("time_utc").reset_index(drop=True)
    out = out[CANONICAL_COLUMNS]
    if output_csv:
        output_csv = Path(output_csv); output_csv.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(output_csv, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    return out


def read_catalog(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in ("time_utc", "window_start", "window_end"):
        if c in df: df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    return df


def validate_catalog(df: pd.DataFrame) -> list[str]:
    errors=[]
    missing=[c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing: errors.append("Missing columns: " + ", ".join(missing))
    if "event_id" in df and df.event_id.duplicated().any(): errors.append("Duplicate event_id values")
    if "time_utc" in df and pd.to_datetime(df.time_utc, utc=True, errors="coerce").isna().any(): errors.append("Invalid time_utc values")
    return errors
