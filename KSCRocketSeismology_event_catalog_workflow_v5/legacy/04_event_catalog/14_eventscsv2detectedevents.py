#!/usr/bin/env python3
"""
Detect launches (and optional sonic booms) directly from SDS windows listed in a CSV.

- Reads each row's time window from the CSV
- Pulls the waveform from SDS with a chosen preset (raw_preset | archive_preset | analysis_preset)
- Runs detect_network_event() for LAUNCH
- Optionally runs SONIC in a delayed window after each launch (SpaceX-only if desired)
- Writes ONE MiniSEED per detected event (whole Stream snippet) via write_wavfile()
- Saves a detections CSV

Example:
  python detect_from_csv_sds.py \
    --csv all_florida_launches.csv \
    --sds-root /data/remastered/SDS_KSC \
    --det-csv /data/KSC/detections_from_sds.csv \
    --mseed-dir /data/KSC/event_snippets \
    --preset analysis_preset \
    --minchans 3 \
    --detect-launch \
    --enable-sonic-after-launch --sonic-only-spacex
"""

import os
import argparse
import warnings
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from obspy import UTCDateTime, Stream, read_inventory

from flovopy.sds.sds2event import load_event_stream_from_sds  # read from SDS with preset
from flovopy.seisanio.utils.helpers import write_wavfile      # write 1 MiniSEED per event Stream
from flovopy.processing.detection import detect_network_event # your network detector


# ------------------------------ small helpers ------------------------------

