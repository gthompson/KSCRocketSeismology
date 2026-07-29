from __future__ import annotations

from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime


def load_video_audio_as_stream(
    audio_file: str | Path,
    starttime: UTCDateTime | str,
    *,
    network: str = "YT",
    station: str = "SYNC",
    channel: str = "AUD",
) -> Stream:
    """Load an audio file as a single ObsPy trace."""
    try:
        import librosa
    except ImportError as exc:
        raise ImportError("librosa is required to load video audio") from exc

    y, sampling_rate = librosa.load(Path(audio_file), sr=None)
    tr = Trace(np.asarray(y, dtype=np.float32))
    tr.stats.sampling_rate = sampling_rate
    tr.stats.network = network
    tr.stats.station = station
    tr.stats.location = ""
    tr.stats.channel = channel
    tr.stats.starttime = UTCDateTime(starttime)
    return Stream([tr])
