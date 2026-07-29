from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from obspy import Stream, UTCDateTime


def plot_key_event_waveforms(
    st_event: Stream,
    *,
    reference_time: UTCDateTime | str,
    pressure_results=None,
    title: str,
    outfile: str | Path | None = None,
    seismic_channels=("HHZ", "HHN", "HHE"),
    infrasound_channels=("HD1", "HD2", "HD3"),
    add_measurements: bool = True,
    figsize=(11.5, 6.8),
):
    """Create a publication-style seismic/infrasound key-event figure."""
    reference_time = UTCDateTime(reference_time)
    seismic_labels = {"HHZ": "Vertical", "HHN": "North", "HHE": "East"}

    seismic = []
    pressure = []
    for channel in seismic_channels:
        matches = st_event.select(channel=channel)
        if len(matches) != 1:
            raise ValueError(f"Expected one {channel}; found {len(matches)}")
        seismic.append(matches[0])
    for channel in infrasound_channels:
        matches = st_event.select(channel=channel)
        if len(matches) != 1:
            raise ValueError(f"Expected one {channel}; found {len(matches)}")
        pressure.append(matches[0])

    fig = plt.figure(figsize=figsize, constrained_layout=True)
    grid = fig.add_gridspec(3, 2, width_ratios=(1.0, 1.25), wspace=0.08, hspace=0.05)
    sax = [fig.add_subplot(grid[i, 0]) for i in range(3)]
    pax = [fig.add_subplot(grid[i, 1]) for i in range(3)]

    slimit = max(np.nanmax(np.abs(tr.data.astype(float))) for tr in seismic) * 1.08

    corrected_pressure = {}
    for tr in pressure:
        baseline = 0.0
        if pressure_results is not None and "baseline_pa" in pressure_results:
            row = pressure_results.loc[pressure_results["channel"] == tr.stats.channel]
            if len(row) == 1:
                baseline = float(row.iloc[0]["baseline_pa"])
        corrected_pressure[tr.stats.channel] = tr.data.astype(float) - baseline

    pmin = min(np.nanmin(v) for v in corrected_pressure.values())
    pmax = max(np.nanmax(v) for v in corrected_pressure.values())
    pad = 0.05 * max(pmax - pmin, 1.0)

    for i, (ax, tr) in enumerate(zip(sax, seismic)):
        t = tr.times(reftime=reference_time)
        ax.plot(t, tr.data.astype(float), lw=0.9)
        ax.axhline(0, lw=0.5, alpha=0.5)
        ax.set_ylim(-slimit, slimit)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.text(0.02, 0.86, seismic_labels.get(tr.stats.channel, tr.stats.channel),
                transform=ax.transAxes, fontweight="bold", va="top")
        if i < 2:
            ax.tick_params(labelbottom=False)
        ax.spines[["top", "right"]].set_visible(False)

    for i, (ax, tr) in enumerate(zip(pax, pressure)):
        channel = tr.stats.channel
        t = tr.times(reftime=reference_time)
        y = corrected_pressure[channel]
        ax.plot(t, y, lw=1.0)
        ax.axhline(0, lw=0.5, alpha=0.5)
        ax.set_ylim(pmin - pad, pmax + pad)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        ax.text(0.02, 0.86, channel, transform=ax.transAxes,
                fontweight="bold", va="top")
        if add_measurements:
            ipos, ineg = int(np.nanargmax(y)), int(np.nanargmin(y))
            ax.scatter(t[ipos], y[ipos], s=24, zorder=4)
            ax.scatter(t[ineg], y[ineg], s=24, zorder=4)
            ax.annotate(f"{y[ipos]:.0f} Pa", (t[ipos], y[ipos]),
                        xytext=(5, -16), textcoords="offset points", fontsize=8)
            ax.annotate(f"{y[ineg]:.0f} Pa", (t[ineg], y[ineg]),
                        xytext=(5, 7), textcoords="offset points", fontsize=8)
        if i < 2:
            ax.tick_params(labelbottom=False)
        ax.spines[["top", "right"]].set_visible(False)

    xmin = min(tr.stats.starttime - reference_time for tr in seismic + pressure)
    xmax = max(tr.stats.endtime - reference_time for tr in seismic + pressure)
    for ax in sax + pax:
        ax.set_xlim(xmin, xmax)
        ax.grid(axis="x", linewidth=0.4, alpha=0.3)

    sax[0].set_title("Ground velocity", fontweight="bold")
    pax[0].set_title("Acoustic pressure", fontweight="bold")
    sax[1].set_ylabel("Ground velocity (m s$^{-1}$)")
    pax[1].set_ylabel("Pressure (Pa)")
    xlabel = (
        f"Time relative to "
        f"{reference_time.strftime('%H:%M:%S.%f')[:-3]} UTC (s)"
    )
    sax[-1].set_xlabel(xlabel)
    pax[-1].set_xlabel(xlabel)
    fig.suptitle(title, fontweight="bold")

    if outfile is not None:
        outfile = Path(outfile)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(outfile, dpi=300, bbox_inches="tight")
        if outfile.suffix.lower() != ".pdf":
            fig.savefig(outfile.with_suffix(".pdf"), bbox_inches="tight")
    return fig, {"seismic": sax, "infrasound": pax}
