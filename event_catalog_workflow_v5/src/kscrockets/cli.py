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
    reconcile_sources, write_reconciliation, read_source_cache, refresh_ll2_cache, refresh_gcat_cache,
    read_id_registry, assign_persistent_ids, id_registry_from_sources, EVENT_TYPES,
    ll2_rows_from_raw_dir, write_source_cache, fetch_ll2)
from .event_times import read_known_times, read_detected_times, resolve_event_times, apply_times_to_db

KNOWN_TIMES_CSV="data/curated/known_times.csv"
DETECTED_TIMES_CSV="data/curated/detected_times.csv"
LL2_RAW_DIR="data/raw/external/ll2_raw"


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
                        refresh_external=False, include_air_launches=True,
                        replace_events=True, detected_times=None):
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
        air=_is_gcat_air_launch(gcat); n=int(air.sum())
        if not include_air_launches:
            gcat=gcat.loc[~air].copy()
            if n: print(f"GCAT: excluded {n} Cape-origin air-launch record(s) (--exclude-air-launches)",flush=True)
        elif n:
            gcat.loc[air & gcat.event_type.eq("orbital_launch"),"event_type"]="air_launch"
            print(f"GCAT: kept {n} Cape-origin air-launch record(s) as air_launch",flush=True)
        print(f"GCAT reconciliation subset: {len(gcat)} records ({pd.Timestamp(start).date()} through {pd.Timestamp(end).date()})",flush=True)
        if not gcat.empty: sources.append(gcat)

    print("Reconciling source records...",flush=True)
    ev,src=reconcile_sources(sources,progress=True)
    # Keep reconciled ids stable across rebuilds (see data/curated/reconciled_event_ids.csv).
    registry_path=s.root/"data/curated/reconciled_event_ids.csv"
    registry=read_id_registry(registry_path)
    ev,src,report=assign_persistent_ids(ev,src,registry)
    print(f"Event ids: {report['kept']} kept from {registry_path.name}, {report['new']} new",flush=True)
    for new_id,old_id in report["contested"]:
        print(f"  WARNING: {new_id} also matched registered id {old_id}, which went to another event",flush=True)
    id_registry_from_sources(src,registry).to_csv(registry_path,index=False)
    # Best time: known > consensus (to the second) > detected > consensus (SQLITE_CATALOG.md).
    known=read_known_times(s.root/KNOWN_TIMES_CSV)
    detected=read_detected_times(Path(detected_times) if detected_times else s.root/DETECTED_TIMES_CSV)
    ev=resolve_event_times(ev,known,detected,strict=True)
    print(f"Event times: {len(known)} known, {len(detected)} detected; basis {ev.event_time_basis.value_counts().to_dict()}",flush=True)
    processed=s.root/"data/processed"; processed.mkdir(parents=True,exist_ok=True)
    out=processed/"event_reconciliation.csv"; sout=processed/"event_time_sources.csv"
    ev.to_csv(out,index=False); src.to_csv(sout,index=False)

    # The database is a final product of reconciliation: rebuild its base schema,
    # then replace the events table with reconciled events and source provenance.
    if not s.canonical_catalog.exists(): _build_catalog(s)
    build_database(s.canonical_catalog,s.database)
    write_reconciliation(s.database,ev,src,replace_events=replace_events)
    _load_availability(s)
    print(f"reconciled events: {len(ev)} -> {out}",flush=True)
    print(f"database updated from reconciled catalog: {s.database}",flush=True)
    return ev,src


AVAILABILITY_CSV="data/availability/event_waveform_availability.csv"


def _availability(s, a):
    import sqlite3
    from .availability import Archive, sds_day_index, event_availability, coverage_gaps, write_availability_table
    archives=[Archive.parse(x) for x in a.sds]
    with sqlite3.connect(s.database) as con:
        events=pd.read_sql("SELECT event_id,event_time_utc,event_type,name,vehicle,pad FROM events ORDER BY event_time_utc",con)
    indexes={}
    for arch in archives:
        years=set(range(arch.start.year,(arch.end-pd.Timedelta(seconds=1)).year+1))
        indexes[str(arch.root)]=sds_day_index(arch.root,years=years,progress=True)
        print(f"availability: {arch.root}: {len(indexes[str(arch.root)])} day files",flush=True)
    table=event_availability(events,archives,indexes,pre=a.pre,post=a.post)
    out=(s.root/a.out_dir); out.mkdir(parents=True,exist_ok=True)
    table.to_csv(out/"event_waveform_availability.csv",index=False)
    t0=pd.Timestamp(f"{s.year_min}-01-01",tz="UTC"); t1=pd.Timestamp(s.interval[1])
    gaps=coverage_gaps(indexes,t0,t1)
    gaps.to_csv(out/"sds_coverage_gaps.csv",index=False)
    write_availability_table(s.database,table)
    print(f"availability: {len(table)} events, {int((table.n_stations>0).sum())} with data -> {out}",flush=True)
    print(f"availability: {len(gaps)} gap(s) with no day file in any archive -> {out/'sds_coverage_gaps.csv'}",flush=True)


