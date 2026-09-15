from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import pandas as pd
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


def _cache_paths(s):
    return (s.root/"data/raw/external/ll2_events.csv", s.root/"data/raw/external/gcat_events.csv")


def _subset_times(df, start, end):
    if df is None or df.empty: return pd.DataFrame()
    t=pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    gs=pd.Timestamp(start); ge=pd.Timestamp(end)
    gs=gs.tz_localize("UTC") if gs.tzinfo is None else gs.tz_convert("UTC")
    ge=ge.tz_localize("UTC") if ge.tzinfo is None else ge.tz_convert("UTC")
    return df.loc[t.between(gs,ge)].copy()


def _is_gcat_air_launch(df):
    if df is None or df.empty: return pd.Series(False,index=getattr(df,'index',None))
    vm=df.get("vehicle_mission",pd.Series("",index=df.index)).astype(str)
    pad=df.get("pad",pd.Series("",index=df.index)).astype(str)
    # GCAT Cape-origin Pegasus launches use the runway as the launch pad. They are
    # air launches, not KSC/Cape pad launches, and are excluded by default.
    return vm.str.contains(r"\bPegasus\b",case=False,regex=True,na=False) | pad.str.match(r"^RW\d+",case=False,na=False)


def _run_reconciliation(s, excel, start, end, use_ll2=True, use_gcat=True,
                        refresh_external=False, include_air_launches=False,
                        replace_events=True):
    ll2_cache,gcat_cache=_cache_paths(s)
    manual=read_manual_excel(excel); sources=[manual]
    curated=manual_events_as_source(s.root/"data/curated/manual_events.csv")
    if not curated.empty: sources.append(curated)

    if use_ll2:
        if refresh_external:
            ll2,status=refresh_ll2_cache(start,end,ll2_cache)
            print(f"LL2 cache: {status}; {len(ll2)} records",flush=True)
        else:
            ll2=read_source_cache(ll2_cache)
            if ll2.empty:
                raise RuntimeError(f"LL2 cache is missing at {ll2_cache}. Run `ksc-rockets fetch-ll2` or use `rebuild --refresh-external`.")
            print(f"LL2 cache: using {ll2_cache} ({len(ll2)} records)",flush=True)
        ll2=_subset_times(ll2,start,end)
        if not ll2.empty: sources.append(ll2)

    if use_gcat:
        if refresh_external:
            gcat,status=refresh_gcat_cache(gcat_cache)
            print(f"GCAT cache: {status}; {len(gcat)} records total",flush=True)
        else:
            gcat=read_source_cache(gcat_cache)
            if gcat.empty:
                raise RuntimeError(f"GCAT cache is missing at {gcat_cache}. Run `ksc-rockets fetch-gcat` or use `rebuild --refresh-external`.")
            print(f"GCAT cache: using {gcat_cache} ({len(gcat)} records total)",flush=True)
        gcat=_subset_times(gcat,start,end)
        if not include_air_launches:
            air=_is_gcat_air_launch(gcat); n=int(air.sum()); gcat=gcat.loc[~air].copy()
            if n: print(f"GCAT: excluded {n} Cape-origin air-launch record(s) (use --include-air-launches to retain)",flush=True)
        print(f"GCAT reconciliation subset: {len(gcat)} records ({pd.Timestamp(start).date()} through {pd.Timestamp(end).date()})",flush=True)
        if not gcat.empty: sources.append(gcat)

    print("Reconciling source records...",flush=True)
    ev,src=reconcile_sources(sources,progress=True)
    processed=s.root/"data/processed"; processed.mkdir(parents=True,exist_ok=True)
    out=processed/"event_reconciliation.csv"; sout=processed/"event_time_sources.csv"
    ev.to_csv(out,index=False); src.to_csv(sout,index=False)

    # The database is a final product of reconciliation: rebuild its base schema,
    # then replace the events table with reconciled events and source provenance.
    if not s.canonical_catalog.exists(): _build_catalog(s)
    build_database(s.canonical_catalog,s.database)
    write_reconciliation(s.database,ev,src,replace_events=replace_events)
    print(f"reconciled events: {len(ev)} -> {out}",flush=True)
    print(f"database updated from reconciled catalog: {s.database}",flush=True)
    return ev,src


def _clean(s, caches=False):
    removed=[]
    processed=s.root/"data/processed"
    if processed.exists():
        shutil.rmtree(processed); removed.append(processed)
    # Only configured generated output directories are removed; raw and curated
    # research inputs are deliberately preserved.
    for p in (s.website_output,s.analysis_output):
        if p.exists(): shutil.rmtree(p); removed.append(p)
    if caches:
        external=s.root/"data/raw/external"
        if external.exists(): shutil.rmtree(external); removed.append(external)
    print("Clean complete.")
    if removed:
        for p in removed: print(f"removed: {p}")
    else: print("nothing to remove")
    if not caches: print("external caches preserved (use `ksc-rockets clean --caches` to remove them)")


