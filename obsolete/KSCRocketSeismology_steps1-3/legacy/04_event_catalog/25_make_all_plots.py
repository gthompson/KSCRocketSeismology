#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Regenerate updated CSV and plots for KSC launch analysis:

- Updates vehicle classification, filters non-KSC vehicles (Electron),
  and fixes SLC for Astra (LC-46) and Vulcan (SLC-41).
- (Optional) Re-scan SDS to refresh sds_* columns.
- Rewrites the enriched CSV in place.
- Rebuilds ALL plots:
  1) cumulative launches by SLC (small groups -> "Other SLC")
  2) cumulative windows vs SDS-present vs detected
  3) cumulative launches by vehicle (small groups -> "Other vehicle")
  4) scatter: sds_n_stations
  5) scatter: sds_n_seis_ch
  6) scatter: sds_n_inf_ch
"""

import os
import re
import warnings
from typing import List, Set, Tuple, Optional

import pandas as pd
import matplotlib.pyplot as plt
from obspy import UTCDateTime

# ========================= paths & settings (hard-wired) =========================
EVENTDIR        = "/data/KSC/launch_events"
CSVFILE         = os.path.join(EVENTDIR, "all_florida_launches_with_data.csv")  # INPUT & OUTPUT
DETECTIONS_CSV  = os.path.join(EVENTDIR, "detections_from_sds.csv")
SDS_ROOT        = "/data/remastered/SDS_KSC"

# plots
OUT_CUM_SLC     = os.path.join(EVENTDIR, "cumulative_launches_by_slc.png")
OUT_WIN_SDS_DET = os.path.join(EVENTDIR, "cumulative_windows_vs_sds_vs_detected.png")
OUT_CUM_VEH     = os.path.join(EVENTDIR, "cumulative_launches_by_vehicle.png")
OUT_UNKNOWN_CSV = os.path.join(EVENTDIR, "unknown_vehicle_rows.csv")
OUT_COUNTS_VEH  = os.path.join(EVENTDIR, "vehicle_counts.csv")
OUT_STATIONS    = os.path.join(EVENTDIR, "sds_n_stations_scatter.png")
OUT_SEIS        = os.path.join(EVENTDIR, "sds_n_seis_ch_scatter.png")
OUT_INF         = os.path.join(EVENTDIR, "sds_n_inf_ch_scatter.png")

# columns
DATECOL   = "window_start"
ENDCOL    = "window_end"
SLCCOL    = "SLC"
NAMECOL   = "name"

# shading
NO_NETWORK_RANGES = [
    ("2016-10-07", "2017-08-17"),
    ("2022-12-03", None),  # open-ended
]

# grouping thresholds
MIN_SLC_COUNT  = 5
MIN_VEH_COUNT  = 5

# SDS scan toggle (keep False for speed; True to refresh sds_* columns from filesystem)
RESCAN_SDS = False
PREPAD = 60.0
POSTPAD = 60.0

# detections
DETECT_PHASE = "launch"

# ========================= fast SDS helpers (optional) =========================
FAST_SDS_AVAILABLE = True
try:
    from flovopy.sds.sds import SDSobj  # provides _get_nonempty_traceids()
except Exception:
    FAST_SDS_AVAILABLE = False
    from obspy.clients.filesystem.sds import Client as SDSClient  # fallback

def to_utc_any(val) -> UTCDateTime:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        raise ValueError("Missing time value")
    s = str(val).strip()
    ts = pd.to_datetime(s.replace("Z", "+00:00"), utc=True, errors="coerce")
    return UTCDateTime(ts.to_pydatetime()) if not pd.isna(ts) else UTCDateTime(s)

def day_floor_utc(t: UTCDateTime) -> UTCDateTime:
    dt = pd.Timestamp(t.datetime, tz="UTC").normalize()
    return UTCDateTime(dt.to_pydatetime())

def day_ceil_utc(t: UTCDateTime) -> UTCDateTime:
    dt = (pd.Timestamp(t.datetime, tz="UTC").normalize() + pd.Timedelta(days=1))
    return UTCDateTime(dt.to_pydatetime())

def get_trace_ids_for_window_fast(sds_root: str, t1: UTCDateTime, t2: UTCDateTime) -> List[str]:
    sds = SDSobj(sds_root)
    d1 = day_floor_utc(t1)
    d2 = day_ceil_utc(t2)
    return sds._get_nonempty_traceids(d1, d2, skip_low_rate_channels=True, speed=1)

def get_trace_ids_for_window_fallback(sds_root: str, t1: UTCDateTime, t2: UTCDateTime) -> List[str]:
    from obspy.clients.filesystem.sds import Client as _Client
    ids: Set[str] = set()
    cli = _Client(sds_root)
    thisday = day_floor_utc(t1)
    endday  = day_ceil_utc(t2)
    while thisday < endday:
        try:
            try:
                nslc_list = cli.get_all_nslc(sds_type='D', datetime=thisday)
            except TypeError:
                nslc_list = cli.get_all_nslc(sds_type='D', datetime=thisday.datetime)
        except Exception:
            nslc_list = []
        for net, sta, loc, chan in nslc_list:
            if isinstance(chan, str) and chan.startswith("L"):
                continue
            ids.add(f"{net}.{sta}.{loc}.{chan}")
        thisday += 86400
    return sorted(ids)

def harvest_counts_from_ids(ids: List[str]) -> Tuple[int, int, int]:
    stations: Set[str] = set()
    n_seis = 0
    n_inf = 0
    for tid in ids:
        parts = tid.split(".")
        if len(parts) < 4:
            continue
        net, sta, loc, cha = parts[-4], parts[-3], parts[-2], parts[-1]
        stations.add(f"{net}.{sta}")
        if len(cha) >= 2:
            if cha[1].upper() == "H":
                n_seis += 1
            elif cha[1].upper() == "D":
                n_inf += 1
    return len(stations), n_seis, n_inf

# ========================= vehicle & SLC normalization =========================
VEHICLE_PATTERNS = [
    (r"\bfalcon\s+heavy\b",        "Falcon Heavy"),
    (r"\bfalcon\s+9\b",            "Falcon 9"),
    (r"\bdelta\s+iv\s+heavy\b",    "Delta IV Heavy"),
    (r"\bdelta\s+iv\s+m\+",      "Delta IV M+"),
    (r"\batlas\s+v\b",             "Atlas V"),
    (r"\bvulcan\b",                "Vulcan"),
    (r"\bpegasus\b",               "Pegasus"),
    (r"\bnew\s+glenn\b",           "New Glenn"),
    (r"\bminotaur\b",              "Minotaur"),
    (r"\belectron\b",              "Electron"),
    (r"\bastra\b",                 "Astra"),
    (r"\bsls\b",                   "SLS"),
    (r"\bterran\b",                "Terran"),
    (r"\borion\b",                 "Orion"),
]
UNKNOWN_LABEL = "Unknown vehicle"
OTHER_SLC    = "Other SLC"
OTHER_VEH    = "Other vehicle"

def normalize_name(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.lower()
    s = re.sub(r"\([^)]*\)", " ", s)  # remove contents in parentheses
    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def classify_vehicle(raw_name: str) -> str:
    s = normalize_name(raw_name)
    if not s:
        return UNKNOWN_LABEL
    for pat, label in VEHICLE_PATTERNS:
        if re.search(pat, s):
            return label
    return UNKNOWN_LABEL

def normalize_slc(s: str) -> Optional[str]:
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip().upper().replace(" ", "")
    # unify separators
    t = t.replace("LC-", "LC-").replace("SLC-", "SLC-")
    # keep common forms as-is (e.g., LC-39A, SLC-40, SLC-41, LC-46)
    return t

def fix_slc_by_vehicle(slc_norm: Optional[str], vehicle: str) -> Optional[str]:
    """Correct obvious mismatches where vehicle implies a specific pad family."""
    if vehicle == "Astra":
        return "LC-46"   # Astra launches from LC-46 (CCSFS)
    if vehicle == "Vulcan":
        return "SLC-41"  # Vulcan from SLC-41
    # else leave as provided/normalized
    return slc_norm

# ========================= shading helper =========================
def shade_no_network(ax, x_max_ts):
    for start_s, end_s in NO_NETWORK_RANGES:
        start = pd.Timestamp(start_s, tz="UTC")
        end = (pd.Timestamp(end_s, tz="UTC") + pd.Timedelta(days=1)) if end_s else x_max_ts
        if end > start:
            ax.axvspan(start, end, alpha=0.12, zorder=0)

# ========================= plotting helpers =========================
def plot_cumulative_by_slc(df, out_png: str):
    totals = df.groupby("slc_fixed").size()
    small = set(totals[totals < MIN_SLC_COUNT].index)
    df2 = df.copy()
    df2["slc_group"] = df2["slc_fixed"].where(~df2["slc_fixed"].isin(small), OTHER_SLC)

    g = (df2.dropna(subset=["slc_group"])
            .groupby(["slc_group", "date"])
            .size().rename("count").reset_index())
    if g.empty:
        print("No SLC data to plot.")
        return
    wide = g.pivot(index="date", columns="slc_group", values="count").fillna(0)
    cum = wide.cumsum()

    fig, ax = plt.subplots(figsize=(12, 6))
    x_max = cum.index.max().tz_localize("UTC") if cum.index.tz is None else cum.index.max()
    shade_no_network(ax, x_max)

    # order legend by final totals
    order = cum.iloc[-1].sort_values(ascending=False).index.tolist()
    for slc in order:
        ax.step(cum.index, cum[slc], where="post", label=str(slc))

    ax.set_xlabel("Date (UTC)")
    ax.set_ylabel("Cumulative launches")
    ax.set_title(f"Cumulative launches by Launch Complex (min {MIN_SLC_COUNT} per group; others → '{OTHER_SLC}')")
    ax.grid(True, linestyle="--", alpha=0.4)

    import matplotlib.patches as mpatches
    shaded_patch = mpatches.Patch(alpha=0.12, label="No network period")
    handles, labels = ax.get_legend_handles_labels()
    handles.append(shaded_patch); labels.append("No network period")
    ax.legend(handles, labels, fontsize=8, title="Launch Complex", ncol=2)

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    print(f"✅ Saved {out_png}")
    return cum

def plot_cumulative_windows_vs_sds_vs_detected(df, out_png: str, detections_csv: str):
    # 1) windows
    ls = df["date"].value_counts().sort_index().rename("windows_per_day").to_frame()
    ls["cum_windows"] = ls["windows_per_day"].cumsum()

    # 2) SDS-present
    with_data = df.loc[df["sds_has_any_data"], "date"].value_counts().sort_index().rename("with_data_per_day").to_frame()
    with_data["cum_with_data"] = with_data["with_data_per_day"].cumsum()

    # 3) detected (one per launch row_index and **restricted to retained rows**)
    det_curve = None
    if os.path.exists(detections_csv):
        det = pd.read_csv(detections_csv)
        if {"phase", "row_index"}.issubset(det.columns):
            # Keep detections that map to retained row indices
            valid_idx = set(df["row_index"].astype(int)) if "row_index" in df.columns else None
            det_phase = det[det["phase"].str.lower() == DETECT_PHASE.lower()].copy()
            if valid_idx is not None and "row_index" in det_phase.columns:
                det_phase = det_phase[det_phase["row_index"].isin(valid_idx)]

            onset = pd.to_datetime(det_phase.get("onset_utc", pd.NaT), utc=True, errors="coerce")
            det_phase["onset_dt"] = onset
            if det_phase["onset_dt"].isna().all():
                det_phase["onset_dt"] = pd.to_datetime(det_phase.get("window_start"), utc=True, errors="coerce")
            det_phase = det_phase.dropna(subset=["onset_dt"])
            first_hits = (det_phase.sort_values("onset_dt")
                                   .drop_duplicates(subset=["row_index"], keep="first"))
            detected_daily = (first_hits["onset_dt"].dt.normalize()
                              .value_counts().sort_index()
                              .rename("detected_per_day").to_frame())
            detected_daily["cum_detected"] = detected_daily["detected_per_day"].cumsum()
            det_curve = detected_daily
        else:
            warnings.warn("Detections CSV missing required columns; skipping detected curve.")

    # merge index
    idx = ls.index
    idx = idx.union(with_data.index)
    if det_curve is not None and len(det_curve) > 0:
        idx = idx.union(det_curve.index)
    idx = idx.sort_values()

    merged = pd.DataFrame(index=idx)
    merged["cum_windows"]   = ls.reindex(idx)["cum_windows"].ffill().fillna(0).astype(int)
    merged["cum_with_data"] = with_data.reindex(idx)["cum_with_data"].ffill().fillna(0).astype(int)
    if det_curve is not None:
        merged["cum_detected"] = det_curve.reindex(idx)["cum_detected"].ffill().fillna(0).astype(int)

    # plot
    fig, ax = plt.subplots(figsize=(12, 6))
    x_max = merged.index.max().tz_localize("UTC") if merged.index.tz is None else merged.index.max()
    shade_no_network(ax, x_max)

    ax.step(merged.index, merged["cum_windows"],   where="post", label="Cumulative launch windows (CSV)")
    ax.step(merged.index, merged["cum_with_data"], where="post", label="Cumulative launches with SDS data")
    if "cum_detected" in merged.columns:
        ax.step(merged.index, merged["cum_detected"], where="post", label=f"Cumulative detected {DETECT_PHASE}s")

    import matplotlib.patches as mpatches
    shaded_patch = mpatches.Patch(alpha=0.12, label="No network period")
    handles, labels = ax.get_legend_handles_labels()
    handles.append(shaded_patch); labels.append("No network period")
    ax.legend(handles, labels)

    ax.set_xlabel("Date (UTC)")
    ax.set_ylabel("Count")
    ax.set_title("Cumulative: windows vs SDS-present vs detected")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    print(f"✅ Saved {out_png}")
    return merged

def plot_cumulative_by_vehicle(df, out_png: str):
    totals = df.groupby("vehicle").size().sort_values(ascending=False)
    rare = set(totals[totals < MIN_VEH_COUNT].index) - {"Unknown vehicle"}
    df2 = df.copy()
    df2["vehicle_group"] = df2["vehicle"].where(~df2["vehicle"].isin(rare), OTHER_VEH)

    g = (df2.groupby(["vehicle_group", "date"])
              .size().rename("count").reset_index())
    wide = g.pivot(index="date", columns="vehicle_group", values="count").fillna(0)
    cum = wide.cumsum()

    fig, ax = plt.subplots(figsize=(12, 6))
    x_max = cum.index.max().tz_localize("UTC") if cum.index.tz is None else cum.index.max()
    shade_no_network(ax, x_max)

    # order by final totals; push Unknown/Other to end if present
    final = cum.iloc[-1].sort_values(ascending=False)
    order = [c for c in final.index if c not in (OTHER_VEH, "Unknown vehicle")]
    if OTHER_VEH in cum.columns: order.append(OTHER_VEH)
    if "Unknown vehicle" in cum.columns: order.append("Unknown vehicle")

    for lab in order:
        ax.step(cum.index, cum[lab], where="post", label=str(lab))

    ax.set_xlabel("Date (UTC)")
    ax.set_ylabel("Cumulative launches")
    ax.set_title(f"Cumulative launches by vehicle (min {MIN_VEH_COUNT} per group; others → '{OTHER_VEH}')")
    ax.grid(True, linestyle="--", alpha=0.4)

    import matplotlib.patches as mpatches
    shaded_patch = mpatches.Patch(alpha=0.12, label="No network period")
    handles, labels = ax.get_legend_handles_labels()
    handles.append(shaded_patch); labels.append("No network period")
    ax.legend(handles, labels, ncol=2, fontsize=8, title="Vehicle")

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    print(f"✅ Saved {out_png}")
    return cum

def plot_scatter(df, column: str, out_png: str, title: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(11, 4.8))
    x_max = df["date"].max().tz_localize("UTC") if df["date"].dt.tz is None else df["date"].max()
    shade_no_network(ax, x_max)
    ax.scatter(df["date"], df[column], s=14, alpha=0.7)
    ax.set_xlabel("Date (UTC)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    print(f"✅ Saved {out_png}")


def write_summary_csv(df_slc, df_detected, df_vehicle, out_csv=None):
    """
    Build a tidy summary CSV with the final (last-row) cumulative totals from:
      - df_slc: cumulative by SLC (columns = SLC groups, index = dates)
      - df_detected: cumulative windows/SDS-present/detected (columns: cum_*; index = dates)
      - df_vehicle: cumulative by vehicle (columns = vehicle groups, index = dates)
    """
    parts = []

    # --- SLC totals ---
    if df_slc is not None and not df_slc.empty:
        slc_last = (
            df_slc.iloc[-1]
                 .rename_axis("label")
                 .reset_index(name="total")
        )
        slc_last.insert(0, "category", "SLC")
        parts.append(slc_last)

    # --- Windows / SDS-present / Detected totals ---
    if df_detected is not None and not df_detected.empty:
        cols = [c for c in ["cum_windows", "cum_with_data", "cum_detected"] if c in df_detected.columns]
        det_last = (
            df_detected.iloc[[-1]][cols]
                      .T.reset_index()
                      .rename(columns={"index": "label", df_detected.index.name or df_detected.index.dtype.name: "total"})
        )
        # The line above may create a weird "total" col name if index has a dtype name; fix explicitly:
        det_last.columns = ["label", "total"]
        det_last.insert(0, "category", "Overall")
        # Friendlier labels
        label_map = {
            "cum_windows":   "Launch windows (cumulative)",
            "cum_with_data": "Windows with SDS data (cumulative)",
            "cum_detected":  "Detected launches (cumulative)",
        }
        det_last["label"] = det_last["label"].map(label_map).fillna(det_last["label"])
        parts.append(det_last)

    # --- Vehicle totals ---
    if df_vehicle is not None and not df_vehicle.empty:
        veh_last = (
            df_vehicle.iloc[-1]
                      .rename_axis("label")
                      .reset_index(name="total")
        )
        veh_last.insert(0, "category", "Vehicle")
        parts.append(veh_last)

    if not parts:
        raise ValueError("No data to summarize — all input DataFrames were empty.")

    out = pd.concat(parts, ignore_index=True)
    # Order columns and rows nicely
    out = out[["category", "label", "total"]].sort_values(["category", "label"]).reset_index(drop=True)
    out.to_csv(out_csv, index=False)
    print(f"🧾 Wrote summary cumulative totals → {out_csv}")
    return out

# ========================= main driver =========================
def main():
    os.makedirs(EVENTDIR, exist_ok=True)
    if not os.path.exists(CSVFILE):
        raise FileNotFoundError(f"Missing CSV: {CSVFILE}")

    df = pd.read_csv(CSVFILE)

    # basic checks
    required = {DATECOL, NAMECOL}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")

    # preserve original row_index if present; otherwise add one
    if "row_index" not in df.columns:
        df["row_index"] = range(len(df))

    # parse dates & add day
    df[DATECOL] = pd.to_datetime(df[DATECOL], utc=True, errors="coerce")
    df = df.dropna(subset=[DATECOL]).copy()
    df["date"] = df[DATECOL].dt.normalize()

    # classify vehicle
    df["vehicle"] = df[NAMECOL].apply(classify_vehicle)

    # filter out Electron (non-KSC)
    before = len(df)
    df = df[df["vehicle"].str.lower() != "electron"].copy()
    removed = before - len(df)
    if removed:
        print(f"🧹 Removed {removed} Electron rows (non-KSC).")

    # normalize & fix SLC
    if SLCCOL in df.columns:
        df["slc_fixed"] = df[SLCCOL].apply(normalize_slc)
    else:
        df["slc_fixed"] = None
    df["slc_fixed"] = df.apply(lambda r: fix_slc_by_vehicle(r["slc_fixed"], r["vehicle"]), axis=1)

    # optionally refresh SDS presence counts
    if RESCAN_SDS:
        print("Rescanning SDS for sds_* columns (this may take a while)…")
        have_end = ENDCOL in df.columns
        for i, row in df.iterrows():
            try:
                t_start = to_utc_any(row[DATECOL])
            except Exception as e:
                warnings.warn(f"[row {i}] bad {DATECOL}: {e}")
                continue
            if have_end and pd.notna(row.get(ENDCOL)):
                try:
                    t_end = to_utc_any(row[ENDCOL])
                except Exception:
                    t_end = t_start
            else:
                t_end = t_start
            t1 = t_start - PREPAD
            t2 = t_end + POSTPAD
            try:
                ids = (get_trace_ids_for_window_fast(SDS_ROOT, t1, t2)
                       if FAST_SDS_AVAILABLE else
                       get_trace_ids_for_window_fallback(SDS_ROOT, t1, t2))
            except Exception as e:
                warnings.warn(f"SDS scan failed for row {i}: {e}")
                ids = []
            n_sta, n_seis, n_inf = harvest_counts_from_ids(ids)
            df.at[i, "sds_seed_ids"]   = ";".join(ids)
            df.at[i, "sds_has_any_data"] = (len(ids) > 0)
            df.at[i, "sds_n_stations"] = n_sta
            df.at[i, "sds_n_seis_ch"]  = n_seis
            df.at[i, "sds_n_inf_ch"]   = n_inf

    # make sure sds columns exist (even if RESCAN_SDS is False)
    for col in ["sds_has_any_data", "sds_n_stations", "sds_n_seis_ch", "sds_n_inf_ch"]:
        if col not in df.columns:
            df[col] = 0 if col != "sds_has_any_data" else False

    # write updated CSV in place
    df.to_csv(CSVFILE, index=False)
    print(f"💾 Updated CSV written → {CSVFILE}")

    # plots
    df_slc = plot_cumulative_by_slc(df, OUT_CUM_SLC)
    df_detected = plot_cumulative_windows_vs_sds_vs_detected(df, OUT_WIN_SDS_DET, DETECTIONS_CSV)
    df_vehicle = plot_cumulative_by_vehicle(df, OUT_CUM_VEH)
    plot_scatter(df, "sds_n_stations", OUT_STATIONS, "Stations with data per launch window", "Unique stations")
    plot_scatter(df, "sds_n_seis_ch", OUT_SEIS, "Seismic channels present per launch window", "Seismic channels (?H?)")
    plot_scatter(df, "sds_n_inf_ch", OUT_INF, "Infrasound channels present per launch window", "Infrasound channels (?D?)")

    summary_df = write_summary_csv(df_slc, df_detected, df_vehicle, out_csv=os.path.join(EVENTDIR, "summary_cumulative_totals.csv"))
if __name__ == "__main__":
    main()