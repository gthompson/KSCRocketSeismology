#!/usr/bin/env python3
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd

from obspy import UTCDateTime, read_inventory
from obspy.clients.filesystem.sds import Client as SDSClient


# -----------------------------
# Channel typing
# -----------------------------
def is_pressure_channel(chan: str) -> bool:
    # Pressure/infrasound: ?D? (second character is 'D')
    return bool(chan) and len(chan) >= 2 and chan[1].upper() == "D"


def parse_seed_ids(val) -> list[str]:
    if pd.isna(val):
        return []
    return [s.strip() for s in str(val).split(",") if s.strip()]


# -----------------------------
# Signal helpers
# -----------------------------
def peak_abs(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(np.max(np.abs(x))) if x.size else np.nan


def robust_metrics(x: np.ndarray) -> dict:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return dict(npts=0, peak_abs=np.nan, p2p=np.nan, rms=np.nan, mad=np.nan)
    peak = float(np.max(np.abs(x)))
    p2p = float(np.max(x) - np.min(x))
    rms = float(np.sqrt(np.mean(x**2)))
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)))
    return dict(npts=int(x.size), peak_abs=peak, p2p=p2p, rms=rms, mad=mad)


def choose_prefilt(sr: float) -> tuple[float, float, float, float]:
    """
    Generic pre_filt for remove_response.
    You can tune later; this is a safe-ish default to start.
    """
    nyq = 0.5 * sr
    f1, f2 = 0.02, 0.05
    f4 = min(0.90 * nyq, 50.0)         # keep well below Nyquist
    f3 = min(0.70 * nyq, 25.0)
    # ensure ordering
    if f3 <= f2:
        f3 = min(0.50 * nyq, max(f2 * 2, f2 + 0.1))
    if f4 <= f3:
        f4 = min(0.90 * nyq, f3 * 1.5)
    return (f1, f2, f3, f4)


