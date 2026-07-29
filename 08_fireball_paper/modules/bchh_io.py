from __future__ import annotations

from pathlib import Path
import warnings

from obspy import Stream, UTCDateTime, read


DEFAULT_CHANNEL_ORDER = ("HD1", "HD2", "HD3", "HHE", "HHN", "HHZ")


def read_corrected_bchh_stream(
    pickle_file: str | Path,
    miniseed_file: str | Path,
    *,
    starttime: UTCDateTime | str | None = None,
    endtime: UTCDateTime | str | None = None,
    network: str | None = None,
    station: str | None = "BCHH",
    location: str | None = "00",
    channel_order: tuple[str, ...] = DEFAULT_CHANNEL_ORDER,
) -> Stream:
    """Load and validate one authoritative six-channel corrected BCHH stream."""
    pickle_file = Path(pickle_file)
    miniseed_file = Path(miniseed_file)

    if pickle_file.exists():
        stream = read(str(pickle_file), format="PICKLE")
        source_file = pickle_file
    elif miniseed_file.exists():
        stream = read(str(miniseed_file), format="MSEED")
        source_file = miniseed_file
        warnings.warn(
            "Loaded corrected miniSEED rather than Pickle; custom metadata "
            "such as units may not be preserved."
        )
    else:
        raise FileNotFoundError(
            "No corrected BCHH stream found. Expected one of:\n"
            f"  {pickle_file}\n  {miniseed_file}"
        )

    if network is not None:
        stream = stream.select(network=network)
    if station is not None:
        stream = stream.select(station=station)
    if location is not None:
        stream = stream.select(location=location)

    if starttime is not None or endtime is not None:
        t0 = UTCDateTime(starttime) if starttime is not None else None
        t1 = UTCDateTime(endtime) if endtime is not None else None
        stream.trim(starttime=t0, endtime=t1, pad=False)

    selected = Stream()
    for channel in channel_order:
        matches = stream.select(channel=channel)
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one {channel} trace after selection; "
                f"found {len(matches)}: {[tr.id for tr in matches]}"
            )
        selected += matches[0].copy()

    selected.sort(keys=["channel"])
    selected.stats = getattr(selected, "stats", {})
    print(f"Loaded corrected BCHH stream from: {source_file}")
    print(selected)
    return selected


def select_channels_in_order(
    stream: Stream,
    channel_order: tuple[str, ...] = DEFAULT_CHANNEL_ORDER,
) -> Stream:
    """Return one unique trace for each requested channel."""
    selected = Stream()
    for channel in channel_order:
        matches = stream.select(channel=channel)
        if len(matches) != 1:
            raise ValueError(
                f"Expected one trace for {channel}; found "
                f"{[tr.id for tr in matches]}"
            )
        selected += matches[0].copy()
    return selected


def is_infrasound_channel(channel: str) -> bool:
    channel = channel.upper()
    return channel.startswith("HD") or channel.startswith("DD")


def is_seismic_channel(channel: str) -> bool:
    channel = channel.upper()
    return channel.startswith(("HH", "DH", "EH", "BH"))


def validate_trace_units(stream: Stream) -> None:
    """Print units and warn when corrected-stream units are absent."""
    for tr in stream:
        units = tr.stats.get("units")
        if units is None:
            warnings.warn(f"{tr.id}: no units stored in trace metadata")
        print(f"{tr.id}: {units or 'unknown units'}")
