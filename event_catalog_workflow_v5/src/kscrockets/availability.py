"""Which stations have waveform day files for each catalog event.

Only the SDS directory tree is read (``YYYY/NET/STA/CHAN.D/NET.STA.LOC.CHAN.D.YYYY.JJJ``); no
waveform data are opened, so a day file counts as available even if it covers only part of the
day. Each archive root is listed once into a (net, sta, chan, year, doy) index.

    ksc-rockets availability --sds 2016-01-01:2023-01-01:/Volumes/classdata/remastered/SDS_KSC \\
                             --sds 2026-01-01:2027-01-01:/Volumes/KSCGTdownld/SDS
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import sqlite3

import pandas as pd

DAYFILE = re.compile(r"^(?P<net>[^.]+)\.(?P<sta>[^.]+)\.(?P<loc>[^.]*)\.(?P<cha>[^.]+)\.D\.(?P<year>\d{4})\.(?P<doy>\d{3})$")


@dataclass(frozen=True)
class Archive:
    """An SDS root used for events with start <= time < end."""
    start: pd.Timestamp
    end: pd.Timestamp
    root: Path

    @classmethod
    def parse(cls, spec: str) -> "Archive":
        start, end, root = spec.split(":", 2)
        return cls(pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC"), Path(root))


def sds_day_index(root: str | Path, years=None, progress: bool = False) -> pd.DataFrame:
    """One row per SDS day file under `root`: net, sta, loc, cha, year, doy, date."""
    root = Path(root); rows = []
    if not root.is_dir(): return pd.DataFrame(columns=["net", "sta", "loc", "cha", "year", "doy", "date"])
    for ydir in sorted(p for p in root.iterdir() if p.is_dir() and p.name.isdigit()):
        if years is not None and int(ydir.name) not in years: continue
        if progress: print(f"availability: listing {ydir}", flush=True)
        for dirpath, _dirs, files in os.walk(ydir):
            for f in files:
                m = DAYFILE.match(f)
                if m: rows.append(m.groupdict())
    df = pd.DataFrame(rows, columns=["net", "sta", "loc", "cha", "year", "doy"])
    if df.empty: return df.assign(date=pd.Series(dtype="datetime64[ns, UTC]"))
    df["year"] = df.year.astype(int); df["doy"] = df.doy.astype(int)
    df["date"] = pd.to_datetime(df.year.astype(str) + df.doy.map("{:03d}".format), format="%Y%j", utc=True)
    return df.drop_duplicates().reset_index(drop=True)


def event_availability(events: pd.DataFrame, archives: list[Archive], indexes: dict,
                       pre: float = 600.0, post: float = 600.0) -> pd.DataFrame:
    """Stations/channels with a day file for every UTC day touched by [t - pre, t + post].

    `indexes` maps archive root -> :func:`sds_day_index` frame. Events outside every archive
    interval get archive '' and zero stations.
    """
    out = []
    for e in events.itertuples():
        t = pd.Timestamp(e.event_time_utc)
        t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        arch = next((a for a in archives if a.start <= t < a.end), None)
        days = pd.date_range((t - pd.Timedelta(seconds=pre)).normalize(), (t + pd.Timedelta(seconds=post)).normalize(), freq="D")
        row = {"event_id": e.event_id, "event_time_utc": e.event_time_utc, "event_type": e.event_type,
               "name": e.name, "vehicle": getattr(e, "vehicle", ""), "pad": getattr(e, "pad", ""),
               "archive": str(arch.root) if arch else "", "n_stations": 0, "n_channels": 0,
               "stations": "", "networks": ""}
        if arch is not None:
            idx = indexes[str(arch.root)]
            sub = idx[idx.date.isin(days)]
            # a channel counts only if it has a file for every day the window touches
            per = sub.groupby(["net", "sta", "loc", "cha"]).date.nunique()
            ok = per[per == len(days)].reset_index()
            row.update(n_stations=ok.sta.nunique(), n_channels=len(ok),
                       stations=";".join(sorted(set(ok.net + "." + ok.sta))),
                       networks=";".join(sorted(ok.net.unique())))
        out.append(row)
    return pd.DataFrame(out)


def coverage_gaps(indexes: dict, start, end, min_days: int = 1) -> pd.DataFrame:
    """Runs of UTC days in [start, end) with no day file in any of the indexed archives."""
    utc = lambda x: (pd.Timestamp(x).tz_localize("UTC") if pd.Timestamp(x).tzinfo is None
                     else pd.Timestamp(x).tz_convert("UTC")).normalize()
    days = pd.date_range(utc(start), utc(end), freq="D", inclusive="left")
    have = set()
    for idx in indexes.values():
        if not idx.empty: have |= set(idx.date)
    missing = [d for d in days if d not in have]
    runs = []
    for d in missing:
        if runs and d - runs[-1][1] == pd.Timedelta(days=1): runs[-1][1] = d
        else: runs.append([d, d])
    df = pd.DataFrame([{"first_day": a.date().isoformat(), "last_day": b.date().isoformat(),
                        "n_days": (b - a).days + 1} for a, b in runs])
    return df[df.n_days >= min_days].reset_index(drop=True) if not df.empty else df


def write_availability_table(db_path: str | Path, table: pd.DataFrame) -> None:
    # counts must be integers in sqlite: a re-attached CSV is read as text, and in SQL
    # '0' > 0 is true, which made every event look as if it had data
    table = table.copy()
    for c in ("n_stations", "n_channels"):
        if c in table:
            table[c] = pd.to_numeric(table[c], errors="coerce").fillna(0).astype(int)
    with sqlite3.connect(db_path) as con:
        table.to_sql("event_waveform_availability", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS idx_availability_event ON event_waveform_availability(event_id)")
