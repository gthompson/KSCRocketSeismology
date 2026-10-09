#!/usr/bin/env python3
"""
recover_gecko_sd.py

Safely recover Gecko / Silicon Graphics digitizer files from an SD card whose
filesystem may contain corrupt directory entries, duplicate directory records,
or malformed filenames.

Expected source layout:

    SD_CARD_ROOT/
        data/
            YYYY/
                MM/
                    DD/
                        HH/
                            YYYY-MM-DD hhmm ss STATION.ms
                            YYYY-MM-DD hhmm ss STATION.ss
        histogram/
            YYYY-MM-DD.csv

You may pass either SD_CARD_ROOT or SD_CARD_ROOT/data as the source.

Destination layout:

    <destination>/
        YYYY/
            MM/
                DD/
                    HH/
                        ... .ms / .ss
        histogram/
            YYYY-MM-DD.csv
        gecko_recovery.log

Typical usage:

    python recover_gecko_sd.py "/Volumes/NO NAME" \
        "/path/to/00_downloads/SiliconGraphics"

or:

    python recover_gecko_sd.py "/Volumes/NO NAME/data" \
        "/path/to/00_downloads/SiliconGraphics"

Dry run:

    python recover_gecko_sd.py "/Volumes/NO NAME" \
        "/path/to/00_downloads/SiliconGraphics" \
        --dry-run

Only station B23:

    python recover_gecko_sd.py "/Volumes/NO NAME" \
        "/path/to/00_downloads/SiliconGraphics" \
        --station B23

SHA256 verify copied files and same-sized existing files:

    python recover_gecko_sd.py "/Volumes/NO NAME" \
        "/path/to/00_downloads/SiliconGraphics" \
        --verify

By default:
- malformed directory/file names are rejected and logged;
- symlinks are not followed;
- duplicate apparent pathnames are processed once;
- existing destination files with the same size are skipped;
- existing destination files with a different size are left untouched and logged;
- new files are first written as *.partial, checked for size, then atomically renamed.

Use --overwrite-mismatched only if you explicitly want a source file to replace
an existing destination file whose size differs.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Tuple


YEAR_RE = re.compile(r"^\d{4}$")
MONTH_RE = re.compile(r"^(0[1-9]|1[0-2])$")
DAY_RE = re.compile(r"^(0[1-9]|[12]\d|3[01])$")
HOUR_RE = re.compile(r"^([01]\d|2[0-3])$")

DATA_FILE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}) "
    r"(?P<hhmm>\d{4}) "
    r"(?P<ss>\d{2}) "
    r"(?P<station>[A-Za-z0-9_-]+)\."
    r"(?P<ext>ms|ss)$",
    re.ASCII,
)

HISTOGRAM_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})\.csv$", re.ASCII)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely copy valid Gecko/Silicon Graphics .ms, .ss, and histogram "
            "CSV files from a potentially corrupt SD-card filesystem."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  %(prog)s "/Volumes/NO NAME" \
      "/Volumes/archive/202609_service/00_downloads/SiliconGraphics"

  %(prog)s "/Volumes/NO NAME/data" \
      "./00_downloads/SiliconGraphics" \
      --station B23 --dry-run

  %(prog)s "/Volumes/NO NAME" \
      "./00_downloads/SiliconGraphics" \
      --verify
""",
    )

    parser.add_argument(
        "source",
        type=Path,
        help="SD-card root, or the card's data/ directory.",
    )
    parser.add_argument(
        "destination",
        type=Path,
        help="Destination directory, normally 00_downloads/SiliconGraphics/.",
    )
    parser.add_argument(
        "--station",
        help="Only recover this station code, e.g. B23. Default: all stations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would happen without writing destination files.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "SHA256-verify newly copied files and same-sized existing files. "
            "This is much slower and rereads the SD card."
        ),
    )
    parser.add_argument(
        "--overwrite-mismatched",
        action="store_true",
        help=(
            "Replace destination files when their size differs from the source. "
            "Without this option, mismatches are logged and left untouched."
        ),
    )
    parser.add_argument(
        "--quiet-existing",
        action="store_true",
        help="Do not print a line for every same-sized existing file.",
    )
    return parser.parse_args()


class Logger:
    def __init__(self, path: Path, dry_run: bool):
        self.path = path
        self.dry_run = dry_run

    def write(self, message: str = "") -> None:
        print(message)
        # A dry run should not create anything in the destination.
        if self.dry_run:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", errors="backslashreplace") as f:
            f.write(message + "\n")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def safe_name(name: str) -> str:
    """Printable/loggable representation even for malformed Unicode."""
    return name.encode("utf-8", "backslashreplace").decode("utf-8", "replace")


