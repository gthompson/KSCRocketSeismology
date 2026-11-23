#!/usr/bin/env python3
"""
compute_launch_peaks_physical.py

For each rocket launch window in an input CSV, read waveforms from an SDS archive,
preprocess (incl. response removal) using flovopy, compute amp/energy/fft metrics
via EnhancedStream.ampengfft(), and save per-launch outputs:

  - <outdir>/<slug>_<start>.mseed
  - <outdir>/<slug>_<start>.csv           (per-trace metrics; flattened)
  - <outdir>/<slug>_<start>_station.csv   (station-level metrics; if available)
  - optional: <outdir>/<slug>_<start>.pkl

Also writes an index CSV summarizing which launches were processed and where outputs live.

Assumptions:
- Input CSV has at least: window_start, window_end
- Optional metadata columns: slug, name, launch_designator, SLC, success

This script:
- Reads ONCE per launch window (padded), then filters traces by network/station/channel patterns.
- Runs preprocess_stream on padded data.
- Trims to the exact launch window AFTER preprocessing to avoid taper bias.
- Recomputes ampengfft on the trimmed window so metrics reflect the launch window only.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read_inventory
from obspy.core.util.attribdict import AttribDict

from flovopy.sds.sds import SDSobj
from flovopy.enhanced.stream import EnhancedStream
from flovopy.core.preprocess import preprocess_stream
from flovopy.processing.spectrograms import icewebSpectrogram


# -----------------------------
# Logging
# -----------------------------
def log(msg: str, verbose: int = 0, level: int = 1) -> None:
    if verbose >= level:
        print(msg, flush=True)


# -----------------------------
# Utils
# -----------------------------
def parse_utc(s: Optional[str]) -> Optional[pd.Timestamp]:
    if not s:
        return None
    return pd.to_datetime(s, utc=True, errors="coerce")


def window_overlaps(a0: pd.Timestamp, a1: pd.Timestamp, b0: pd.Timestamp, b1: pd.Timestamp) -> bool:
    return (a0 <= b1) and (a1 >= b0)


def match_any(value: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    return any(fnmatch.fnmatch(value, pat) for pat in patterns)


def is_pressure_channel(chan: str) -> bool:
    # Pressure/infrasound: ?D? (second character is 'D')
    return bool(chan) and len(chan) >= 2 and chan[1].upper() == "D"


def safe_slug(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "launch"
    s = s.lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "launch"


# -----------------------------
# Flattening for metrics export
# -----------------------------
def _flatten(obj: Any, prefix: str = "", out: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Recursively flatten dict-like objects (including ObsPy AttribDict) into key/value pairs.

    Examples:
      {"a": {"b": 1}} -> {"a_b": 1}
      AttribDict({"sam": AttribDict({"values": AttribDict({"low": 1})})})
        -> {"sam_values_low": 1}

    Lists/tuples/np arrays are left as-is (stored in CSV as a stringified object by pandas).
    """
    if out is None:
        out = {}

    if obj is None:
        return out

    # Dict-like (AttribDict has .items but isn't a dict subclass)
    if hasattr(obj, "items"):
        for k, v in obj.items():
            key = f"{prefix}{k}" if not prefix else f"{prefix}_{k}"
            if hasattr(v, "items"):
                _flatten(v, key, out)
            else:
                out[key] = v
        return out

    # Non-dict-like
    if prefix:
        out[prefix] = obj
    return out


