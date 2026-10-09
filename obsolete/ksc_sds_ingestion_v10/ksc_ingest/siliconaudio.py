"""Convert SiliconAudio B23-style minute MiniSEED to a *staging* SDS archive.

Input is station/data/MM/DD/HH/*.ms (or data/YYYY/MM/DD/HH/*.ms).
Uses FLOVOpy EnhancedSDSClient.write_stream; the canonical SDS is merged
separately using flovopy.sds.merge_sds_archives.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from obspy import Stream, UTCDateTime, read
from flovopy.enhanced.sdsclient import EnhancedSDSClient


def _numeric_dirs(path):
    return sorted((p for p in path.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name))


def _days(root: Path, year: int | None):
    """Yield (UTC day, directory) for MM/DD or YYYY/MM/DD trees."""
    top = _numeric_dirs(root)
    if not top:
        return
    if all(len(p.name) == 4 for p in top):
        for yr in top:
            for mo in _numeric_dirs(yr):
                for dy in _numeric_dirs(mo):
                    yield datetime(int(yr.name), int(mo.name), int(dy.name), tzinfo=timezone.utc), dy
    else:
        if year is None:
            raise ValueError(f"Year required for MM/DD/HH SiliconAudio directory: {root}")
        for mo in top:
            for dy in _numeric_dirs(mo):
                yield datetime(int(year), int(mo.name), int(dy.name), tzinfo=timezone.utc), dy


def convert_siliconaudio(input_root, sds_root, *, year=None, pattern='*.ms',
                         write_mode='merge', preprocess=False, dry_run=False,
                         verbose=True, strict=True, **write_kwargs):
    """Convert one station's minute files to day-based SDS files.

    This is restartable via EnhancedSDSClient's merge mode, but writing into
    a dedicated staging SDS root is recommended. Existing master files are
    never modified by this function unless explicitly supplied as sds_root.

    Returns a dictionary with day/file counts, errors and written paths.
    """
    source = Path(input_root).expanduser()
    target = Path(sds_root).expanduser()
    if not source.is_dir():
        raise FileNotFoundError(source)
    if source.resolve() == target.resolve() or target.resolve().is_relative_to(source.resolve()):
        raise ValueError('SDS output must not be inside the source directory')
    days = list(_days(source, year))
    if not days:
        raise ValueError(f'No dated subdirectories found under {source}')
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
        client = EnhancedSDSClient(str(target))
    stats = Counter()
    written_paths = []
    errors = []
    for date, day_dir in days:
        files = [f for hour in _numeric_dirs(day_dir) for f in sorted(hour.glob(pattern)) if f.is_file()]
        stats['days_seen'] += 1
        stats['files_found'] += len(files)
        if verbose:
            print(f'{date.date()} | {len(files)} minute files', flush=True)
        if not files:
            continue
        if dry_run:
            stats['days_with_files'] += 1
            continue
        day_stream = Stream()
        day_failed = False
        for f in files:
            if f.stat().st_size == 0:
                stats['empty_files'] += 1
                continue
            try:
                day_stream += read(str(f), format='MSEED')
                stats['files_read'] += 1
            except Exception as exc:
                day_failed = True
                stats['read_errors'] += 1
                errors.append(f'{f}: {exc}')
                if verbose:
                    print(f'  ERROR reading {f}: {exc}', flush=True)
        if not day_stream:
            continue
        # Never publish an incomplete day silently when a minute file failed.
        if day_failed and strict:
            stats['days_skipped'] += 1
            continue
        try:
            day_stream.merge(method=0, fill_value=None)
            # End boundary is inclusive in ObsPy; subtract one sample per trace
            # so samples at midnight belong to the following SDS day.
            start = UTCDateTime(date)
            for tr in day_stream:
                tr.trim(starttime=start, endtime=start + 86400 - tr.stats.delta,
                        nearest_sample=False)
            day_stream = Stream(tr for tr in day_stream if tr.stats.npts)
            if not day_stream:
                continue
            written = client.write_stream(day_stream, mode=write_mode,
                                          preprocess=preprocess, verbose=verbose,
                                          **write_kwargs)
            written_paths.extend(str(p) for p in (written or []))
            stats['days_written'] += 1
            stats['sds_files_reported'] += len(written or [])
        except Exception as exc:
            stats['write_errors'] += 1
            errors.append(f'{date.date()}: {exc}')
            if verbose:
                print(f'  ERROR writing {date.date()}: {exc}', flush=True)
    return {'source': str(source), 'target': str(target), 'dry_run': dry_run,
            **dict(stats), 'errors': errors, 'written': written_paths}
