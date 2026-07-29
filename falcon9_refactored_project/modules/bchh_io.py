
"""I/O helpers for response-corrected BCHH waveform products."""

from __future__ import annotations

from pathlib import Path
from obspy import Stream, read


def read_corrected_bchh_stream(
    pickle_file,
    mseed_file,
    *,
    starttime=None,
    endtime=None,
    station=None,
    location=None,
) -> Stream:
    pickle_file = Path(pickle_file)
    mseed_file = Path(mseed_file)

    if pickle_file.exists():
        stream = read(str(pickle_file), format="PICKLE")
    elif mseed_file.exists():
        stream = read(str(mseed_file))
    else:
        raise FileNotFoundError(
            f"Neither corrected waveform product exists: {pickle_file}, {mseed_file}"
        )

    if station:
        stream = stream.select(station=station)
    if location is not None:
        selected = stream.select(location=location)
        if len(selected):
            stream = selected
    if starttime is not None or endtime is not None:
        stream.trim(starttime=starttime, endtime=endtime, pad=False)

    return stream


def validate_trace_units(stream: Stream) -> None:
    missing = []
    for trace in stream:
        units = getattr(trace.stats, "units", None)
        if not units:
            missing.append(trace.id)
    if missing:
        print(
            "WARNING: trace units are not embedded for: "
            + ", ".join(missing)
            + ". Verify units from the response-correction summary."
        )
