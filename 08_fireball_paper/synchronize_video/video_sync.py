"""
video_sync.py

Synchronized local-video + waveform renderer.

Design goal:
    Reproduce the MATLAB 40_make_synchronized_video workflow without writing
    one MAT file per video frame.

Dependencies:
    numpy
    matplotlib
    obspy
    av          (PyAV; accurate timestamp-based local video access)

Movie assembly:
    ffmpeg executable on PATH

This is intentionally event-agnostic. Absolute UTC timing is supplied in the
VideoSource configuration for each clip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
import subprocess

import av
import matplotlib.pyplot as plt
import numpy as np
from obspy import Stream, UTCDateTime


@dataclass
class VideoSource:
    path: str
    start_utc: UTCDateTime
    title: str = ""
    panel: int = 0


@dataclass
class OverlayDelay:
    label: str
    delay_seconds: float


@dataclass
class SyncConfig:
    event_name: str
    start_utc: UTCDateTime
    end_utc: UTCDateTime
    fps: float = 20.0
    zoom_seconds: float = 10.0
    output_dir: str = "sync_frames"
    videos: list[VideoSource] = field(default_factory=list)
    overlay_delays: list[OverlayDelay] = field(default_factory=list)


class VideoReaderUTC:
    """
    Timestamp-driven local-video reader using PyAV.

    A video's UTC time is:
        source.start_utc + frame.pts * stream.time_base

    This avoids assuming that frame_number / nominal_fps is the true timestamp.
    """

    def __init__(self, source: VideoSource):
        self.source = source
        self.container = av.open(source.path)
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"

        self._last_time_s = None
        self._last_frame = None

    def close(self):
        self.container.close()

    def _seek_seconds(self, rel_s: float):
        rel_s = max(0.0, rel_s)
        # seek() uses AV_TIME_BASE units when stream is not specified.
        self.container.seek(
            int(rel_s * av.time_base),
            backward=True,
            any_frame=False,
        )

    def frame_at_utc(self, utc: UTCDateTime):
        rel_s = float(utc - self.source.start_utc)
        if rel_s < 0:
            return None

        # Seeking every frame is robust and simple. For long productions this
        # can later be optimized to decode monotonically.
        self._seek_seconds(rel_s)

        best = None
        best_dt = np.inf

        for frame in self.container.decode(video=0):
            if frame.pts is None:
                continue
            frame_s = float(frame.pts * frame.time_base)
            dt = abs(frame_s - rel_s)
            if dt < best_dt:
                best = frame
                best_dt = dt
            if frame_s >= rel_s:
                break

        if best is None:
            return None
        return best.to_ndarray(format="rgb24")


def _trace_time_seconds(tr, reference: UTCDateTime) -> np.ndarray:
    return (
        np.arange(tr.stats.npts, dtype=float) / tr.stats.sampling_rate
        + float(tr.stats.starttime - reference)
    )


def _plot_waveform_panel(ax, traces, reference, cursor_s, title):
    for tr in traces:
        t = _trace_time_seconds(tr, reference)
        data = np.asarray(tr.data, dtype=float)
        scale = np.nanmax(np.abs(data))
        y = data / scale if scale > 0 else data
        ax.plot(t, y, lw=0.8, label=tr.id)
    ax.axvline(cursor_s, lw=1.2)
    ax.set_title(title)
    ax.set_xlim(
        min(_trace_time_seconds(tr, reference)[0] for tr in traces),
        max(_trace_time_seconds(tr, reference)[-1] for tr in traces),
    )
    ax.legend(loc="upper right", fontsize=7)


def _plot_zoom_panel(ax, traces, reference, cursor_s, zoom_seconds, title):
    half = zoom_seconds / 2.0
    for tr in traces:
        t = _trace_time_seconds(tr, reference)
        data = np.asarray(tr.data, dtype=float)
        scale = np.nanmax(np.abs(data))
        y = data / scale if scale > 0 else data
        ax.plot(t, y, lw=0.9, label=tr.id)
    ax.axvline(cursor_s, lw=1.2)
    ax.set_xlim(cursor_s - half, cursor_s + half)
    ax.set_title(title)


def render_frames(
    cfg: SyncConfig,
    waveform_stream: Stream,
    seismic_selector: Optional[dict] = None,
    infrasound_selector: Optional[dict] = None,
    polarization_time_s: Optional[np.ndarray] = None,
    polarization_series: Optional[dict[str, np.ndarray]] = None,
) -> list[Path]:
    """
    Render synchronized PNG frames.

    `seismic_selector` / `infrasound_selector` are kwargs for Stream.select(),
    e.g. {"station": "BCHH", "channel": "BH?"}.

    `polarization_series` can contain arrays such as:
        {"linearity": ..., "planarity": ..., "ellipticity": ...}
    using the same time base as `polarization_time_s`.
    """
    outdir = Path(cfg.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    readers = [VideoReaderUTC(v) for v in cfg.videos]

    seis = (
        waveform_stream.select(**seismic_selector)
        if seismic_selector
        else waveform_stream
    )
    infra = (
        waveform_stream.select(**infrasound_selector)
        if infrasound_selector
        else Stream()
    )

    duration = float(cfg.end_utc - cfg.start_utc)
    nframes = int(np.floor(duration * cfg.fps)) + 1

    saved = []
    try:
        for iframe in range(nframes):
            rel_s = iframe / cfg.fps
            now = cfg.start_utc + rel_s

            n_video = max(1, len(readers))
            extra_pol = polarization_time_s is not None and polarization_series
            nrows = n_video + 2 + (1 if extra_pol else 0)

            fig, axes = plt.subplots(
                nrows=nrows,
                ncols=1,
                figsize=(12, 3.0 * nrows),
                constrained_layout=True,
            )
            axes = np.atleast_1d(axes)

            row = 0
            if readers:
                for reader in readers:
                    frame = reader.frame_at_utc(now)
                    ax = axes[row]
                    if frame is None:
                        ax.text(
                            0.5, 0.5, "No video frame at this UTC time",
                            ha="center", va="center", transform=ax.transAxes
                        )
                    else:
                        ax.imshow(frame)
                    ax.set_axis_off()
                    ax.set_title(
                        reader.source.title or Path(reader.source.path).name
                    )
                    row += 1
            else:
                axes[row].text(
                    0.5, 0.5, "No video configured",
                    ha="center", va="center", transform=axes[row].transAxes
                )
                axes[row].set_axis_off()
                row += 1

            if len(infra):
                _plot_waveform_panel(
                    axes[row], infra, cfg.start_utc, rel_s, "Infrasound"
                )
            else:
                axes[row].text(0.5, 0.5, "No infrasound traces selected",
                               ha="center", va="center")
            row += 1

            if len(seis):
                _plot_zoom_panel(
                    axes[row], seis, cfg.start_utc, rel_s,
                    cfg.zoom_seconds, "Seismic — scrolling zoom"
                )
                for overlay in cfg.overlay_delays:
                    axes[row].axvline(
                        rel_s + overlay.delay_seconds,
                        ls="--", lw=0.8,
                        label=overlay.label,
                    )
            row += 1

            if extra_pol:
                ax = axes[row]
                for name, values in polarization_series.items():
                    ax.plot(polarization_time_s, values, label=name)
                ax.axvline(rel_s, lw=1.2)
                ax.set_xlim(rel_s - cfg.zoom_seconds / 2,
                            rel_s + cfg.zoom_seconds / 2)
                ax.set_ylim(-0.05, 1.05)
                ax.set_title("Polarization attributes")
                ax.legend(loc="upper right")

            fig.suptitle(
                f"{cfg.event_name} — {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC"
            )

            outfile = outdir / f"frame_{iframe:06d}.png"
            fig.savefig(outfile, dpi=120)
            plt.close(fig)
            saved.append(outfile)

    finally:
        for reader in readers:
            reader.close()

    return saved


def assemble_movie(
    frames_dir: str,
    output_file: str,
    fps: float,
    audio_file: Optional[str] = None,
    crf: int = 18,
):
    """
    Assemble frame_XXXXXX.png into an H.264 MP4 with ffmpeg.

    If audio_file is supplied, it is muxed with the rendered video.
    """
    frames_pattern = str(Path(frames_dir) / "frame_%06d.png")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", frames_pattern,
    ]

    if audio_file:
        cmd += ["-i", str(audio_file), "-shortest"]

    cmd += [
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
        str(output_file),
    ]

    subprocess.run(cmd, check=True)