def safe_scandir(path: Path, log: Logger, counts: Counter) -> list[os.DirEntry]:
    try:
        with os.scandir(path) as it:
            return list(it)
    except (OSError, UnicodeError) as exc:
        counts["scan_errors"] += 1
        log.write(f"SCAN ERROR: {safe_name(str(path))}: {exc}")
        return []


def entry_is_dir(entry: os.DirEntry, log: Logger, counts: Counter) -> bool:
    try:
        return entry.is_dir(follow_symlinks=False)
    except (OSError, UnicodeError) as exc:
        counts["entry_errors"] += 1
        log.write(f"BAD DIRECTORY ENTRY: {safe_name(entry.path)}: {exc}")
        return False


def entry_is_file(entry: os.DirEntry, log: Logger, counts: Counter) -> bool:
    try:
        return entry.is_file(follow_symlinks=False)
    except (OSError, UnicodeError) as exc:
        counts["entry_errors"] += 1
        log.write(f"BAD FILE ENTRY: {safe_name(entry.path)}: {exc}")
        return False


def valid_calendar_date(year: str, month: str, day: str) -> bool:
    try:
        datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_valid_data_filename(
    name: str,
    station_filter: Optional[str],
    year: str,
    month: str,
    day: str,
    hour: str,
) -> bool:
    """
    Validate filename structure and also require the timestamp encoded in the
    filename to agree with the directory YYYY/MM/DD/HH containing it.
    """
    m = DATA_FILE_RE.fullmatch(name)
    if not m:
        return False

    if station_filter and m.group("station") != station_filter:
        return False

    date_text = m.group("date")
    hhmm = m.group("hhmm")
    sec = m.group("ss")

    try:
        dt = datetime.strptime(
            f"{date_text} {hhmm} {sec}",
            "%Y-%m-%d %H%M %S",
        )
    except ValueError:
        return False

    if dt.strftime("%Y") != year:
        return False
    if dt.strftime("%m") != month:
        return False
    if dt.strftime("%d") != day:
        return False
    if dt.strftime("%H") != hour:
        return False

    return True