def _to_utc_any(val) -> UTCDateTime:
    """Epoch/ISO/ISOZ -> UTCDateTime (robust)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        raise ValueError("Missing time value")
    s = str(val).strip()
    # Pandas handles most formats; fall back to ObsPy as needed
    ts = pd.to_datetime(s.replace("Z", "+00:00"), utc=True, errors="coerce")
    return UTCDateTime(ts.to_pydatetime()) if not pd.isna(ts) else UTCDateTime(s)

def _looks_like_spacex(row: pd.Series) -> bool:
    keys = ("rocket", "mission", "provider", "launch_provider")
    text = " ".join(str(row.get(k, "")).lower() for k in keys)
    return ("spacex" in text) or ("falcon" in text) or ("starship" in text)

def _write_event_stream(
    st_full: Stream,
    t_on: UTCDateTime,
    t_off: UTCDateTime,
    out_root: str,
    *,
    pre_pad: float = 10.0,
    post_pad: float = 10.0,
    dbstring: str = "DET",
    plot: bool = True,
) -> str:
    """
    Trim WHOLE stream to [t_on-pre_pad, t_off+post_pad] and write ONE MiniSEED via write_wavfile().
    write_wavfile() creates <out_root>/<YYYY>/<MM>/YYYY-MM-DD-HHMM-SSS.DBSTRING_NUMCHANS
    """
    t1 = t_on - pre_pad
    t2 = t_off + post_pad
    st_cut = st_full.copy().trim(t1, t2, pad=False)
    if len(st_cut) == 0:
        raise RuntimeError("Empty stream after trim")
    wavpath = write_wavfile(st_cut, out_root, dbstring, numchans=len(st_cut), year_month_dirs=True, fmt="MSEED")
    if plot:
        pngpath = wavpath + '.png'
        st_cut.plot(equal_scale=False, outfile=pngpath);
    return wavpath


def _detect_events(
    st: Stream,
    *,
    band: Tuple[float, float],
    sta: float, lta: float,
    on: float, off: float,
    minchans: int,
    join_within: float,
    min_duration: float,
    max_duration: Optional[float] = None,
    algorithm: str = "recstalta",
    criterion: str = "longest",
) -> List[Dict[str, Any]]:
    """
    Thin wrapper that calls detect_network_event() once and normalizes output.
    Returns list of {t_on, t_off, meta}.
    """
    trig, ontimes, offtimes = detect_network_event(
        st_in=st,
        minchans=minchans,
        threshon=on, threshoff=off,
        sta=sta, lta=lta,
        pad=0.0,
        best_only=False,
        verbose=False,
        freq=[band[0], band[1]],
        algorithm=algorithm,
        criterion=criterion,
        join_within=join_within,
        min_duration=min_duration,
    )
    events: List[Dict[str, Any]] = []
    if trig and ontimes and offtimes:
        for ev, t_on, t_off in zip(trig, ontimes, offtimes):
            dur = float(t_off - t_on)
            if (max_duration is not None) and (dur > max_duration):
                continue
            events.append({"t_on": t_on, "t_off": t_off, "meta": ev})
        events.sort(key=lambda r: r["t_on"])
    return events


# ------------------------------ CLI / main ------------------------------

def main():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # CSV + SDS
    ap.add_argument("--csv", required=True, help="CSV with event windows + metadata")
    ap.add_argument("--sds-root", required=True, help="SDS root directory")
    ap.add_argument("--start-col", default="window_start")
    ap.add_argument("--end-col",   default="window_end")

    # SDS selectors + loading preset
    ap.add_argument("--net", default="*")
    ap.add_argument("--sta", default="*")
    ap.add_argument("--loc", default="*")
    ap.add_argument("--cha", default="*")
    ap.add_argument("--preset", choices=["raw_preset","archive_preset","analysis_preset"], default="analysis_preset", help="How to normalize data when reading from SDS")
    ap.add_argument("--prepad", type=float, default=-999, help="Seconds before launch window or network trigger ON to include in segmented waveform file")
    ap.add_argument("--postpad", type=float, default=-999, help="Seconds after launch window or network trigger OFF to include in segmented waveform file")
    ap.add_argument("--stationxml", action="append", default=None, help="Path to StationXML file(s). Repeat flag to provide multiple.")
    # (optional) if you want to choose output units after response removal
    ap.add_argument("--resp-output", choices=["VEL", "DISP", "ACC", "DEF"], default="DEF", help="Target unit for response removal in analysis_preset.")

    # Outputs
    ap.add_argument("--det-csv", required=True, help="CSV for detections")
    ap.add_argument("--mseed-dir", required=True, help="Directory for event MiniSEED snippets")

    # Detection control
    ap.add_argument("--minchans", type=int, default=3)
    ap.add_argument("--detect-launch", action="store_true", help="Run LAUNCH detection")
    ap.add_argument("--enable-sonic-after-launch", action="store_true", help="Run SONIC in a delayed window after each launch")
    ap.add_argument("--sonic-only-spacex", action="store_true", help="Run SONIC only for rows that look like SpaceX launches")

    # LAUNCH params (minutes-long, emergent)
    ap.add_argument("--launch-band", type=float, nargs=2, default=[0.5, 12.0])
    ap.add_argument("--launch-sta", type=float, default=5.0)
    ap.add_argument("--launch-lta", type=float, default=60.0)
    ap.add_argument("--launch-on",  type=float, default=3.5)
    ap.add_argument("--launch-off", type=float, default=1.2)
    ap.add_argument("--launch-join", type=float, default=-999, help="Merge detections whose gaps ≤ this (s)")
    ap.add_argument("--launch-dur-min", type=float, default=-999)
    ap.add_argument("--launch-dur-max", type=float, default=300)

    # SONIC params (short, impulsive, minutes after)
    ap.add_argument("--sonic-band", type=float, nargs=2, default=[0.5, 20.0])
    ap.add_argument("--sonic-sta", type=float, default=0.25)
    ap.add_argument("--sonic-lta", type=float, default=5.0)
    ap.add_argument("--sonic-on",  type=float, default=6.0)
    ap.add_argument("--sonic-off", type=float, default=2.5)
    ap.add_argument("--sonic-join", type=float, default=-999, help="Tiny merge for very close impulses (s)")
    ap.add_argument("--sonic-dur-min", type=float, default=-999)
    ap.add_argument("--sonic-dur-max", type=float, default=10)
    ap.add_argument("--sonic-delay-min", type=float, default=300.0, help="Seconds after launch onset to start SONIC search")
    ap.add_argument("--sonic-delay-max", type=float, default=900.0, help="Seconds after launch onset to end SONIC search")
    try:
        args = ap.parse_args()
    except:
        import sys
        for a in sys.argv:
            print(f'{type(a).__name__}:{a}')
    if args.prepad < 0:
        args.prepad = args.launch_lta
    if args.postpad < 0:
        args.postpad = args.prepad
    if args.launch_dur_min < 0:
        args.launch_dur_min = args.launch_lta
    if args.sonic_dur_min < 0:
        args.sonic_dur_min = args.sonic_lta
    if args.launch_join < 0:
        args.launch_join = args.launch_lta     
    if args.sonic_join < 0:
        args.sonic_join = args.sonic_lta     
    
    

    inv = None
    if args.stationxml:
        for p in args.stationxml:
            try:
                this_inv = read_inventory(p)
                inv = this_inv if inv is None else (inv + this_inv)
            except Exception as e:
                warnings.warn(f"Failed to read StationXML '{p}': {e}")

    os.makedirs(os.path.dirname(args.det_csv), exist_ok=True)
    os.makedirs(args.mseed_dir, exist_ok=True)

    df = pd.read_csv(args.csv)
    det_rows: List[Dict[str, Any]] = []

    for i, row in df.iterrows():
        # --- derive window to read from SDS ---
        try:
            t_start = _to_utc_any(row[args.start_col])
        except Exception as e:
            warnings.warn(f"[row {i}] bad {args.start_col}: {e}")
            continue

        if args.end_col in df.columns and pd.notna(row[args.end_col]):
            try:
                t_end = _to_utc_any(row[args.end_col])
            except Exception:
                t_end = t_start
        else:
            t_end = t_start

        t1 = t_start - float(args.prepad)
        t2 = t_end   + float(args.postpad)
        print('\n\n\n')
        print(f'Reading SDS from {t1} to {t2}')

        # --- read from SDS once for this window ---
        st = load_event_stream_from_sds(
            sds_root=args.sds_root,
            t1=t1, t2=t2,
            net=args.net, sta=args.sta, loc=args.loc, cha=args.cha,
            preset=args.preset, inv=inv,
            verbose=False,
        )
        if len(st) == 0:
            continue

        print(f'\nReturned from loader after processing:\n{st}')

        # --- LAUNCH detection (optional) ---
        if args.detect_launch:
            launch_events = _detect_events(
                st,
                band=tuple(args.launch_band),
                sta=args.launch_sta, lta=args.launch_lta,
                on=args.launch_on, off=args.launch_off,
                minchans=max(args.minchans, 3),
                join_within=args.launch_join,
                min_duration=args.launch_dur_min,
                max_duration=args.launch_dur_max,
                algorithm="recstalta",
                criterion="longest",
            )
            print(f'\nlaunch events:\n{launch_events}')

            for k, ev in enumerate(launch_events, 1):
                # write one stream snippet per event
                try:
                    out_path = _write_event_stream(
                        st, ev["t_on"], ev["t_off"],
                        out_root=args.mseed_dir,
                        pre_pad=args.prepad,
                        post_pad=args.postpad,
                        dbstring="LAUNCH",
                    )
                except Exception as e:
                    warnings.warn(f"[row {i}] write LAUNCH failed: {e}")
                    continue

                det_rows.append({
                    "row_index": i,
                    "phase": "launch",
                    "event_idx": k,
                    "window_start": str(t_start),
                    "window_end":   str(t_end),
                    "onset_utc":    str(ev["t_on"]),
                    "offset_utc":   str(ev["t_off"]),
                    "duration_s":   float(ev["t_off"] - ev["t_on"]),
                    "coincidence_sum": ev["meta"].get("coincidence_sum"),
                    "out_mseed": out_path,
                })

                # --- SONIC-after-launch (optional) ---
                if args.enable_sonic_after_launch:
                    if args.sonic_only_spacex and not _looks_like_spacex(row):
                        continue
                    s1 = ev["t_on"] + float(args.sonic_delay_min)
                    s2 = ev["t_on"] + float(args.sonic_delay_max)
                    st_delay = st.copy().trim(s1, s2, pad=False)
                    if len(st_delay) == 0:
                        continue

                    sonic_events = _detect_events(
                        st_delay,
                        band=tuple(args.sonic_band),
                        sta=args.sonic_sta, lta=args.sonic_lta,
                        on=args.sonic_on, off=args.sonic_off,
                        minchans=max(args.minchans, 2),
                        join_within=args.sonic_join,
                        min_duration=args.sonic_dur_min,
                        max_duration=args.sonic_dur_max,
                        algorithm="recstalta",
                        criterion="longest",
                    )

                    for j, sev in enumerate(sonic_events, 1):
                        try:
                            outp = _write_event_stream(
                                st, sev["t_on"], sev["t_off"],
                                out_root=args.mseed_dir,
                                pre_pad=args.prepad,
                                post_pad=args.postpad,
                                dbstring="SONIC",
                            )
                        except Exception as e:
                            warnings.warn(f"[row {i}] write SONIC failed: {e}")
                            continue

                        det_rows.append({
                            "row_index": i,
                            "phase": "sonic",
                            "event_idx": j,
                            "window_start": str(t_start),
                            "window_end":   str(t_end),
                            "onset_utc":    str(sev["t_on"]),
                            "offset_utc":   str(sev["t_off"]),
                            "duration_s":   float(sev["t_off"] - sev["t_on"]),
                            "coincidence_sum": sev["meta"].get("coincidence_sum"),
                            "out_mseed": outp,
                        })
        #input('<ENTER> to continue')
        print('')

    # --- write detections table ---
    pd.DataFrame(det_rows).to_csv(args.det_csv, index=False)
    print(f"✅ Wrote {len(det_rows)} detections → {args.det_csv}")
    print(f"📁 Event MiniSEED segments in: {args.mseed_dir} (organized by YYYY/MM)")

if __name__ == "__main__":
    import sys
    import platform
    # === Define metadata paths ===
    home = os.path.expanduser("~")
    system = platform.system()
    repodir = os.path.dirname(os.path.dirname(__file__))
    csvfile = os.path.join(os.path.dirname(__file__), "all_florida_launches.csv")
    # Use Dropbox path on macOS; otherwise default to /data
    metadata_dir = (
        os.path.join(home, "Dropbox", "DATA", "station_metadata")
    )
    os.makedirs(metadata_dir, exist_ok=True)

    # Define all relevant paths
    xmlfile = os.path.join(metadata_dir, "KSC3.xml")
    if len(sys.argv) == 1:
        # sensible defaults for quick run
        sys.argv += [
            "--csv", csvfile,
            "--sds-root", "/data/remastered/SDS_KSC",
            "--det-csv", "/data/KSC/launch_events/detections_from_sds.csv",
            "--mseed-dir", "/data/KSC/launch_events",
            "--preset", "analysis_preset",
            "--stationxml", xmlfile,
            "--minchans", "3",
            "--detect-launch",
            #"--prepad", 60,
            #"--postpad", 60,
            # "--enable-sonic-after-launch", "--sonic-only-spacex",
        ]
    main()