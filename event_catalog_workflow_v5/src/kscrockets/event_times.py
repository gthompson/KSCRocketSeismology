"""Event time fields kept apart from the best time, and the rule that picks the best time.

Each event row carries:

``consensus_time_utc``
    the time reconciliation chose from the source records (LL2, GCAT, the workbook, curated
    manual events): the largest group of distinct sources agreeing within 5 s.
``window_start_utc`` / ``window_end_utc``
    the launch window (LL2 or curated). Can be hours long; an instantaneous window has
    start == end.
``known_time_utc`` + ``known_time_source``
    a confirmed time entered by hand from another source (webcast clock, NASA release, our own
    picks): ``data/curated/known_times.csv``.
``detected_time_utc`` + ``detected_time_method``
    a time measured on our own waveforms (STA/LTA etc.): ``data/curated/detected_times.csv``,
    written by the waveform pilot. It must be a *source-time* estimate (onset minus the travel
    time from the pad), not a station arrival time.

``event_time_utc`` (the best time) is then, in order:

1. ``known_time_utc`` if set;
2. ``consensus_time_utc`` if its precision is ``second`` (a liftoff time to the second from
   LL2/GCAT beats an STA/LTA onset that still carries travel-time error);
3. ``detected_time_utc`` if set;
4. ``consensus_time_utc``.

``event_time_basis`` says which one won (known / consensus / detected) and ``event_time_source``,
``event_time_precision`` follow it. Event ids never depend on these fields.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

KNOWN_COLUMNS = ["event_id", "known_time_utc", "known_time_source", "precision", "source_url", "notes"]
DETECTED_COLUMNS = ["event_id", "detected_time_utc", "detected_time_method", "precision", "notes"]

# Columns added to the events table for these fields.
TIME_FIELD_COLUMNS = {
    "consensus_time_utc": "TEXT", "event_time_basis": "TEXT",
    "window_start_utc": "TEXT", "window_end_utc": "TEXT", "event_end_utc": "TEXT",
    "known_time_utc": "TEXT", "known_time_source": "TEXT",
    "detected_time_utc": "TEXT", "detected_time_method": "TEXT",
}


def _iso(v):
    from .event_catalog import iso_utc
    try: return iso_utc(v)
    except (ValueError, TypeError): return None


def read_time_table(path: str | Path, time_col: str, label_col: str) -> pd.DataFrame:
    """Read a CSV keyed by event_id with one time column and one label column.

    Extra columns are kept. Rows with no event_id or no time are dropped; one row per event_id is
    allowed (a duplicate is an error, so the winner is never ambiguous).
    """
    path = Path(path)
    if not path.exists(): return pd.DataFrame(columns=["event_id", time_col, label_col])
    df = pd.read_csv(path, dtype=str, comment="#").fillna("")
    missing = {"event_id", time_col, label_col} - set(df.columns)
    if missing: raise ValueError(f"{path}: missing column(s) {sorted(missing)}")
    df = df[(df.event_id.str.strip() != "") & (df[time_col].str.strip() != "")].copy()
    df["event_id"] = df.event_id.str.strip()
    df[time_col] = df[time_col].map(_iso)
    bad = df[df[time_col].isna()]
    if not bad.empty: raise ValueError(f"{path}: unparseable {time_col} for {bad.event_id.tolist()}")
    dup = df.event_id[df.event_id.duplicated()]
    if not dup.empty: raise ValueError(f"{path}: more than one row for {sorted(set(dup))}")
    return df.reset_index(drop=True)


def read_known_times(path) -> pd.DataFrame:
    return read_time_table(path, "known_time_utc", "known_time_source")


def read_detected_times(path) -> pd.DataFrame:
    return read_time_table(path, "detected_time_utc", "detected_time_method")


def resolve_event_times(events: pd.DataFrame, known: pd.DataFrame | None = None,
                        detected: pd.DataFrame | None = None, strict: bool = False) -> pd.DataFrame:
    """Attach known/detected times to `events` and recompute event_time_utc by the precedence rule.

    `events` must have event_time_utc (the source consensus on first use) or consensus_time_utc.
    Unknown event ids in `known`/`detected` raise if `strict`, otherwise they are ignored.
    """
    ev = events.copy()
    for c in TIME_FIELD_COLUMNS:
        if c not in ev: ev[c] = None
    first = ev["consensus_time_utc"].isna() | (ev["consensus_time_utc"].astype(str).isin(["", "None", "nan"]))
    ev.loc[first, "consensus_time_utc"] = ev.loc[first, "event_time_utc"]
    for c in ("consensus_time_source", "consensus_time_precision"):
        if c not in ev: ev[c] = None
    first = ev["consensus_time_source"].isna()
    ev.loc[first, "consensus_time_source"] = ev.loc[first, "event_time_source"]
    ev.loc[first, "consensus_time_precision"] = ev.loc[first, "event_time_precision"]

    ids = set(ev.event_id)
    for table, tcol, lcol in ((known, "known_time_utc", "known_time_source"),
                              (detected, "detected_time_utc", "detected_time_method")):
        if table is None or table.empty: continue
        unknown = sorted(set(table.event_id) - ids)
        if unknown and strict: raise ValueError(f"{tcol}: unknown event_id(s) {unknown}")
        m = table.set_index("event_id").copy()
        m[tcol] = m[tcol].map(_iso)
        hit = ev.event_id.isin(m.index)
        ev.loc[hit, tcol] = ev.loc[hit, "event_id"].map(m[tcol])
        ev.loc[hit, lcol] = ev.loc[hit, "event_id"].map(m[lcol])

    def has(v): return v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v) not in ("", "None", "nan")

    out = []
    for r in ev.itertuples(index=False):
        r = r._asdict()
        if has(r["known_time_utc"]):
            r.update(event_time_utc=r["known_time_utc"], event_time_basis="known",
                     event_time_source=f"known:{r['known_time_source']}", event_time_precision="second")
        elif str(r["consensus_time_precision"] or "").lower() != "second" and has(r["detected_time_utc"]):
            r.update(event_time_utc=r["detected_time_utc"], event_time_basis="detected",
                     event_time_source=f"detected:{r['detected_time_method']}", event_time_precision="second")
        else:
            r.update(event_time_utc=r["consensus_time_utc"], event_time_basis="consensus",
                     event_time_source=r["consensus_time_source"], event_time_precision=r["consensus_time_precision"])
        out.append(r)
    return pd.DataFrame(out, columns=list(ev.columns))


def ensure_time_columns(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(events)")}
    for c, t in {**TIME_FIELD_COLUMNS, "consensus_time_source": "TEXT", "consensus_time_precision": "TEXT",
                 "route": "TEXT", "source_url": "TEXT"}.items():
        if c not in cols: con.execute(f"ALTER TABLE events ADD COLUMN {c} {t}")


def apply_times_to_db(db_path: str | Path, known: pd.DataFrame | None = None,
                      detected: pd.DataFrame | None = None, strict: bool = True) -> dict:
    """Load known/detected times into an existing database and recompute event_time_utc.

    This is what the waveform pilot runs after writing detected_times.csv; no rebuild needed.
    Returns counts by event_time_basis.
    """
    with sqlite3.connect(db_path) as con:
        ensure_time_columns(con)
        ev = pd.read_sql("SELECT * FROM events", con)
        # Reset to the source consensus first so removing a row from a CSV takes effect.
        ev["known_time_utc"] = None; ev["known_time_source"] = None
        ev["detected_time_utc"] = None; ev["detected_time_method"] = None
        new = resolve_event_times(ev, known, detected, strict=strict)
        cols = ["event_time_utc", "event_time_basis", "event_time_source", "event_time_precision",
                "consensus_time_utc", "consensus_time_source", "consensus_time_precision",
                "known_time_utc", "known_time_source", "detected_time_utc", "detected_time_method"]
        con.executemany(f"UPDATE events SET {', '.join(c + '=?' for c in cols)} WHERE event_id=?",
                        [[None if pd.isna(r[c]) else r[c] for c in cols] + [r["event_id"]]
                         for r in new.to_dict("records")])
    return new.event_time_basis.value_counts().to_dict()
