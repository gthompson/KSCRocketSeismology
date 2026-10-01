from __future__ import annotations
import argparse, json
from .service import new_service_run, ingest_run, ingest_centaur, status
from .merge_sds_archives import rollback_transaction


def main():
    p=argparse.ArgumentParser(prog="ksc-sds")
    p.add_argument("--config", default="config/ksc.yaml")
    sp=p.add_subparsers(dest="cmd", required=True)
    n=sp.add_parser("new-run"); n.add_argument("start_date"); n.add_argument("--end-date")
    i=sp.add_parser("ingest"); i.add_argument("run_id"); i.add_argument("--instrument", action="append"); i.add_argument("--dry-run", action="store_true"); i.add_argument("--centaur-mode", choices=["fast","slow"])
    c=sp.add_parser("centaur"); c.add_argument("run_id"); c.add_argument("--source"); c.add_argument("--mode", choices=["fast","slow"], default="fast"); c.add_argument("--dry-run", action="store_true")
    s=sp.add_parser("status"); s.add_argument("run_id")
    a=p.parse_args()
    if a.cmd=="new-run": result=str(new_service_run(a.config,a.start_date,a.end_date))
    elif a.cmd=="ingest": result=ingest_run(a.config,a.run_id,a.instrument,dry_run=a.dry_run,centaur_mode=a.centaur_mode)
    elif a.cmd=="centaur": result=ingest_centaur(a.config,a.run_id,mode=a.mode,dry_run=a.dry_run,source=a.source)
    else: result=status(a.config,a.run_id)
    print(json.dumps(result,indent=2,default=str) if not isinstance(result,str) else result)

if __name__ == "__main__": main()
