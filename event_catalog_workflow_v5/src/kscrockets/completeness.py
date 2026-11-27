"""Month-by-month completeness of the catalog against independent launch lists (GCAT, LL2).

Every month from the start month to the current month gets one row, including months with no
events. Launches are compared record by record through ``event_aliases``: a GCAT/LL2 launch with
no alias in the catalog, or a catalog launch with no GCAT/LL2 alias, is named in the row, so any
count difference is explained by specific records. Waveform availability plays no part.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

# Catalog types compared with GCAT's orbital launch list (GCAT lists pad explosions as 'E' launches).
LAUNCH_TYPES = ("orbital_launch", "launch_failure", "air_launch", "pad_explosion",
                "suborbital_launch", "aborted_launch")
LL2_LAUNCH_TYPES = ("orbital_launch", "launch_failure", "air_launch", "pad_explosion",
                "suborbital_launch", "aborted_launch")

# Hand-checked explanations for months where the counts differ for a known reason.
KNOWN_NOTES = {
    "2016-02": "Extra catalog event ksc-60d2d5d7be04 is the SES-9 pad abort (Falcon 9 engines lit, then shut down, at 2016-02-29 00:21Z). Its legacy type is aborted_launch from the workbook. GCAT and LL2 count only the launch on 2016-03-04.",
    "2016-10": "No launch: Falcon 9 was grounded after AMOS-6 (2016-09-01), and Hurricane Matthew passed the Cape on 2016-10-07. No other event was found.",
    "2016-09": "AMOS-6 exploded on the pad on 2016-09-01 during a static-fire campaign. GCAT lists it as launch 2016-E05 (a pad explosion). LL2 lists it only as a scheduled launch, 'Failure before launch', with a NET of 2016-09-03.",
    "2026-05": "The New Glenn pad explosion on 2026-05-29 (a static fire) is curated. GCAT lists it as an E launch.",
}


def _month(t: pd.Series) -> pd.Series:
    return pd.to_datetime(t, utc=True, format="ISO8601").dt.strftime("%Y-%m")


def catalog_completeness(db_path: str | Path, gcat_cache: str | Path, ll2_cache: str | Path,
                         start: str = "2016-02", end: str | None = None) -> pd.DataFrame:
    con = sqlite3.connect(db_path)
    ev = pd.read_sql("SELECT event_id, event_type, event_time_utc, name FROM events", con)
    al = pd.read_sql("SELECT event_id, source_name, source_event_id FROM event_aliases", con)
    con.close()
    gcat = pd.read_csv(gcat_cache, dtype=str).fillna("")
    ll2 = pd.read_csv(ll2_cache, dtype=str).fillna("")
    end = end or pd.Timestamp.now(tz="UTC").strftime("%Y-%m")
    months = pd.period_range(start, end, freq="M").strftime("%Y-%m")

    ev["month"] = _month(ev.event_time_utc)
    launches = ev[ev.event_type.isin(LAUNCH_TYPES)]
    gcat = gcat[gcat.time_utc >= start]
    gcat["month"] = _month(gcat.time_utc)
    ll2 = ll2[ll2.event_type.isin(LL2_LAUNCH_TYPES) & ll2.time_role.eq("actual_event_time")
              & ~ll2.source_event_id.str.contains(":")]   # launches only, not landing/scrub/event rows
    ll2 = ll2[ll2.time_utc >= start]
    ll2["month"] = _month(ll2.time_utc)

    in_cat = {(r.source_name, r.source_event_id) for r in al.itertuples()}
    has_gcat = set(al.event_id[al.source_name.eq("gcat")])
    has_ll2 = set(al.event_id[al.source_name.eq("launch_library_2")])
    other_types = sorted(set(ev.event_type) - set(LAUNCH_TYPES))

    rows = []
    for m in months:
        cl = launches[launches.month == m]; g = gcat[gcat.month == m]; l = ll2[ll2.month == m]
        g_missing = [f"{r.source_event_id} {r.vehicle_mission[:40]}" for r in g.itertuples()
                     if ("gcat", r.source_event_id) not in in_cat]
        l_missing = [f"{r.source_name_value[:50]}" for r in l.itertuples()
                     if ("launch_library_2", r.source_event_id) not in in_cat]
        c_no_gcat = [f"{r.event_id} {r.name[:40]}" for r in cl.itertuples() if r.event_id not in has_gcat]
        c_no_ll2 = [f"{r.event_id} {r.name[:40]}" for r in cl.itertuples() if r.event_id not in has_ll2]
        allm = ev[ev.month == m]
        row = {"month": m, "catalog_launches": len(cl), "gcat_launches": len(g), "ll2_launches": len(l),
               "launch_diff_vs_gcat": len(cl) - len(g), "catalog_events_all_types": len(allm),
               **{f"n_{t}": int((allm.event_type == t).sum()) for t in other_types},
               "gcat_not_in_catalog": "; ".join(g_missing), "ll2_not_in_catalog": "; ".join(l_missing),
               "catalog_launch_without_gcat": "; ".join(c_no_gcat),
               "catalog_launch_without_ll2": "; ".join(c_no_ll2)}
        notes = []
        if len(allm) == 0:
            notes.append("No event of any type: GCAT and LL2 list no Cape/KSC launch this month, and no other event was found."
                         if len(g) == 0 and len(l) == 0 else "No catalog event, but a source lists a launch. CHECK")
        elif len(cl) == 0:
            notes.append("No launch from the Cape/KSC (GCAT and LL2 agree)." if len(g) == len(l) == 0 else "CHECK")
        # LL2's /launches/ omits military suborbital launches (Trident, LRHW) and, at the Cape, air launches.
        no_ll2_types = sorted(set(cl[~cl.event_id.isin(has_ll2)].event_type))
        if no_ll2_types and set(no_ll2_types) <= {"suborbital_launch", "air_launch", "pad_explosion"}:
            notes.append(f"LL2 lists fewer launches: it has no record of the catalog's {', '.join(no_ll2_types)} event(s) "
                         "(LL2 omits military suborbital and Cape air launches, and the New Glenn/AMOS-6 pad explosions "
                         "appear in LL2 only as scheduled launches, if at all).")
        if g_missing or c_no_gcat or l_missing:
            notes.append(KNOWN_NOTES.get(m, "Records differ, see the named records. CHECK"))
        elif len(cl) != len(g):
            notes.append(KNOWN_NOTES.get(m, "CHECK"))
        elif m in KNOWN_NOTES:
            notes.append(KNOWN_NOTES[m])
        row["explanation"] = " ".join(notes)
        rows.append(row)
    return pd.DataFrame(rows)
