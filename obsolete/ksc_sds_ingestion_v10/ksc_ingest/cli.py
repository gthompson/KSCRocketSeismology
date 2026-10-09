from __future__ import annotations
import argparse, json
from .service import new_service_run, ingest_run, ingest_centaur, ingest_sds, ingest_siliconaudio, ingest_gem, status
from .config import load_project, master_sds
from .merge_sds_archives import rollback_merge_session


def main(argv=None):
    p = argparse.ArgumentParser(prog="ksc-sds")
    p.add_argument("--config", default="config/ksc.yaml")
    sp = p.add_subparsers(dest="cmd", required=True)
    n = sp.add_parser("new-run"); n.add_argument("start_date"); n.add_argument("--end-date")
    i = sp.add_parser("ingest"); i.add_argument("run_id"); i.add_argument("--instrument", action="append"); i.add_argument("--dry-run", action="store_true"); i.add_argument("--centaur-mode", choices=["fast", "slow"]); i.add_argument("--progress-every", type=int, default=50)
    c = sp.add_parser("centaur"); c.add_argument("run_id"); c.add_argument("--source"); c.add_argument("--mode", choices=["fast", "slow"], default="fast"); c.add_argument("--dry-run", action="store_true"); c.add_argument("--progress-every", type=int, default=50)
    a = sp.add_parser("merge-sds", help="Merge any existing SDS tree, including mixed-instrument archives")
    a.add_argument("source"); a.add_argument("--mode", choices=["fast", "slow"], default="fast"); a.add_argument("--dry-run", action="store_true"); a.add_argument("--progress-every", type=int, default=50)
    sa = sp.add_parser("siliconaudio", help="Convert station minute MiniSEED to staged SDS")
    sa.add_argument("run_id"); sa.add_argument("--station"); sa.add_argument("--year", type=int)
    sa.add_argument("--pattern", default="*.ms"); sa.add_argument("--dry-run", action="store_true")
    sa.add_argument("--allow-partial-days", action="store_true")
    gm = sp.add_parser("gem", help="Stage gemconvert MiniSEED into Gem/SDS")
    gm.add_argument("run_id"); gm.add_argument("--mapping")
    gm.add_argument("--pattern", default="*.mseed")
    gm.add_argument("--dry-run", action="store_true")
    gm.add_argument("--allow-unmapped", action="store_true")
    gps = sp.add_parser("gem-gps", help="Summarize gemconvert GPS logs as a QC CSV")
    gps.add_argument("gps_dir"); gps.add_argument("output_csv"); gps.add_argument("--mapping")
    gr = sp.add_parser("gem-report", help="Summarize Gem waveforms, GPS, metadata into one CSV")
    gr.add_argument("converted_root", help="Directory containing mseed/, gps/, metadata/")
    gr.add_argument("output_csv"); gr.add_argument("--mapping", required=True)
    gr.add_argument("--daily-csv"); gr.add_argument("--deployment-start")
    gr.add_argument("--deployment-end")
    gc = sp.add_parser("gem-convert", help="Run upstream gemconvert in a prepared raw/ workspace")
    gc.add_argument("workspace"); gc.add_argument("--executable", default="gemconvert")
    r = sp.add_parser("rollback"); r.add_argument("transaction_id"); r.add_argument("--force", action="store_true")
    s = sp.add_parser("status"); s.add_argument("run_id")
    args = p.parse_args(argv)
    if args.cmd == "new-run": result = str(new_service_run(args.config, args.start_date, args.end_date))
    elif args.cmd == "ingest": result = ingest_run(args.config, args.run_id, args.instrument, dry_run=args.dry_run, centaur_mode=args.centaur_mode, progress_every=args.progress_every)
    elif args.cmd == "centaur": result = ingest_centaur(args.config, args.run_id, mode=args.mode, dry_run=args.dry_run, source=args.source, progress_every=args.progress_every)
    elif args.cmd == "merge-sds": result = ingest_sds(args.config, args.source, mode=args.mode, dry_run=args.dry_run, progress_every=args.progress_every)
    elif args.cmd == "siliconaudio":
        result = ingest_siliconaudio(args.config, args.run_id, station=args.station,
                                    year=args.year, pattern=args.pattern,
                                    dry_run=args.dry_run, strict=not args.allow_partial_days)
    elif args.cmd == "gem":
        result = ingest_gem(args.config, args.run_id, mapping=args.mapping,
                            pattern=args.pattern, dry_run=args.dry_run,
                            strict=not args.allow_unmapped)
    elif args.cmd == "gem-gps":
        from .gem import summarize_gem_gps
        df = summarize_gem_gps(args.gps_dir, args.output_csv, mapping=args.mapping)
        result = {"output_csv": args.output_csv, "stations": len(df)}
    elif args.cmd == "gem-report":
        from .gem_report import report_gem_deployment
        result = report_gem_deployment(args.converted_root, args.mapping, args.output_csv,
                                       daily_csv=args.daily_csv, deployment_start=args.deployment_start,
                                       deployment_end=args.deployment_end)
    elif args.cmd == "gem-convert":
        from .gem import run_gemconvert
        result = {"mseed_dir": str(run_gemconvert(args.workspace, executable=args.executable))}
    elif args.cmd == "rollback":
        target = master_sds(load_project(args.config))
        result = rollback_merge_session(args.transaction_id, db_path=target / ".merge_tracking.sqlite", force=args.force)
    else: result = status(args.config, args.run_id)
    print(json.dumps(result, indent=2, default=str) if not isinstance(result, str) else result)
    return 0

if __name__ == "__main__": main()