def main(argv=None):
    p=argparse.ArgumentParser(prog="ksc-rockets")
    p.add_argument("--config",default=None)
    p.add_argument("--version",action="version",version=f"%(prog)s {__version__}")
    sp=p.add_subparsers(dest="command",required=True)
    for cmd in ("build-catalog","build-db","build-website","analyze","build-all","validate","info"):
        sp.add_parser(cmd)
    c=sp.add_parser("clean",help="Remove generated products; preserve raw/curated inputs and caches by default")
    c.add_argument("--caches",action="store_true",help="Also remove LL2/GCAT external caches")
    f=sp.add_parser("fetch-ll2",help="Refresh the cached Launch Library 2 snapshot")
    f.add_argument("--start",default="2016-01-01T00:00:00Z"); f.add_argument("--end",default="2022-12-31T23:59:59Z")
    sp.add_parser("fetch-gcat",help="Refresh cached GCAT launch snapshot")
    r=sp.add_parser("reconcile-events")
    r.add_argument("--excel",default="data/raw/All_KSC_Rocket_Launches.xlsx",help="Hand-curated workbook")
    r.add_argument("--fetch-ll2",action="store_true",help="Refresh LL2 before reconciling")
    r.add_argument("--no-ll2-cache",action="store_true"); r.add_argument("--no-gcat-cache",action="store_true")
    r.add_argument("--start",default="2016-01-01T00:00:00Z"); r.add_argument("--end",default="2022-12-31T23:59:59Z")
    r.add_argument("--replace-events",action="store_true",help="Compatibility option; v5 reconciliation already replaces canonical DB events")
    r.add_argument("--include-air-launches",action="store_true",help="Include Cape-origin runway/air launches such as Pegasus")
    rb=sp.add_parser("rebuild",help="Clean generated products and rebuild catalog, reconciliation, and database")
    rb.add_argument("--excel",default="data/raw/All_KSC_Rocket_Launches.xlsx")
    rb.add_argument("--refresh-external",action="store_true",help="Delete/refetch LL2 and GCAT caches before rebuilding (slower)")
    rb.add_argument("--include-air-launches",action="store_true")
    rb.add_argument("--start",default="2016-01-01T00:00:00Z"); rb.add_argument("--end",default="2022-12-31T23:59:59Z")
    m=sp.add_parser("add-event")
    m.add_argument("event_type",choices=["orbital_launch","launch_failure","pad_explosion","static_fire","aborted_launch","booster_landing","aircraft_sonic_boom"])
    m.add_argument("time_utc"); m.add_argument("name"); m.add_argument("--pad",default=""); m.add_argument("--source",default="waveform_review"); m.add_argument("--notes",default="")
    a=p.parse_args(argv); s=load_settings(a.config)
    if a.command=="info":
        import kscrockets
        print(f"KSCRocketSeismology {__version__}"); print(f"package: {Path(kscrockets.__file__).resolve()}"); print(f"root: {s.root}"); print(f"database: {s.database}"); return
    ll2_cache,gcat_cache=_cache_paths(s)
    if a.command=="clean": _clean(s,a.caches); return
    if a.command=="fetch-ll2":
        df,status=refresh_ll2_cache(a.start,a.end,ll2_cache); print(f"LL2 cache: {ll2_cache} ({len(df)} KSC/Cape records; {status})"); return
    if a.command=="fetch-gcat":
        df,status=refresh_gcat_cache(gcat_cache); print(f"GCAT cache: {gcat_cache} ({len(df)} KSC/Cape records; {status})"); return
    if a.command=="add-event":
        eid=add_manual_event(s.root/"data/curated/manual_events.csv",a.event_type,a.time_utc,a.name,a.pad,a.source,a.notes); print(f"manual event: {eid}"); return
    if a.command=="reconcile-events":
        _run_reconciliation(s,a.excel,a.start,a.end,use_ll2=not a.no_ll2_cache,use_gcat=not a.no_gcat_cache,
                            refresh_external=a.fetch_ll2,include_air_launches=a.include_air_launches,replace_events=True); return
    if a.command=="rebuild":
        _clean(s,caches=a.refresh_external)
        df=_build_catalog(s); print(f"catalog: {s.canonical_catalog} ({len(df)} events)",flush=True)
        _run_reconciliation(s,a.excel,a.start,a.end,refresh_external=a.refresh_external,
                            include_air_launches=a.include_air_launches,replace_events=True)
        print("Rebuild complete.",flush=True); return
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
