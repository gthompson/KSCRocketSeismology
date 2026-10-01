"""Transactional SDS archive merger built around EnhancedSDSClient.

Two modes are provided:

``fast``
    Trust SDS filenames/paths.  Files whose canonical target does not exist are
    copied byte-for-byte without opening MiniSEED.  Only filename collisions
    (including ``.part`` files that map onto an existing canonical SDS day)
    are read and merged with EnhancedSDSClient.

``slow``
    Read every MiniSEED file, derive the canonical SDS destination from trace
    headers, split at UTC day boundaries, and merge through EnhancedSDSClient.
    This is intended for validation/repair/import of archives whose names or
    layout cannot be trusted.

Every run is recorded in SQLite.  Before an existing target file is changed it
is copied into a transaction cache.  Newly-created files are recorded.  A
completed transaction can therefore be rolled back, subject to safety checks
that refuse to overwrite/delete a target that appears to have changed since
that transaction.

This module deliberately does *not* hash every source file: doing so would
remove much of the speed advantage when ingesting a large SDS archive directly
from SD media.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence

try:
    from flovopy.enhanced.sdsclient import EnhancedSDSClient
except ImportError:  # compatibility with an older/development package layout
    from flovopy.sds.enhanced_sds_client import EnhancedSDSClient


PART_SUFFIXES = (".part",)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stat_signature(path: Path) -> tuple[int | None, int | None]:
    """Cheap signature used only to make rollback safer (no full-file read)."""
    try:
        st = path.stat()
        return int(st.st_size), int(st.st_mtime_ns)
    except FileNotFoundError:
        return None, None


def _strip_part_suffix(name: str) -> tuple[str, bool]:
    lower = name.lower()
    for suffix in PART_SUFFIXES:
        if lower.endswith(suffix):
            return name[: -len(suffix)], True
    return name, False


def _canonical_sds_info(path: Path):
    """Parse a canonical SDS name, accepting known recorder ``.part`` suffixes."""
    base, was_part = _strip_part_suffix(path.name)
    parsed = EnhancedSDSClient.parse_sds_filename(base)
    if parsed is None:
        return None
    net, sta, loc, chan, dtype, year, day = parsed
    if dtype != "D":
        return None
    return {
        "network": net,
        "station": sta,
        "location": loc,
        "channel": chan,
        "dtype": dtype,
        "year": year,
        "day": day,
        "canonical_name": base,
        "was_part": was_part,
    }


def _target_from_name(source_file: Path, target_root: Path) -> Path | None:
    """Map a trusted SDS filename to its canonical target without reading data."""
    info = _canonical_sds_info(source_file)
    if info is None:
        return None
    return (
        target_root
        / info["year"]
        / info["network"]
        / info["station"]
        / f'{info["channel"]}.D'
        / info["canonical_name"]
    )


def discover_sds_files(source_root: str | Path) -> Iterator[Path]:
    """Yield canonical SDS files and recognized ``.part`` files recursively."""
    root = Path(source_root)
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            p = Path(dirpath) / filename
            if _canonical_sds_info(p) is not None:
                yield p


@dataclass
class MergeSummary:
    transaction_id: str
    mode: str
    discovered: int = 0
    copied: int = 0
    merged: int = 0
    would_copy: int = 0
    would_merge: int = 0
    skipped: int = 0
    errors: int = 0

    def as_dict(self) -> dict:
        return self.__dict__.copy()


class MergeTracker:
    """SQLite transaction/action tracker plus rollback-cache manager."""

    def __init__(self, db_path: str | Path, cache_root: str | Path):
        self.db_path = Path(db_path)
        self.cache_root = Path(cache_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS merge_transactions (
                transaction_id TEXT PRIMARY KEY,
                source_root TEXT NOT NULL,
                target_root TEXT NOT NULL,
                mode TEXT NOT NULL,
                dry_run INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS merge_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                source_path TEXT,
                target_path TEXT NOT NULL,
                action TEXT NOT NULL,
                backup_path TEXT,
                target_existed INTEGER NOT NULL,
                before_size INTEGER,
                before_mtime_ns INTEGER,
                after_size INTEGER,
                after_mtime_ns INTEGER,
                status TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(transaction_id) REFERENCES merge_transactions(transaction_id)
            );
            CREATE INDEX IF NOT EXISTS idx_merge_actions_tx
                ON merge_actions(transaction_id);
            """
        )
        self.conn.commit()

    def begin(self, txid: str, source_root: Path, target_root: Path, mode: str, dry_run: bool):
        self.conn.execute(
            """INSERT INTO merge_transactions
               (transaction_id, source_root, target_root, mode, dry_run, started_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (txid, str(source_root), str(target_root), mode, int(dry_run), _utcnow(), "running"),
        )
        self.conn.commit()

    def finish(self, txid: str, status: str, notes: str | None = None):
        self.conn.execute(
            "UPDATE merge_transactions SET ended_at=?, status=?, notes=? WHERE transaction_id=?",
            (_utcnow(), status, notes, txid),
        )
        self.conn.commit()

    def backup_target(self, txid: str, target: Path, target_root: Path) -> Path:
        rel = target.relative_to(target_root)
        backup = self.cache_root / txid / "modified" / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        return backup

    def action(
        self,
        txid: str,
        source: Path | None,
        target: Path,
        action: str,
        *,
        backup: Path | None = None,
        target_existed: bool,
        before: tuple[int | None, int | None] = (None, None),
        after: tuple[int | None, int | None] = (None, None),
        status: str = "ok",
        message: str | None = None,
    ):
        self.conn.execute(
            """INSERT INTO merge_actions
               (transaction_id, source_path, target_path, action, backup_path,
                target_existed, before_size, before_mtime_ns, after_size,
                after_mtime_ns, status, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                txid,
                str(source) if source else None,
                str(target),
                action,
                str(backup) if backup else None,
                int(target_existed),
                before[0], before[1], after[0], after[1],
                status, message, _utcnow(),
            ),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


def _copy_new_file(source: Path, target: Path):
    """Copy to a temporary sibling and atomically publish it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.copytmp")
    try:
        shutil.copy2(source, tmp)
        os.replace(tmp, target)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def _merge_one_source_file(
    client: EnhancedSDSClient,
    source: Path,
    *,
    merge_strategy: str,
    preprocess: bool,
    verbose: bool,
):
    """Read one source MiniSEED container and merge its traces into SDS."""
    st = client.read_files([source], verbose=verbose)
    if st is None or len(st) == 0:
        raise ValueError(f"No readable MiniSEED traces in {source}")
    return client.write_stream(
        st,
        mode="merge",
        preprocess=preprocess,
        merge=True,
        merge_strategy=merge_strategy,
        verbose=verbose,
    )


def _paths_for_stream(client: EnhancedSDSClient, stream) -> list[Path]:
    """Return canonical destination day-files that write_stream() can touch."""
    split = client._split_stream_to_days(stream)
    return sorted(client._group_stream_by_sds_path(split).keys())


def merge_sds_archives(
    source_sds_dir: str | Path,
    dest_sds_dir: str | Path,
    *,
    mode: str = "fast",
    db_path: str | Path | None = None,
    cache_root: str | Path | None = None,
    dry_run: bool = False,
    merge_strategy: str = "obspy",
    preprocess: bool = False,
    verbose: bool = True,
) -> MergeSummary:
    """Merge one SDS/archive tree into another.

    Parameters
    ----------
    source_sds_dir
        Source archive or subtree (for example a Centaur ``2026`` directory).
    dest_sds_dir
        Root of the canonical target SDS archive.
    mode
        ``"fast"`` trusts SDS filenames.  New canonical files are copied
        byte-for-byte; only collisions are read and waveform-merged.
        ``"slow"`` reads every discovered MiniSEED file and derives output SDS
        paths from the trace headers.
    db_path, cache_root
        Tracking database and rollback cache.  By default these live in hidden
        directories under the destination root.
    dry_run
        Discover and classify operations without changing target files.
        In fast mode this does not open MiniSEED files.
    merge_strategy
        Passed to EnhancedSDSClient/smart_merge for waveform collisions.
    preprocess
        Apply FLOVOpy's preprocessing pipeline before writes.  Normally False
        for trusted Centaur SDS data.
    """
    source_root = Path(source_sds_dir).expanduser().resolve()
    target_root = Path(dest_sds_dir).expanduser().resolve()
    mode = mode.lower().strip()
    if mode not in {"fast", "slow"}:
        raise ValueError("mode must be 'fast' or 'slow'")
    if not source_root.is_dir():
        raise ValueError(f"Source directory does not exist: {source_root}")
    if source_root == target_root:
        raise ValueError("Source and destination must be different directories")
    # Avoid obvious recursive merges in either direction.
    if source_root in target_root.parents or target_root in source_root.parents:
        raise ValueError("Source and destination must not contain one another")

    target_root.mkdir(parents=True, exist_ok=True)
    db_path = Path(db_path) if db_path else target_root / ".merge_tracking.sqlite"
    cache_root = Path(cache_root) if cache_root else target_root / ".merge_cache"

    tracker = MergeTracker(db_path, cache_root)
    txid = uuid.uuid4().hex
    summary = MergeSummary(transaction_id=txid, mode=mode)
    tracker.begin(txid, source_root, target_root, mode, dry_run)
    client = EnhancedSDSClient(str(target_root))

    try:
        for source in discover_sds_files(source_root):
            summary.discovered += 1
            try:
                if mode == "fast":
                    target = _target_from_name(source, target_root)
                    if target is None:  # defensive; discovery already filtered this
                        summary.skipped += 1
                        continue

                    exists = target.exists()
                    if dry_run:
                        if exists or _canonical_sds_info(source)["was_part"]:
                            # A .part whose canonical target is absent still needs a
                            # waveform-aware write so it is published canonically.
                            summary.would_merge += 1
                        else:
                            summary.would_copy += 1
                        continue

                    # A canonical, non-.part file with no target can be copied
                    # without opening the MiniSEED container.
                    was_part = _canonical_sds_info(source)["was_part"]
                    if not exists and not was_part:
                        _copy_new_file(source, target)
                        after = _stat_signature(target)
                        tracker.action(
                            txid, source, target, "COPY",
                            target_existed=False, after=after,
                        )
                        summary.copied += 1
                        continue

                    # Collision (or .part): protect any existing target first,
                    # then let EnhancedSDSClient do the waveform-aware merge.
                    before = _stat_signature(target)
                    backup = None
                    if exists:
                        backup = tracker.backup_target(txid, target, target_root)

                    written = _merge_one_source_file(
                        client, source,
                        merge_strategy=merge_strategy,
                        preprocess=preprocess,
                        verbose=verbose,
                    )
                    if target not in [Path(p) for p in written] and not target.exists():
                        raise RuntimeError(f"Expected SDS target was not written: {target}")
                    after = _stat_signature(target)
                    tracker.action(
                        txid, source, target, "MERGE",
                        backup=backup, target_existed=exists,
                        before=before, after=after,
                    )
                    summary.merged += 1

                else:  # slow
                    st = client.read_files([source], verbose=verbose)
                    if st is None or len(st) == 0:
                        raise ValueError(f"No readable MiniSEED traces in {source}")

                    targets = _paths_for_stream(client, st)
                    if dry_run:
                        summary.would_merge += len(targets)
                        continue

                    protected = {}
                    for target in targets:
                        exists = target.exists()
                        before = _stat_signature(target)
                        backup = tracker.backup_target(txid, target, target_root) if exists else None
                        protected[target] = (exists, before, backup)

                    written = client.write_stream(
                        st,
                        mode="merge",
                        preprocess=preprocess,
                        merge=True,
                        merge_strategy=merge_strategy,
                        verbose=verbose,
                    )
                    written_set = {Path(p) for p in written}

                    for target in targets:
                        exists, before, backup = protected[target]
                        if target not in written_set and not target.exists():
                            raise RuntimeError(f"Expected SDS target was not written: {target}")
                        tracker.action(
                            txid, source, target, "MERGE_SLOW",
                            backup=backup, target_existed=exists,
                            before=before, after=_stat_signature(target),
                        )
                        summary.merged += 1

            except Exception as exc:
                summary.errors += 1
                # Record an error even if a canonical target could not be found.
                fallback_target = (
                    _target_from_name(source, target_root)
                    or (target_root / "<unknown>")
                )
                tracker.action(
                    txid, source, fallback_target, "ERROR",
                    target_existed=fallback_target.exists(),
                    status="error", message=repr(exc),
                )
                if verbose:
                    print(f"ERROR: {source}: {exc}")

        status = "dry-run" if dry_run else ("completed_with_errors" if summary.errors else "completed")
        tracker.finish(txid, status, notes=str(summary.as_dict()))
        return summary

    except BaseException as exc:
        tracker.finish(txid, "aborted", notes=repr(exc))
        raise
    finally:
        tracker.close()


def rollback_merge_session(
    transaction_id: str,
    *,
    db_path: str | Path,
    force: bool = False,
    verbose: bool = True,
) -> dict:
    """Rollback one merge transaction in reverse action order.

    Safety rule
    -----------
    Unless ``force=True``, a target is only removed/restored when its current
    size and mtime still match the post-action signature recorded by the merge.
    This avoids silently undoing later archive changes.
    """
    db_path = Path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    tx = conn.execute(
        "SELECT * FROM merge_transactions WHERE transaction_id=?", (transaction_id,)
    ).fetchone()
    if tx is None:
        conn.close()
        raise ValueError(f"Unknown transaction: {transaction_id}")
    if tx["dry_run"]:
        conn.close()
        raise ValueError("A dry-run transaction changed no files and cannot be rolled back")

    actions = conn.execute(
        """SELECT * FROM merge_actions
           WHERE transaction_id=? AND status='ok'
           ORDER BY id DESC""",
        (transaction_id,),
    ).fetchall()

    restored = removed = refused = 0
    for row in actions:
        target = Path(row["target_path"])
        expected_after = (row["after_size"], row["after_mtime_ns"])
        current = _stat_signature(target)
        if not force and current != expected_after:
            refused += 1
            if verbose:
                print(f"REFUSE changed target: {target}")
            continue

        if row["target_existed"]:
            backup = Path(row["backup_path"]) if row["backup_path"] else None
            if backup is None or not backup.exists():
                refused += 1
                if verbose:
                    print(f"REFUSE missing backup: {target}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.rollbacktmp")
            shutil.copy2(backup, tmp)
            os.replace(tmp, target)
            restored += 1
            if verbose:
                print(f"RESTORE {target}")
        else:
            if target.exists():
                target.unlink()
            removed += 1
            if verbose:
                print(f"REMOVE  {target}")

    status = "rolled_back" if refused == 0 else "rollback_incomplete"
    conn.execute(
        "UPDATE merge_transactions SET status=?, notes=? WHERE transaction_id=?",
        (status, f"rollback restored={restored} removed={removed} refused={refused}", transaction_id),
    )
    conn.commit()
    conn.close()
    return {"restored": restored, "removed": removed, "refused": refused, "status": status}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Merge SDS archives transactionally")
    sub = p.add_subparsers(dest="command", required=True)

    m = sub.add_parser("merge", help="merge a source archive into a target archive")
    m.add_argument("source")
    m.add_argument("target")
    m.add_argument("--mode", choices=("fast", "slow"), default="fast")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--db")
    m.add_argument("--cache")
    m.add_argument("--merge-strategy", default="obspy")
    m.add_argument("--preprocess", action="store_true")
    m.add_argument("--quiet", action="store_true")

    r = sub.add_parser("rollback", help="rollback a previous merge transaction")
    r.add_argument("transaction_id")
    r.add_argument("--db", required=True)
    r.add_argument("--force", action="store_true")
    r.add_argument("--quiet", action="store_true")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "merge":
        result = merge_sds_archives(
            args.source,
            args.target,
            mode=args.mode,
            db_path=args.db,
            cache_root=args.cache,
            dry_run=args.dry_run,
            merge_strategy=args.merge_strategy,
            preprocess=args.preprocess,
            verbose=not args.quiet,
        )
        print(result.as_dict())
        return 1 if result.errors else 0

    result = rollback_merge_session(
        args.transaction_id,
        db_path=args.db,
        force=args.force,
        verbose=not args.quiet,
    )
    print(result)
    return 0 if result["refused"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
