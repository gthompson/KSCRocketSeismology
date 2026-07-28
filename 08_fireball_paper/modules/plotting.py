
"""Reusable plotting helpers used by the paper-figure notebook."""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from obspy import Stream, UTCDateTime


def plot_key_event_waveforms(
    stream: Stream,
    reference_time: UTCDateTime,
    pressure_results=None,
    title: str = "",
    outfile: Path | None = None,
    add_measurements: bool = True,
):
    if len(stream) == 0:
        raise ValueError("No traces supplied to plot_key_event_waveforms")

    fig, axes = plt.subplots(
        len(stream),
        1,
        figsize=(10.5, max(4.5, 1.25 * len(stream))),
        sharex=True,
    )
    if len(stream) == 1:
        axes = [axes]

    for ax, trace in zip(axes, stream):
        x = trace.times(reftime=reference_time)
        y = np.asarray(trace.data, dtype=float)
        scale = np.nanpercentile(np.abs(y), 99.5)
        if not np.isfinite(scale) or scale <= 0:
            scale = 1.0

        ax.plot(x, y / scale, color="black", lw=0.7)
        ax.set_ylabel(trace.stats.channel, rotation=0, ha="right", va="center")
        ax.grid(axis="x", alpha=0.25)

    axes[-1].set_xlabel("Time relative to window start (s)")
    axes[0].set_title(title)

    if (
        add_measurements
        and pressure_results is not None
        and hasattr(pressure_results, "empty")
        and not pressure_results.empty
    ):
        axes[0].text(
            0.99,
            0.95,
            f"{len(pressure_results)} measurement row(s)",
            transform=axes[0].transAxes,
            ha="right",
            va="top",
            fontsize=8,
        )

    for ax in axes:
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    fig.tight_layout()

    if outfile is not None:
        outfile = Path(outfile)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(outfile, dpi=300, bbox_inches="tight")
        fig.savefig(outfile.with_suffix(".pdf"), dpi=300, bbox_inches="tight")

    return fig, axes