# -----------------------------
# Save helpers (without requiring you to edit flovopy code right now)
# -----------------------------
def save_enhancedstream_bundle(
    est: EnhancedStream,
    basepath: str,
    *,
    save_pickle: bool = False,
    verbose: int = 0,
) -> Dict[str, str]:
    """
    Save:
      - waveform: basepath.mseed
      - per-trace metrics: basepath.csv     (flattened metrics)
      - station metrics: basepath_station.csv (if available)
      - optional pickle: basepath.pkl

    Returns dict of written paths.
    """
    import pickle

    # strip .mseed if user passed it
    if basepath.endswith(".mseed"):
        basepath = basepath[:-6]

    outdir = os.path.dirname(basepath)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)

    written: Dict[str, str] = {}

    # 1) waveform
    mseed_path = basepath + ".mseed"
    est.write(mseed_path, format="MSEED")
    written["mseed"] = mseed_path

    # 2) per-trace metrics
    trace_rows: List[Dict[str, Any]] = []
    for tr in est:
        s = tr.stats
        row: Dict[str, Any] = {
            "id": tr.id,
            "network": getattr(s, "network", ""),
            "station": getattr(s, "station", ""),
            "location": getattr(s, "location", ""),
            "channel": getattr(s, "channel", ""),
            "starttime": s.starttime,
            "endtime": s.endtime,
            "Fs": getattr(s, "sampling_rate", None),
            "calib": getattr(s, "calib", None),
            "units": getattr(s, "units", None),
            "quality": getattr(s, "quality_factor", None),
            "is_pressure": is_pressure_channel(getattr(s, "channel", "")),
        }

        # spectrum (if present)
        if hasattr(s, "spectrum"):
            row.update(_flatten(s.spectrum, prefix="spectrum"))

        # metrics (flatten deeply, including AttribDict)
        if hasattr(s, "metrics"):
            row.update(_flatten(s.metrics, prefix=""))

        # coordinates (if present)
        if hasattr(s, "coordinates"):
            try:
                row["latitude"] = s.coordinates.latitude
                row["longitude"] = s.coordinates.longitude
                row["elevation"] = s.coordinates.elevation
            except Exception:
                pass

        trace_rows.append(row)

    df_traces = pd.DataFrame(trace_rows)
    csv_path = basepath + ".csv"
    df_traces.to_csv(csv_path, index=False)
    written["trace_csv"] = csv_path

    # 3) station-level metrics (if EnhancedStream provides them)
    station_csv = basepath + "_station.csv"
    wrote_station = False
    try:
        sdf = getattr(est, "station_metrics", None)
        if sdf is None or getattr(sdf, "empty", True):
            # Some flovopy versions compute station metrics lazily
            if hasattr(est, "_station_level_metrics"):
                sdf = est._station_level_metrics()
        if sdf is not None and not getattr(sdf, "empty", True):
            sdf.to_csv(station_csv, index=False)
            wrote_station = True
            written["station_csv"] = station_csv
    except Exception as e:
        log(f"[WARN] station-level CSV not written: {e}", verbose, 1)

    # 4) pickle (optional)
    if save_pickle:
        pkl_path = basepath + ".pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump(est, f)
        written["pickle"] = pkl_path

    log(f"[✓] Saved {len(est)} traces to {mseed_path} and metrics to {csv_path}", verbose, 1)
    if wrote_station:
        log(f"[✓] Station metrics: {station_csv}", verbose, 2)
    return written


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-csv", required=True, help="CSV containing at least window_start/window_end")
    ap.add_argument("--stationxml", required=True)
    ap.add_argument("--sds-root", default="/raid/data/remastered/SDS_KSC")

    ap.add_argument("--outdir", default="event_outputs", help="Directory to save per-launch bundles")
    ap.add_argument("--index-out", default="launch_metrics_index.csv", help="Summary CSV of processed launches")
    ap.add_argument("--save-pickle", action="store_true")

    ap.add_argument("--pad-s", type=float, default=300.0, help="Padding seconds on each side of window for preprocessing")
    ap.add_argument("--taper-pct", type=float, default=0.01, help="If preprocess uses taper, padding helps avoid bias")

    ap.add_argument("--from", dest="date_from", default=None, help="Only launches whose windows overlap this UTC date/time")
    ap.add_argument("--to", dest="date_to", default=None)

    ap.add_argument("--stations", default="", help="Comma-separated station glob patterns, e.g. 'BCHH,JPK*' (optional)")
    ap.add_argument("--channels", default="", help="Comma-separated channel glob patterns, e.g. '??Z,??N,??E,?D?' (optional)")
    ap.add_argument("--networks", default="", help="Comma-separated network glob patterns (optional)")

    ap.add_argument("--max-launches", type=int, default=0, help="Debug: stop after N launches (0=all)")
    ap.add_argument("-v", "--verbose", action="count", default=0)

    # preprocess_stream knobs (kept minimal; you can expand as needed)
    ap.add_argument("--hp", type=float, default=0.1, help="Highpass corner (Hz) for preprocess_stream")
    args = ap.parse_args()

    date_from = parse_utc(args.date_from)
    date_to = parse_utc(args.date_to)
    if (date_from is not None) and (date_to is None):
        date_to = pd.Timestamp.max.tz_localize("UTC")
    if (date_to is not None) and (date_from is None):
        date_from = pd.Timestamp.min.tz_localize("UTC")

    station_pats = [p.strip() for p in args.stations.split(",") if p.strip()]
    chan_pats = [p.strip() for p in args.channels.split(",") if p.strip()]
    net_pats = [p.strip() for p in args.networks.split(",") if p.strip()]

    log(f"Loading CSV: {args.events_csv}", args.verbose, 1)
    df = pd.read_csv(args.events_csv)
    if "window_start" not in df.columns or "window_end" not in df.columns:
        raise ValueError("events CSV must contain window_start and window_end columns")

    df["window_start"] = pd.to_datetime(df["window_start"], utc=True, errors="coerce")
    df["window_end"] = pd.to_datetime(df["window_end"], utc=True, errors="coerce")

    # Filter by date overlap if requested
    if date_from is not None and date_to is not None:
        before = len(df)
        mask = []
        for r in df.itertuples(index=False):
            if pd.isna(r.window_start) or pd.isna(r.window_end):
                mask.append(False)
            else:
                mask.append(window_overlaps(r.window_start, r.window_end, date_from, date_to))
        df = df.loc[mask].copy()
        log(f"Date filter [{date_from} .. {date_to}] kept {len(df)}/{before} launches", args.verbose, 1)

    log(f"Loading StationXML: {args.stationxml}", args.verbose, 1)
    inv = read_inventory(args.stationxml)

    log(f"Opening SDS via SDSobj: {args.sds_root}", args.verbose, 1)
    sdsobject = SDSobj(args.sds_root)

    os.makedirs(args.outdir, exist_ok=True)

    index_rows: List[Dict[str, Any]] = []
    launch_count = 0

    for r in df.itertuples(index=False):
        if pd.isna(r.window_start) or pd.isna(r.window_end):
            continue

        launch_count += 1
        if args.max_launches and launch_count > args.max_launches:
            break

        t0 = UTCDateTime(r.window_start.to_pydatetime())
        t1 = UTCDateTime(r.window_end.to_pydatetime())
        tp0 = t0 - float(args.pad_s)
        tp1 = t1 + float(args.pad_s)

        slug = safe_slug(getattr(r, "slug", "") or getattr(r, "name", "") or f"launch_{launch_count:04d}")
        start_tag = r.window_start.strftime("%Y%m%dT%H%M%SZ")
        eventdir = os.path.join(args.outdir, start_tag)
        os.makedirs(eventdir, exist_ok=True)
        #base = f"{start_tag}_{slug}"
        basepath = os.path.join(eventdir, slug)

        log(f"\nLaunch {launch_count}: {slug}  {r.window_start} -> {r.window_end}", args.verbose, 1)

        # --- Read once per launch window (padded) ---
        try:
            sdsobject.read(tp0, tp1)
            st = sdsobject.stream
        except Exception as e:
            log(f"  READ FAIL: {type(e).__name__}: {e}", args.verbose, 1)
            index_rows.append(dict(
                slug=slug,
                name=getattr(r, "name", ""),
                window_start=str(r.window_start),
                window_end=str(r.window_end),
                status="read_fail",
                error=f"{type(e).__name__}: {e}",
                basepath=basepath,
            ))
            continue

        if not st or len(st) == 0:
            log("  NO DATA (window)", args.verbose, 2)
            index_rows.append(dict(
                slug=slug,
                name=getattr(r, "name", ""),
                window_start=str(r.window_start),
                window_end=str(r.window_end),
                status="no_data",
                error="",
                basepath=basepath,
            ))
            continue

        # --- Filter by network/station/channel after read ---
        try:
            st_filt = []
            for tr in st:
                if not match_any(tr.stats.network, net_pats):
                    continue
                if not match_any(tr.stats.station, station_pats):
                    continue
                if not match_any(tr.stats.channel, chan_pats):
                    continue
                st_filt.append(tr)
            st = st.__class__(st_filt)  # keep Stream type
        except Exception as e:
            log(f"  WARN filtering failed: {e}", args.verbose, 1)

        if not st or len(st) == 0:
            log("  NO DATA after filters", args.verbose, 2)
            index_rows.append(dict(
                slug=slug,
                name=getattr(r, "name", ""),
                window_start=str(r.window_start),
                window_end=str(r.window_end),
                status="no_data_after_filters",
                error="",
                basepath=basepath,
            ))
            continue

        log(f"  Read {len(st)} traces (padded window)", args.verbose, 2)

        # --- Preprocess (response removal, filtering, etc.) on PADDED data ---
        try:
            # NOTE: your preprocess_stream signature might accept freq=0.1 or freq=[0.1]
            # If it expects list, change to freq=[args.hp]
            st_processed = preprocess_stream(
                st,
                freq=args.hp,
                filter_type="highpass",
                inv=inv,
                verbose=args.verbose,
            )
            log("  preprocess_stream succeeded", args.verbose, 2)
        except Exception as e:
            log(f"  preprocess_stream FAILED: {type(e).__name__}: {e}", args.verbose, 1)
            index_rows.append(dict(
                slug=slug,
                name=getattr(r, "name", ""),
                window_start=str(r.window_start),
                window_end=str(r.window_end),
                status="preprocess_fail",
                error=f"{type(e).__name__}: {e}",
                basepath=basepath,
            ))
            continue

        # --- Ensure EnhancedStream ---
        try:
            est = st_processed if isinstance(st_processed, EnhancedStream) else EnhancedStream(st_processed)
        except Exception as e:
            log(f"  EnhancedStream FAILED: {type(e).__name__}: {e}", args.verbose, 1)
            index_rows.append(dict(
                slug=slug,
                name=getattr(r, "name", ""),
                window_start=str(r.window_start),
                window_end=str(r.window_end),
                status="enhancedstream_fail",
                error=f"{type(e).__name__}: {e}",
                basepath=basepath,
            ))
            continue

        # --- Trim to EXACT launch window to avoid taper bias ---
        try:
            est_win = est.copy().trim(t0, t1, pad=False)
        except Exception as e:
            log(f"  WARN trim failed; using untrimmed stream: {e}", args.verbose, 1)
            est_win = est

        # --- Compute metrics on the TRIMMED window ---
        try:
            est_win.ampengfft()
            log("  ampengfft succeeded (trimmed)", args.verbose, 2)
        except Exception as e:
            log(f"  ampengfft FAILED: {type(e).__name__}: {e}", args.verbose, 1)
            index_rows.append(dict(
                slug=slug,
                name=getattr(r, "name", ""),
                window_start=str(r.window_start),
                window_end=str(r.window_end),
                status="ampengfft_fail",
                error=f"{type(e).__name__}: {e}",
                basepath=basepath,
            ))
            continue

        # --- Save bundle (waveforms + flattened metrics CSVs) ---
        try:
            written = save_enhancedstream_bundle(
                est_win,
                basepath,
                save_pickle=args.save_pickle,
                verbose=args.verbose,
            )
            status = "ok"
            error = ""
        except Exception as e:
            written = {}
            status = "save_fail"
            error = f"{type(e).__name__}: {e}"
            log(f"  SAVE FAILED: {error}", args.verbose, 1)

        # --- Add one summary row per launch ---
        index_rows.append(dict(
            slug=slug,
            name=getattr(r, "name", ""),
            launch_designator=getattr(r, "launch_designator", ""),
            slc=getattr(r, "SLC", ""),
            launch_success_flag=getattr(r, "success", ""),
            window_start=str(r.window_start),
            window_end=str(r.window_end),
            pad_s=float(args.pad_s),
            hp_hz=float(args.hp),
            n_traces=int(len(est_win)) if est_win else 0,
            status=status,
            error=error,
            basepath=basepath,
            mseed_path=written.get("mseed", ""),
            trace_csv_path=written.get("trace_csv", ""),
            station_csv_path=written.get("station_csv", ""),
            pickle_path=written.get("pickle", ""),
        ))

        # Cut length for plots - placeholder for detection or real times
        est_win.trim(endtime=t0+900)

        # Make any other plots - and add spectrograms too
        temp_st = est_win.select(component="Z")
        temp_st.select(component="Z").plot(outfile=basepath + "_Z_traces.png", size=(1200, 800))
        spobj_Z = icewebSpectrogram(temp_st)
        spobj_Z.plot(outfile=basepath + "_Z_spectrograms.png")#, size=(1200, 800))

        # Find unique stations in this launch
        stations = set(tr.stats.station for tr in est_win)
        for sta in stations:
            temp_st=est_win.select(station=sta)
            temp_st.plot(outfile=basepath + f"_{sta}_traces.png", size=(1200, 800))
            spobj_sta = icewebSpectrogram(temp_st.select(station=sta))
            spobj_sta.plot(outfile=basepath + f"_{sta}_spectrograms.png")#, size=(1200, 800))

        # plot the first infrasound channel at each station, for all stations in one figure
        infrasound_stream = EnhancedStream()
        for sta in stations:
            p_trs = est_win.select(station=sta).select(channel="*D*")
            if p_trs:
                p_tr = p_trs[0]
                infrasound_stream.append(p_tr)
        if len(infrasound_stream) > 0:
            infrasound_stream.plot(outfile=basepath + f"_P_traces.png", size=(1200, 800))
            spobj_P = icewebSpectrogram(infrasound_stream)
            spobj_P.plot(outfile=basepath + f"_P_spectrograms.png")#, size=(1200, 800))



    # Write index CSV
    out_index = pd.DataFrame(index_rows)
    out_index.to_csv(args.index_out, index=False)
    print(f"\nWrote index: {args.index_out} ({len(out_index):,} launches)")


if __name__ == "__main__":
    main()