#!/usr/bin/env python3
"""Merge Centaur SDS downloads from selected service runs into a master SDS.

This is a project-specific orchestration script for the FLOVOpy ingestion workflow.
Centaur downloads are already SDS, so the reusable implementation is
``flovopy.sds.merge_sds_archives`` (no MiniSEED conversion is necessary).

Dry-run by default. Use --execute to modify the master archive.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flovopy.sds.merge_sds_archives import merge_sds_archives

DEFAULT_RUNS = (
    "20260107_huddle",
    "20260310_service",
    "20260403_service",
    "20260613_service",
    "20260922_service",
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/Volumes/KSCGTdownld"),
                        help="Root containing the service directories and master SDS")
    parser.add_argument("--runs", nargs="+", default=list(DEFAULT_RUNS),
                        help="Service directories to ingest (default: all five)")
    parser.add_argument("--master", type=Path, default=None,
                        help="Master SDS path (default: ROOT/SDS)")
    parser.add_argument("--mode", choices=("fast", "slow"), default="fast")
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument("--execute", action="store_true",
                        help="Actually merge data; without this, dry-run only")
    parser.add_argument("--continue-on-error", action="store_true",
                        help="Continue with later service runs if one fails")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root = args.root.expanduser().resolve()
    master = (args.master or root / "SDS").expanduser().resolve()
    if args.progress_every < 1:
        raise SystemExit("--progress-every must be >= 1")
    sources = [(run, (root / run / "00_download" / "Centaur").resolve())
               for run in args.runs]
    if len(set(args.runs)) != len(args.runs):
        raise SystemExit("Duplicate --runs values")
    for run, source in sources:
        if not source.is_dir():
            raise SystemExit(f"Missing Centaur directory for {run}: {source}")
        if source == master or source in master.parents or master in source.parents:
            raise SystemExit(f"Unsafe source/master directory overlap: {source} / {master}")
    if args.execute and not master.is_dir():
        raise SystemExit(f"Master SDS directory does not exist: {master}")

    print(f"Master SDS: {master}")
    print(f"Mode: {args.mode}; dry_run={not args.execute}")
    failed = []
    for run, source in sources:
        print(f"\n{'=' * 72}\n{run}\nSource: {source}", flush=True)
        try:
            result = merge_sds_archives(
                str(source), str(master), mode=args.mode,
                dry_run=not args.execute, progress_every=args.progress_every,
            )
            print(f"Result for {run}: {result}", flush=True)
        except Exception as exc:
            print(f"ERROR in {run}: {type(exc).__name__}: {exc}", file=sys.stderr)
            failed.append(run)
            if not args.continue_on_error:
                break
    if failed:
        print(f"Failed runs: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nAll selected Centaur runs completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