def _load_availability(s):
    """Re-attach the last availability table (kept outside data/processed) to a rebuilt database."""
    p=s.root/AVAILABILITY_CSV
    if p.exists():
        from .availability import write_availability_table
        write_availability_table(s.database,pd.read_csv(p,dtype=str).fillna(""))
        print(f"availability table re-attached from {p}",flush=True)


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
    ex=sp.add_parser("extract",help="Extract raw SDS waveforms for one or more catalog events")
    ex.add_argument("--event-id")
    ex.add_argument("--all",action="store_true")
    ex.add_argument("--start")
    ex.add_argument("--end")
    ex.add_argument("--event-type",action="append",dest="event_types")
    ex.add_argument("--sds-root",required=True)
    ex.add_argument("--trace-id",action="append",dest="trace_ids",help="Explicit channel; omit to auto-discover")
    ex.add_argument("--station",help="Limit automatic discovery to this station")
    ex.add_argument("--skip-low-rate",action="store_true")
    ex.add_argument("--retry-missing",action="store_true")
    ex.add_argument("--no-availability",action="store_true",help="Skip potentially costly per-channel coverage checks")
    ex.add_argument("--output-dir", help="External event waveform root (default from config/default.toml)")
    ex.add_argument("--pre",type=float,default=30)
    ex.add_argument("--post",type=float,default=240)
    ex.add_argument("--ignore-catalog-window",action="store_true")
    ex.add_argument("--overwrite",action="store_true")
    ex.add_argument("--dry-run",action="store_true")
    c=sp.add_parser("clean",help="Remove generated products; preserve raw/curated inputs and caches by default")
    c.add_argument("--caches",action="store_true",help="Also remove LL2/GCAT external caches")
    f=sp.add_parser("fetch-ll2",help="Refresh the cached Launch Library 2 snapshot")
    f.add_argument("--start",default=None,help="default: config interval start"); f.add_argument("--end",default=None,help="default: config interval end (now when year_max = \"present\")")
    f.add_argument("--from-raw",action="store_true",help=f"Only rebuild ll2_events.csv from the raw pages in {LL2_RAW_DIR}")
    f.add_argument("--wait",action="store_true",help="Sit out the hourly LL2 rate limit instead of failing")
    lt=sp.add_parser("load-times",help="Load known/detected event times into the database and recompute event_time_utc")
    lt.add_argument("--known",default=None,help=f"default: {KNOWN_TIMES_CSV}")
    lt.add_argument("--detected",default=None,help=f"default: {DETECTED_TIMES_CSV}")
    sp.add_parser("fetch-gcat",help="Refresh cached GCAT launch snapshot")
    r=sp.add_parser("reconcile-events")
    r.add_argument("--excel",default="data/raw/All_KSC_Rocket_Launches.xlsx",help="Hand-curated workbook")
    r.add_argument("--fetch-ll2",action="store_true",help="Refresh LL2 before reconciling")
    r.add_argument("--no-ll2-cache",action="store_true"); r.add_argument("--no-gcat-cache",action="store_true")
    r.add_argument("--start",default=None); r.add_argument("--end",default=None)
    r.add_argument("--replace-events",action="store_true",help="Compatibility option; v5 reconciliation already replaces canonical DB events")
    r.add_argument("--exclude-air-launches",action="store_true",help="Drop Cape-origin runway/air launches such as Pegasus (kept by default)")
    r.add_argument("--detected-times",default=None,help=f"CSV keyed by event_id (default: {DETECTED_TIMES_CSV})")
    rb=sp.add_parser("rebuild",help="Clean generated products and rebuild catalog, reconciliation, and database")
    rb.add_argument("--excel",default="data/raw/All_KSC_Rocket_Launches.xlsx")
    rb.add_argument("--refresh-external",action="store_true",help="Delete/refetch LL2 and GCAT caches before rebuilding (slower)")
    rb.add_argument("--exclude-air-launches",action="store_true")
    rb.add_argument("--detected-times",default=None)
    rb.add_argument("--start",default=None); rb.add_argument("--end",default=None)
    av=sp.add_parser("availability",help="Per-event station availability from SDS day files; gaps with no archive")
    av.add_argument("--sds",action="append",required=True,metavar="START:END:ROOT",
                    help="SDS root used for events START <= t < END (repeatable)")
    av.add_argument("--pre",type=float,default=600); av.add_argument("--post",type=float,default=600)
    av.add_argument("--out-dir",default="data/availability")
    kp=sp.add_parser("launchpads-kml",help="Write a Google Earth KML of the pad table (launchpads.csv)")
    kp.add_argument("--out",default=None,help="default: launchpads.csv with a .kml suffix")
    m=sp.add_parser("add-event")
    m.add_argument("event_type",choices=list(EVENT_TYPES))
    m.add_argument("time_utc"); m.add_argument("name"); m.add_argument("--pad",default=""); m.add_argument("--source",default="waveform_review"); m.add_argument("--notes",default="")
    a=p.parse_args(argv); s=load_settings(a.config)
    if a.command in {"fetch-ll2","reconcile-events","rebuild"}:
        a.start=a.start or s.interval[0]; a.end=a.end or s.interval[1]
    if a.command == "extract":
        if not (a.all or a.event_id or a.start or a.end or a.event_types):
            p.error("extract requires --event-id, --all, or a catalog selection filter")
        from .waveforms import extract_catalog
        from flovopy.enhanced.sdsclient import EnhancedSDSClient
        import json
        client=EnhancedSDSClient(a.sds_root)
        root=(Path(a.output_dir).expanduser() if a.output_dir else s.event_waveforms).resolve()
        repo=s.root.resolve()
        if root == repo or repo in root.parents:
            p.error(f"Event waveform output must be outside the repository: {root}")
        # Prevent silent writes to the Mac's internal disk if the volume is unmounted.
        if not root.is_relative_to(Path("/Volumes")):
            p.error(f"Expected an external volume under /Volumes, got: {root}")
        volume=Path("/Volumes") / root.relative_to("/Volumes").parts[0]
        if not volume.is_mount():
            p.error(f"External volume is not mounted: {volume}")
        for result in extract_catalog(s.database,client,root,a.trace_ids,
                    event_id=a.event_id,start=a.start,end=a.end,event_types=a.event_types,
                    pre=a.pre,post=a.post,overwrite=a.overwrite,dry_run=a.dry_run,
                    use_catalog_window=not a.ignore_catalog_window, station=a.station,
                    skip_low_rate=a.skip_low_rate, retry_missing=a.retry_missing,
                    check_availability=not a.no_availability):
            print(json.dumps({k:result.get(k) for k in ("event_id","status","n_traces","waveform","errors")},default=str))
        return

    if a.command=="info":
        import kscrockets
        print(f"KSCRocketSeismology {__version__}"); print(f"package: {Path(kscrockets.__file__).resolve()}"); print(f"root: {s.root}"); print(f"database: {s.database}"); return
    ll2_cache,gcat_cache=_cache_paths(s)
    if a.command=="availability":
        _availability(s,a); return
    if a.command=="launchpads-kml":
        from .kml import write_launchpads_kml
        print(f"KML: {write_launchpads_kml(s.launchpads,a.out)}"); return
    if a.command=="clean": _clean(s,a.caches); return
    if a.command=="fetch-ll2":
        raw=s.root/LL2_RAW_DIR
        if not a.from_raw:
            # Raw pages are kept; a page already in the raw cache is not requested again.
            fetch_ll2(a.start,a.end,raw_dir=raw,max_wait_s=3700 if a.wait else 60)
        df=ll2_rows_from_raw_dir(raw); write_source_cache(df,ll2_cache,"launch_library_2")
        print(f"LL2 cache: {ll2_cache} ({len(df)} KSC/Cape records from {raw})"); return
    if a.command=="load-times":
        known=read_known_times(Path(a.known) if a.known else s.root/KNOWN_TIMES_CSV)
        detected=read_detected_times(Path(a.detected) if a.detected else s.root/DETECTED_TIMES_CSV)
        counts=apply_times_to_db(s.database,known,detected)
        print(f"load-times: {len(known)} known, {len(detected)} detected -> event_time_basis {counts}"); return
    if a.command=="fetch-gcat":
        df,status=refresh_gcat_cache(gcat_cache); print(f"GCAT cache: {gcat_cache} ({len(df)} KSC/Cape records; {status})"); return
    if a.command=="add-event":
        eid=add_manual_event(s.root/"data/curated/manual_events.csv",a.event_type,a.time_utc,a.name,a.pad,a.source,a.notes); print(f"manual event: {eid}"); return
    if a.command=="reconcile-events":
        _run_reconciliation(s,a.excel,a.start,a.end,use_ll2=not a.no_ll2_cache,use_gcat=not a.no_gcat_cache,
                            refresh_external=a.fetch_ll2,include_air_launches=not a.exclude_air_launches,replace_events=True,
                            detected_times=a.detected_times); return
    if a.command=="rebuild":
        _clean(s,caches=a.refresh_external)
        df=_build_catalog(s); print(f"catalog: {s.canonical_catalog} ({len(df)} events)",flush=True)
        _run_reconciliation(s,a.excel,a.start,a.end,refresh_external=a.refresh_external,
                            include_air_launches=not a.exclude_air_launches,replace_events=True,
                            detected_times=a.detected_times)
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
