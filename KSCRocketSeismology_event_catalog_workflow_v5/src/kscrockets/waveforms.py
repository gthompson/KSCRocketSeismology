"""Raw event-window extraction from an SDS archive; no signal processing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

@dataclass(frozen=True)
class ExtractionRequest:
    event_id: str
    start: str
    end: str
    trace_ids: tuple[str, ...]


def select_events(database, event_id=None, start=None, end=None, event_types=None):
    sql = "SELECT * FROM events WHERE 1=1"
    args = []
    if event_id is not None:
        sql += " AND event_id=?"; args.append(event_id)
    if start is not None:
        sql += " AND event_time_utc>=?"; args.append(start)
    if end is not None:
        sql += " AND event_time_utc<=?"; args.append(end)
    if event_types:
        sql += " AND event_type IN (" + ",".join("?" for _ in event_types) + ")"; args.extend(event_types)
    sql += " ORDER BY event_time_utc,event_id"
    with sqlite3.connect(database) as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute(sql,args)]


def event_window(event, pre=30., post=240., use_catalog_window=True):
    from obspy import UTCDateTime
    t = UTCDateTime(event["event_time_utc"])
    a = UTCDateTime(event["window_start"]) if use_catalog_window and event.get("window_start") else t-pre
    b = UTCDateTime(event["window_end"]) if use_catalog_window and event.get("window_end") else t+post
    if b <= a: raise ValueError("Invalid event extraction window")
    return a,b


def discover_channels(client, start, end, cache=None, station=None, skip_low_rate=False):
    """Discover NSLCs on every intersecting UTC day, with optional day cache.

    A file's presence does not imply full event-window coverage.
    """
    from obspy import UTCDateTime
    from datetime import timedelta
    a, b = UTCDateTime(start), UTCDateTime(end)
    if b <= a:
        raise ValueError("Invalid discovery interval")
    cache = {} if cache is None else cache
    day = a.datetime.date()
    last = (b - 0.000001).datetime.date()
    found = set()
    while day <= last:
        key = day.isoformat()
        if key not in cache:
            when = UTCDateTime(key)
            if hasattr(client, "get_nslc_for_day"):
                values = client.get_nslc_for_day(when, skip_low_rate=False)
            else:
                values = client.get_all_nslc(datetime=when)
            cache[key] = tuple(sorted(tuple(x) for x in values))
        found.update(cache[key])
        day += timedelta(days=1)
    if station:
        found = {x for x in found if x[1] == station}
    if skip_low_rate:
        found = {x for x in found if not x[3].startswith("L")}
    return sorted(".".join(x) for x in found)


def _availability(client, parts, start, end):
    try:
        fraction, gaps = client.get_availability_percentage(*parts, start, end)
        fraction = max(0.0, min(1.0, float(fraction)))
        return {"availability_fraction": fraction, "gap_count": int(gaps)}
    except Exception as exc:
        return {"availability_fraction": None, "gap_count": None,
                "availability_error": f"{type(exc).__name__}: {exc}"}


def extract_event(event, client, output_root, trace_ids=None, pre=30., post=240.,
                  overwrite=False, dry_run=False, use_catalog_window=True,
                  discovery_cache=None, station=None, skip_low_rate=False,
                  check_availability=True, retry_missing=False):
    """Extract unchanged SDS samples; optionally discover all channels.

    No detrending, filtering, response removal or gap filling is performed.
    A report records per-channel availability separately from file discovery.
    """
    from obspy import Stream
    start, end = event_window(event, pre, post, use_catalog_window)
    event_id = str(event["event_id"])
    ids = tuple(sorted(set(trace_ids if trace_ids is not None else
        discover_channels(client, start, end, cache=discovery_cache,
                          station=station, skip_low_rate=skip_low_rate))))
    for tid in ids:
        if len(tid.split(".")) != 4:
            raise ValueError(f"Invalid SEED ID: {tid}")
    spec = {"event_id": event_id, "start": str(start), "end": str(end),
            "trace_ids": ids,
            "sds_root": str(getattr(client, "sds_root_path",
                                    getattr(client, "sds_root", "unknown")))}
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]
    directory = Path(output_root) / event_id / key
    waveform = directory / "raw.mseed"
    manifest = directory / "extraction.json"
    result = {**spec, "request_id": key, "waveform": str(waveform),
              "status": "planned", "discovery_mode": "automatic" if trace_ids is None else "explicit"}
    if dry_run:
        return result
    if manifest.exists() and not overwrite:
        try:
            previous = json.loads(manifest.read_text())
            old = previous.get("status")
            if old in ("complete", "partial", "missing") and not (retry_missing and old == "missing"):
                if old == "missing" or (waveform.is_file() and waveform.stat().st_size > 0):
                    return {**previous, "status": "skipped", "previous_status": old}
        except (OSError, ValueError):
            pass
    stream = Stream()
    errors = {}
    found = []
    channels = {}
    for tid in ids:
        parts = tid.split(".")
        entry = _availability(client, parts, start, end) if check_availability else {}
        try:
            st = client.get_waveforms(*parts, start, end, merge=-1)
            stream += st
            if st:
                found.append(tid)
            entry["n_segments"] = len(st)
            entry["n_samples"] = sum(int(tr.stats.npts) for tr in st)
            entry["sampling_rates"] = sorted({float(tr.stats.sampling_rate) for tr in st})
        except Exception as exc:
            errors[tid] = f"{type(exc).__name__}: {exc}"
            entry["read_error"] = errors[tid]
        channels[tid] = entry
    result.update(found_ids=found, missing_ids=sorted(set(ids) - set(found)),
                  errors=errors, channels=channels, n_traces=len(stream),
                  segments=[{"id": tr.id, "start": str(tr.stats.starttime),
                             "end": str(tr.stats.endtime), "npts": int(tr.stats.npts),
                             "sampling_rate": float(tr.stats.sampling_rate)} for tr in stream],
                  created_utc=datetime.now(timezone.utc).isoformat())
    partial_coverage = any(ch.get("availability_fraction") is not None and
                           ch["availability_fraction"] < 0.9999 for ch in channels.values())
    result["status"] = ("error" if errors and not stream else
                        "missing" if not stream else
                        "partial" if errors or len(found) != len(ids) or partial_coverage else "complete")
    directory.mkdir(parents=True, exist_ok=True)
    if stream:
        stream.write(str(waveform), format="MSEED")
    else:
        result["waveform"] = None
        if waveform.exists():
            waveform.unlink()
    tmp = manifest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, indent=2, default=str) + "\n")
    tmp.replace(manifest)
    return result


def extract_catalog(database, client, output_root, trace_ids=None, event_id=None,
                    start=None, end=None, event_types=None, **kwargs):
    cache = {}
    for event in select_events(database, event_id, start, end, event_types):
        yield extract_event(event, client, output_root, trace_ids,
                            discovery_cache=cache, **kwargs)
