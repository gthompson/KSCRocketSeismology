from __future__ import annotations
import argparse
from pathlib import Path
from . import __version__
from .config import load_settings
from .catalog import build_catalog, read_catalog, validate_catalog
from .database import build_database
from .website import build_website
from .analysis import build_ensemble_products
from .event_catalog import (add_manual_event, read_manual_excel, manual_events_as_source,
    reconcile_sources, write_reconciliation, read_source_cache, refresh_ll2_cache, refresh_gcat_cache)


def _build_catalog(s):
    return build_catalog(s.raw_catalog, s.canonical_catalog, s.year_min, s.year_max,
                         overrides_path=s.event_overrides, id_registry_path=s.event_id_registry)


def main(argv=None):
    p=argparse.ArgumentParser(prog="ksc-rockets")
    p.add_argument("--config",default=None)
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sp=p.add_subparsers(dest="command",required=True)
    for cmd in ("build-catalog","build-db","build-website","analyze","build-all","validate","info"):

        sp.add_parser(cmd)
    f=sp.add_parser("fetch-ll2", help="Refresh the cached Launch Library 2 snapshot")
    f.add_argument("--start", default="2016-01-01T00:00:00Z")
    f.add_argument("--end", default="2022-12-31T23:59:59Z")
    sp.add_parser("fetch-gcat", help="Refresh cached GCAT orbital launch/failure/pad-explosion snapshot")
    r=sp.add_parser("reconcile-events")
    r.add_argument("--excel", required=True, help="Hand-curated All_KSC_Rocket_Launches.xlsx")
    r.add_argument("--fetch-ll2", action="store_true", help="Deprecated convenience: refresh LL2 cache before reconciling")
    r.add_argument("--no-ll2-cache", action="store_true", help="Ignore any cached LL2 snapshot")
    r.add_argument("--no-gcat-cache", action="store_true", help="Ignore any cached GCAT snapshot")
    r.add_argument("--start", default="2016-01-01T00:00:00Z")
    r.add_argument("--end", default="2022-12-31T23:59:59Z")
    r.add_argument("--replace-events", action="store_true", help="Replace events table after reconciliation")
    m=sp.add_parser("add-event")
    m.add_argument("event_type", choices=["orbital_launch","launch_failure","pad_explosion","static_fire","aborted_launch","booster_landing","aircraft_sonic_boom"])
    m.add_argument("time_utc"); m.add_argument("name")
    m.add_argument("--pad", default=""); m.add_argument("--source", default="waveform_review"); m.add_argument("--notes", default="")
    a=p.parse_args(argv); s=load_settings(a.config)
    if a.command=="info":
        import kscrockets
        print(f"KSCRocketSeismology {__version__}")
        print(f"package: {Path(kscrockets.__file__).resolve()}")
        print(f"root: {s.root}")
        print(f"database: {s.database}")
        return
    ll2_cache=s.root/"data/raw/external/ll2_events.csv"
    gcat_cache=s.root/"data/raw/external/gcat_events.csv"
    if a.command=="fetch-ll2":
        df,status=refresh_ll2_cache(a.start,a.end,ll2_cache)
        print(f"LL2 cache: {ll2_cache} ({len(df)} KSC/Cape records; {status})")
        return
    if a.command=="fetch-gcat":
        df,status=refresh_gcat_cache(gcat_cache)
        print(f"GCAT cache: {gcat_cache} ({len(df)} KSC/Cape records; {status})")
        return
    if a.command=="add-event":
        eid=add_manual_event(s.root/"data/curated/manual_events.csv",a.event_type,a.time_utc,a.name,a.pad,a.source,a.notes)
        print(f"manual event: {eid}"); return
    if a.command=="reconcile-events":
        manual=read_manual_excel(a.excel)
        sources=[manual]
        curated=manual_events_as_source(s.root/"data/curated/manual_events.csv")
        if not curated.empty: sources.append(curated)
        if a.fetch_ll2:
            ll2,status=refresh_ll2_cache(a.start,a.end,ll2_cache)
            print(f"LL2 cache: {status}; {len(ll2)} records")
            if not ll2.empty: sources.append(ll2)
        elif not a.no_ll2_cache:
            ll2=read_source_cache(ll2_cache)
            if not ll2.empty:
                sources.append(ll2)
                print(f"LL2 cache: using {ll2_cache} ({len(ll2)} records)")
        if not a.no_gcat_cache:
            gcat=read_source_cache(gcat_cache)
            if not gcat.empty:
                sources.append(gcat)
                print(f"GCAT cache: using {gcat_cache} ({len(gcat)} records)")
        ev,src=reconcile_sources(sources)
        out=s.root/"data/processed/event_reconciliation.csv"; ev.to_csv(out,index=False)
        src.to_csv(s.root/"data/processed/event_time_sources.csv",index=False)
        if not s.database.exists(): build_database(s.canonical_catalog,s.database)
        write_reconciliation(s.database,ev,src,replace_events=a.replace_events)
        print(f"reconciled events: {len(ev)} -> {out}"); return
    if a.command in {"build-catalog","build-all"}:
        df=_build_catalog(s); print(f"catalog: {s.canonical_catalog} ({len(df)} events)")
    if a.command in {"build-db","build-all"}:
        if not s.canonical_catalog.exists(): _build_catalog(s)
        pth=build_database(s.canonical_catalog,s.database); print(f"database: {pth}")
    if a.command in {"build-website","build-all"}:
        if not s.canonical_catalog.exists(): _build_catalog(s)
        pth=build_website(s.canonical_catalog,s.website_output,s.metrics_index,s.website_title,s.website_subtitle); print(f"website: {pth}")
    if a.command in {"analyze","build-all"}:
        if not s.canonical_catalog.exists(): _build_catalog(s)
        products=build_ensemble_products(s.canonical_catalog,s.analysis_output,s.year_min,s.year_max); print(f"analysis: {len(products)} products in {s.analysis_output}")
    if a.command=="validate":
        errs=validate_catalog(read_catalog(s.canonical_catalog)); print("OK" if not errs else "\n".join(errs)); raise SystemExit(1 if errs else 0)

if __name__=="__main__": main()