def valid_histogram_filename(name: str) -> bool:
    m = HISTOGRAM_RE.fullmatch(name)
    if not m:
        return False
    try:
        datetime.strptime(m.group("date"), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def determine_source_layout(source_arg: Path) -> Tuple[Path, Optional[Path], Path]:
    """
    Return:
        data_source, histogram_source_or_none, card_root

    Accept either:
        /Volumes/NO NAME
    or:
        /Volumes/NO NAME/data
    """
    source = source_arg.expanduser().resolve()

    if source.name == "data":
        data_source = source
        card_root = source.parent
        histogram_source = card_root / "histogram"
    elif (source / "data").is_dir():
        card_root = source
        data_source = source / "data"
        histogram_source = source / "histogram"
    else:
        raise ValueError(
            f"Could not find a Gecko data directory. Expected either:\n"
            f"  {source}/data\n"
            f"or for the supplied source itself to be named 'data'."
        )

    if not histogram_source.is_dir():
        histogram_source = None

    return data_source, histogram_source, card_root


def copy_one(
    src: Path,
    dst: Path,
    rel_display: str,
    args: argparse.Namespace,
    log: Logger,
    counts: Counter,
) -> None:
    """
    Safely copy one file.

    New/replacement data are written to a .partial file in the destination
    directory first and atomically renamed only after a complete size check.
    """
    try:
        src_size = src.stat().st_size
    except OSError as exc:
        counts["source_stat_errors"] += 1
        log.write(f"SOURCE STAT ERROR: {safe_name(str(src))}: {exc}")
        return

    if dst.exists():
        try:
            dst_size = dst.stat().st_size
        except OSError as exc:
            counts["destination_stat_errors"] += 1
            log.write(f"DEST STAT ERROR: {safe_name(str(dst))}: {exc}")
            return

        if dst_size == src_size:
            if args.verify:
                try:
                    source_hash = sha256_file(src)
                    dest_hash = sha256_file(dst)
                except OSError as exc:
                    counts["verify_errors"] += 1
                    log.write(f"VERIFY ERROR: {rel_display}: {exc}")
                    return

                if source_hash != dest_hash:
                    counts["checksum_mismatches"] += 1
                    log.write(
                        f"CHECKSUM MISMATCH: {rel_display} "
                        f"(same size, different SHA256)"
                    )
                    if not args.overwrite_mismatched:
                        return
                else:
                    counts["existing_verified"] += 1
                    if not args.quiet_existing:
                        print(f"EXISTS VERIFIED: {rel_display}")
                    return
            else:
                counts["existing_same_size"] += 1
                if not args.quiet_existing:
                    print(f"EXISTS: {rel_display}")
                return
        else:
            counts["size_mismatches"] += 1
            log.write(
                f"SIZE MISMATCH: {rel_display}: "
                f"source={src_size}, destination={dst_size}"
            )
            if not args.overwrite_mismatched:
                return

    if args.dry_run:
        action = "WOULD REPLACE" if dst.exists() else "WOULD COPY"
        print(f"{action}: {rel_display}")
        counts["would_copy"] += 1
        return

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        counts["destination_errors"] += 1
        log.write(f"MKDIR ERROR: {safe_name(str(dst.parent))}: {exc}")
        return

    tmp = dst.with_name(dst.name + ".partial")

    try:
        if tmp.exists():
            tmp.unlink()

        with src.open("rb") as fin, tmp.open("wb") as fout:
            shutil.copyfileobj(fin, fout, length=1024 * 1024)
            fout.flush()
            os.fsync(fout.fileno())

        copied_size = tmp.stat().st_size
        if copied_size != src_size:
            raise IOError(
                f"size mismatch after copy: source={src_size}, copied={copied_size}"
            )

        if args.verify:
            source_hash = sha256_file(src)
            copied_hash = sha256_file(tmp)
            if source_hash != copied_hash:
                raise IOError("SHA256 mismatch after copy")

        # Atomic rename on the destination filesystem.
        os.replace(tmp, dst)

        counts["copied"] += 1
        print(f"COPIED: {rel_display}")

    except (OSError, IOError) as exc:
        counts["copy_errors"] += 1
        log.write(f"COPY ERROR: {safe_name(str(src))}: {exc}")
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def recover_data_tree(
    data_source: Path,
    destination: Path,
    args: argparse.Namespace,
    log: Logger,
    counts: Counter,
    seen_paths: set[str],
) -> None:
    """
    Traverse only a strict YYYY/MM/DD/HH tree. No generic recursive walk is used.
    This is intentional: malformed/corrupt directory names are never descended.
    """

    for year_entry in safe_scandir(data_source, log, counts):
        counts["directory_entries_seen"] += 1

        if not entry_is_dir(year_entry, log, counts):
            counts["rejected_entries"] += 1
            continue

        year = year_entry.name
        if not YEAR_RE.fullmatch(year):
            counts["rejected_directories"] += 1
            log.write(f"REJECT DIR: {safe_name(year_entry.path)}")
            continue

        year_path = Path(year_entry.path)

        for month_entry in safe_scandir(year_path, log, counts):
            counts["directory_entries_seen"] += 1

            if not entry_is_dir(month_entry, log, counts):
                counts["rejected_entries"] += 1
                continue

            month = month_entry.name
            if not MONTH_RE.fullmatch(month):
                counts["rejected_directories"] += 1
                log.write(f"REJECT DIR: {safe_name(month_entry.path)}")
                continue

            month_path = Path(month_entry.path)

            for day_entry in safe_scandir(month_path, log, counts):
                counts["directory_entries_seen"] += 1

                if not entry_is_dir(day_entry, log, counts):
                    counts["rejected_entries"] += 1
                    continue

                day = day_entry.name
                if not DAY_RE.fullmatch(day) or not valid_calendar_date(year, month, day):
                    counts["rejected_directories"] += 1
                    log.write(f"REJECT DIR: {safe_name(day_entry.path)}")
                    continue

                day_path = Path(day_entry.path)

                for hour_entry in safe_scandir(day_path, log, counts):
                    counts["directory_entries_seen"] += 1

                    if not entry_is_dir(hour_entry, log, counts):
                        counts["rejected_entries"] += 1
                        continue

                    hour = hour_entry.name
                    if not HOUR_RE.fullmatch(hour):
                        counts["rejected_directories"] += 1
                        log.write(f"REJECT DIR: {safe_name(hour_entry.path)}")
                        continue

                    hour_path = Path(hour_entry.path)

                    for file_entry in safe_scandir(hour_path, log, counts):
                        counts["file_entries_seen"] += 1

                        if not entry_is_file(file_entry, log, counts):
                            counts["rejected_entries"] += 1
                            continue

                        filename = file_entry.name

                        if not parse_valid_data_filename(
                            filename,
                            args.station,
                            year,
                            month,
                            day,
                            hour,
                        ):
                            counts["rejected_files"] += 1
                            log.write(f"REJECT FILE: {safe_name(file_entry.path)}")
                            continue

                        relative = Path(year, month, day, hour, filename)
                        key = relative.as_posix()

                        if key in seen_paths:
                            counts["duplicate_path_entries"] += 1
                            continue

                        seen_paths.add(key)
                        counts["valid_data_files"] += 1

                        copy_one(
                            Path(file_entry.path),
                            destination / relative,
                            key,
                            args,
                            log,
                            counts,
                        )


def recover_histograms(
    histogram_source: Optional[Path],
    destination: Path,
    args: argparse.Namespace,
    log: Logger,
    counts: Counter,
    seen_paths: set[str],
) -> None:
    if histogram_source is None:
        counts["histogram_directory_missing"] += 1
        log.write("NOTE: histogram/ directory not found; skipping histograms.")
        return

    for entry in safe_scandir(histogram_source, log, counts):
        counts["histogram_entries_seen"] += 1

        if not entry_is_file(entry, log, counts):
            counts["rejected_entries"] += 1
            continue

        if not valid_histogram_filename(entry.name):
            counts["rejected_histogram_files"] += 1
            log.write(f"REJECT HISTOGRAM: {safe_name(entry.path)}")
            continue

        relative = Path("histogram", entry.name)
        key = relative.as_posix()

        if key in seen_paths:
            counts["duplicate_path_entries"] += 1
            continue

        seen_paths.add(key)
        counts["valid_histogram_files"] += 1

        copy_one(
            Path(entry.path),
            destination / relative,
            key,
            args,
            log,
            counts,
        )


def print_summary(
    counts: Counter,
    data_source: Path,
    histogram_source: Optional[Path],
    destination: Path,
    log: Logger,
) -> None:
    log.write("")
    log.write("=" * 72)
    log.write("RECOVERY SUMMARY")
    log.write("=" * 72)
    log.write(f"Data source:      {data_source}")
    log.write(
        f"Histogram source: {histogram_source if histogram_source else '(not found)'}"
    )
    log.write(f"Destination:      {destination}")
    log.write("")

    order = [
        "valid_data_files",
        "valid_histogram_files",
        "copied",
        "would_copy",
        "existing_same_size",
        "existing_verified",
        "size_mismatches",
        "checksum_mismatches",
        "duplicate_path_entries",
        "rejected_directories",
        "rejected_files",
        "rejected_histogram_files",
        "rejected_entries",
        "scan_errors",
        "entry_errors",
        "source_stat_errors",
        "destination_stat_errors",
        "destination_errors",
        "verify_errors",
        "copy_errors",
    ]

    for key in order:
        if counts[key]:
            log.write(f"{key:28s}: {counts[key]}")

    # Always print the main totals, even if zero.
    log.write("")
    log.write(
        f"Accepted data files:          {counts['valid_data_files']}"
    )
    log.write(
        f"Accepted histogram CSV files: {counts['valid_histogram_files']}"
    )
    log.write(
        f"Duplicate pathname entries:   {counts['duplicate_path_entries']}"
    )
    log.write(
        f"Copy errors:                  {counts['copy_errors']}"
    )


def main() -> int:
    args = parse_args()

    source_arg = args.source.expanduser()
    destination = args.destination.expanduser().resolve()

    try:
        data_source, histogram_source, card_root = determine_source_layout(source_arg)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not data_source.is_dir():
        print(f"ERROR: data directory does not exist: {data_source}", file=sys.stderr)
        return 2

    # Avoid the dangerous case where destination is on/in the source card.
    try:
        destination.relative_to(card_root.resolve())
        print(
            "ERROR: destination appears to be inside the source SD card. "
            "Choose a destination on another filesystem.",
            file=sys.stderr,
        )
        return 2
    except ValueError:
        pass

    if not args.dry_run:
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"ERROR: cannot create destination {destination}: {exc}", file=sys.stderr)
            return 2

    log = Logger(destination / "gecko_recovery.log", args.dry_run)
    counts: Counter = Counter()
    seen_paths: set[str] = set()

    log.write("=" * 72)
    log.write("Gecko / Silicon Graphics SD recovery")
    log.write("=" * 72)
    log.write(f"Card root:        {card_root}")
    log.write(f"Data source:      {data_source}")
    log.write(
        f"Histogram source: {histogram_source if histogram_source else '(not found)'}"
    )
    log.write(f"Destination:      {destination}")
    log.write(f"Station filter:   {args.station or '(all stations)'}")
    log.write(f"Dry run:          {args.dry_run}")
    log.write(f"SHA256 verify:    {args.verify}")
    log.write(f"Overwrite mismatch: {args.overwrite_mismatched}")
    log.write("")

    recover_data_tree(
        data_source,
        destination,
        args,
        log,
        counts,
        seen_paths,
    )

    recover_histograms(
        histogram_source,
        destination,
        args,
        log,
        counts,
        seen_paths,
    )

    print_summary(
        counts,
        data_source,
        histogram_source,
        destination,
        log,
    )

    if (
        counts["copy_errors"]
        or counts["scan_errors"]
        or counts["entry_errors"]
        or counts["source_stat_errors"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