def compute_peaks_for_trace(tr, inv, t0, t1, pad: float, water_level: float, taper_pct: float) -> dict:
    """
    tr is a Trace already spanning [t0-pad, t1+pad] (padded window).
    We taper & remove response on padded data, then trim to [t0, t1] and compute peaks.
    """
    out = {
        "pgv_mps": np.nan,
        "pga_mps2": np.nan,
        "peak_dp_phys": np.nan,   # typically Pa if response is defined that way
        "dp_units": "",           # filled if we can infer via response
    }

    # Work on a padded copy (so no taper touches the actual launch window after trimming)
    tr0 = tr.copy()
    tr0.detrend("linear")
    tr0.detrend("demean")
    if taper_pct and taper_pct > 0:
        tr0.taper(max_percentage=taper_pct, type="cosine")

    sr = float(tr0.stats.sampling_rate)
    pre_filt = choose_prefilt(sr)

    chan = tr0.stats.channel

    # Try to record expected output units (helps sanity-check)
    try:
        resp = inv.get_response(tr0.id, tr0.stats.starttime)
        out_units = getattr(resp.instrument_sensitivity, "output_units", "") or ""
        out["dp_units"] = out_units
    except Exception:
        pass

    if is_pressure_channel(chan):
        trp = tr0.copy()
        trp.remove_response(inventory=inv, output="DEF", pre_filt=pre_filt, water_level=water_level)
        trp.trim(t0, t1, pad=False)
        out["peak_dp_phys"] = peak_abs(trp.data.astype(np.float64))
    else:
        # PGV
        trv = tr0.copy()
        trv.remove_response(inventory=inv, output="VEL", pre_filt=pre_filt, water_level=water_level)
        trv.trim(t0, t1, pad=False)
        out["pgv_mps"] = peak_abs(trv.data.astype(np.float64))

        # PGA
        tra = tr0.copy()
        tra.remove_response(inventory=inv, output="ACC", pre_filt=pre_filt, water_level=water_level)
        tra.trim(t0, t1, pad=False)
        out["pga_mps2"] = peak_abs(tra.data.astype(np.float64))

    return out


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-csv", required=True)
    ap.add_argument("--stationxml", required=True)
    ap.add_argument("--sds-root", default="/raid/data/remastered/SDS_KSC")
    ap.add_argument("--out", default="launch_peaks_physical.csv")
    ap.add_argument("--pad-s", type=float, default=120.0, help="Pad seconds on each side of launch window")
    ap.add_argument("--water-level", type=float, default=60.0)
    ap.add_argument("--taper-pct", type=float, default=0.01, help="Taper fraction applied to padded traces only")
    args = ap.parse_args()

    df = pd.read_csv(args.events_csv)

    # Ensure expected column names (your CSV has window_start/window_end/SEED_ids)
    df["window_start"] = pd.to_datetime(df["window_start"], utc=True, errors="coerce")
    df["window_end"]   = pd.to_datetime(df["window_end"],   utc=True, errors="coerce")

    inv = read_inventory(args.stationxml)
    client = SDSClient(args.sds_root)

    rows = []
    for r in df.itertuples(index=False):
        if pd.isna(r.window_start) or pd.isna(r.window_end):
            continue

        t0 = UTCDateTime(r.window_start.to_pydatetime())
        t1 = UTCDateTime(r.window_end.to_pydatetime())

        seed_ids = parse_seed_ids(r.SEED_ids)
        if not seed_ids:
            continue

        for tid in seed_ids:
            try:
                net, sta, loc, cha = tid.split(".")
            except ValueError:
                rows.append(dict(slug=r.slug, name=r.name, trace_id=tid, error="bad_trace_id"))
                continue

            # Read padded window
            tp0 = t0 - args.pad_s
            tp1 = t1 + args.pad_s

            try:
                st = client.get_waveforms(net, sta, loc, cha, tp0, tp1, merge=-1)
            except Exception as e:
                rows.append(dict(slug=r.slug, name=r.name, trace_id=tid, error=f"read_fail:{type(e).__name__}"))
                continue

            if not st:
                rows.append(dict(slug=r.slug, name=r.name, trace_id=tid, error="no_data"))
                continue

            # Merge gaps before processing
            try:
                st.merge(method=1, fill_value="interpolate")
            except Exception:
                pass

            # Usually should be one trace per id; if not, compute per-trace then take max peak
            pgv_vals, pga_vals, dp_vals = [], [], []
            dp_units = ""

            for tr in st:
                try:
                    peaks = compute_peaks_for_trace(
                        tr=tr,
                        inv=inv,
                        t0=t0,
                        t1=t1,
                        pad=args.pad_s,
                        water_level=args.water_level,
                        taper_pct=args.taper_pct,
                    )
                    if peaks.get("dp_units"):
                        dp_units = peaks["dp_units"]
                    if np.isfinite(peaks["pgv_mps"]):
                        pgv_vals.append(peaks["pgv_mps"])
                    if np.isfinite(peaks["pga_mps2"]):
                        pga_vals.append(peaks["pga_mps2"])
                    if np.isfinite(peaks["peak_dp_phys"]):
                        dp_vals.append(peaks["peak_dp_phys"])
                except Exception as e:
                    rows.append(dict(slug=r.slug, name=r.name, trace_id=tid, error=f"proc_fail:{type(e).__name__}"))
                    continue

            row = dict(
                slug=r.slug,
                name=r.name,
                launch_designator=getattr(r, "launch_designator", ""),
                slc=getattr(r, "SLC", ""),
                success=getattr(r, "success", ""),
                trace_id=tid,
                channel=cha,
                is_pressure=is_pressure_channel(cha),
                window_start=str(r.window_start),
                window_end=str(r.window_end),
                pad_s=args.pad_s,
                pgv_mps=float(np.max(pgv_vals)) if pgv_vals else np.nan,
                pga_mps2=float(np.max(pga_vals)) if pga_vals else np.nan,
                peak_dp_phys=float(np.max(dp_vals)) if dp_vals else np.nan,
                dp_units=dp_units,
                error="",
            )
            rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False)
    print(f"Wrote {args.out} ({len(out):,} rows)")


if __name__ == "__main__":
    main()