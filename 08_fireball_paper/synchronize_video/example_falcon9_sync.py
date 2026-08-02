"""
example_falcon9_sync.py

Skeleton showing how the two modules fit together.

Replace selectors, file paths and absolute UTC times with the values from the
Falcon 9 event configuration.
"""

from obspy import UTCDateTime, read

from polarization import covariance_polarization_series
from video_sync import (
    OverlayDelay,
    SyncConfig,
    VideoSource,
    render_frames,
    assemble_movie,
)


# --- waveforms ---------------------------------------------------------------

st = read("/absolute/path/to/falcon9_waveforms.mseed")

# Example only: adapt these selectors to the actual BCHH channel codes.
z = st.select(channel="*Z")[0]
n = st.select(channel="*N")[0]
e = st.select(channel="*E")[0]

pol = covariance_polarization_series(
    z=z.data,
    n=n.data,
    e=e.data,
    sampling_rate=z.stats.sampling_rate,
    window_seconds=0.5,
    step_seconds=0.05,
)

# --- video/event timing -------------------------------------------------------

cfg = SyncConfig(
    event_name="Falcon 9 — 2016-09-01",
    start_utc=UTCDateTime("2016-09-01T13:06:30Z"),
    end_utc=UTCDateTime("2016-09-01T13:08:30Z"),
    fps=20.0,
    zoom_seconds=10.0,
    output_dir="falcon9_sync_frames",
    videos=[
        VideoSource(
            path="/absolute/path/to/public_video.mp4",
            start_utc=UTCDateTime("2016-09-01T13:06:00Z"),
            title="Public video",
        ),
    ],
    overlay_delays=[
        # These are examples only. Replace with event-specific values.
        OverlayDelay("Predicted airwave", 4.0),
        OverlayDelay("Predicted seismic", 0.5),
    ],
)

render_frames(
    cfg,
    waveform_stream=st,
    seismic_selector={"channel": "BH?"},
    infrasound_selector={"channel": "BD?"},
    polarization_time_s=pol.time_s,
    polarization_series={
        "linearity": pol.linearity,
        "planarity": pol.planarity,
        "rectilinearity": pol.rectilinearity,
    },
)

assemble_movie(
    frames_dir=cfg.output_dir,
    output_file="falcon9_sync.mp4",
    fps=cfg.fps,
)
