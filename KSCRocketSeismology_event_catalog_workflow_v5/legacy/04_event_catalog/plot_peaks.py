import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PAP_CSV = "pap_max_1s_rms_clipped.csv"   # infrasound (pressure)
PGV_CSV = "pgv_max_1s_rms_clipped.csv"   # seismic (ground velocity)

# ----------------------------
# Helpers
# ----------------------------
def seed_station(seed_id: str) -> str:
    """Return station code from NET.STA.LOC.CHA (or '' if it doesn't match)."""
    try:
        return seed_id.split(".")[1]
    except Exception:
        return ""

def site4_from_seed(seed_id: str) -> str:
    """Site = first 4 chars of station code."""
    sta = seed_station(seed_id)
    return sta[:4] if sta else ""

def get_value_columns(df: pd.DataFrame):
    """Assume non-value columns are starttime/endtime/slug if present; everything else is a SEED-ID column."""
    meta = [c for c in ["starttime", "endtime", "slug"] if c in df.columns]
    val_cols = [c for c in df.columns if c not in meta]
    return meta, val_cols

def coerce_numeric(df: pd.DataFrame, cols):
    """Make sure value columns are numeric (NaNs if not)."""
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

def make_xlabels(df: pd.DataFrame):
    """
    Optional “bonus” x-axis labels.
    Returns list of labels length N (rows). Uses slug and starttime if present.
    """
    n = len(df)
    slug = df["slug"].astype(str).tolist() if "slug" in df.columns else [""] * n
    st = df["starttime"].astype(str).tolist() if "starttime" in df.columns else [""] * n
    # Keep it short-ish: slug only; or slug + date prefix
    labels = []
    for s, t in zip(slug, st):
        if t and t != "nan":
            # take YYYY-MM-DD if it’s ISO-ish
            date = t[:10]
            labels.append(f"{date}\n{s}" if s else date)
        else:
            labels.append(s)
    return labels

def plot_site_series(df: pd.DataFrame, site: str, val_cols, title: str, ylab: str,
                     use_xlabels: bool = False, max_xticks: int = 12, outfile: str | None = None):
    """
    Plot *all* channels for a site vs row number.
    """
    # pick columns whose station starts with site (first 4 chars)
    site_cols = [c for c in val_cols if site4_from_seed(c) == site]
    if not site_cols:
        return False

    x = np.arange(len(df))  # row ordinal / launch number
    plt.figure(figsize=(12, 5))

    for c in site_cols:
        y = df[c].to_numpy(dtype=float)
        plt.plot(x, y, marker=".", linewidth=1, label=c)

    plt.title(f"{title} — Site {site}  (n_rows={len(df)}, n_channels={len(site_cols)})")
    plt.xlabel("Row number (launch ordinal)")
    plt.ylabel(ylab)
    plt.grid(True, alpha=0.3)

    if use_xlabels:
        labels = make_xlabels(df)
        # Avoid a totally unreadable axis: show at most max_xticks evenly spaced
        n = len(df)
        if n > 0:
            idx = np.linspace(0, n - 1, num=min(max_xticks, n), dtype=int)
            plt.xticks(idx, [labels[i] for i in idx], rotation=45, ha="right")

    plt.legend(fontsize=8, ncol=2, frameon=False)

    plt.tight_layout()
    if outfile:
        plt.savefig(outfile, dpi=200)
    plt.show()
    return True

# ----------------------------
# Load both files
# ----------------------------
pap = pd.read_csv(PAP_CSV)
pgv = pd.read_csv(PGV_CSV)

pap_meta, pap_vals = get_value_columns(pap)
pgv_meta, pgv_vals = get_value_columns(pgv)

pap = coerce_numeric(pap, pap_vals)
pgv = coerce_numeric(pgv, pgv_vals)

# Build the site list from BOTH files (first 4 chars of station name)
sites = sorted({site4_from_seed(c) for c in pap_vals + pgv_vals if site4_from_seed(c)})

print(f"Found {len(sites)} sites:", sites)

# ----------------------------
# Plot loop: for each site, make a PAP plot and a PGV plot
# ----------------------------
USE_XLABELS = False          # set True if you want sparse date/slug tick labels
MAX_XTICKS = 10              # only used if USE_XLABELS=True
SAVE_FIGS = False            # set True to save PNGs
OUTDIR = "site_plots"        # created only if SAVE_FIGS=True

import os
if SAVE_FIGS:
    os.makedirs(OUTDIR, exist_ok=True)

for site in sites:
    # Infrasound
    out1 = os.path.join(OUTDIR, f"{site}_pap.png") if SAVE_FIGS else None
    plot_site_series(
        pap, site, pap_vals,
        title="PAP (infrasound) max 1s RMS (clipped)",
        ylab="Pressure (Pa)",
        use_xlabels=USE_XLABELS,
        max_xticks=MAX_XTICKS,
        outfile=out1
    )

    # Seismic
    out2 = os.path.join(OUTDIR, f"{site}_pgv.png") if SAVE_FIGS else None
    plot_site_series(
        pgv, site, pgv_vals,
        title="PGV (seismic) max 1s RMS (clipped)",
        ylab="Ground velocity (m/s)",   # change if yours are in different units
        use_xlabels=USE_XLABELS,
        max_xticks=MAX_XTICKS,
        outfile=out2
    )
