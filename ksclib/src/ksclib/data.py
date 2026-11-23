"""Waveform access: the master SDS archive, with per-file fallback and restored channels."""
from __future__ import annotations

import warnings
from pathlib import Path

from obspy import Stream, UTCDateTime, read

SKIPPED_FILES: list = []   # unreadable SDS files met by get_group_stream: (path, error)


def sds_client(event_or_root):
    """EnhancedSDSClient on an event's master SDS archive (or on an explicit SDS root)."""
    from flovopy.enhanced.sdsclient import EnhancedSDSClient
    root = Path(getattr(event_or_root, "master_sds", event_or_root))
    if not root.is_dir():
        raise FileNotFoundError(f"Master SDS not found (is the drive mounted?): {root}")
    return EnhancedSDSClient(str(root))


def read_sds_files(sds_root, net, sta, loc, cha, starttime, endtime):
    """Read matching SDS day files one by one, skipping (and recording) unreadable ones."""
    st = Stream()
    day = UTCDateTime(starttime.date)
    while day <= endtime:
        pattern = f"{day.year}/{net}/{sta}/{cha}.D/{net}.{sta}.{loc}.{cha}.D.{day.year}.{day.julday:03d}"
        for path in sorted(Path(sds_root).glob(pattern)):
            try:
                st += read(str(path), format="MSEED", starttime=starttime, endtime=endtime)
            except Exception as exc:
                SKIPPED_FILES.append((str(path), f"{type(exc).__name__}: {exc}"))
                warnings.warn(f"SKIPPED unreadable SDS file {path} ({type(exc).__name__})")
        day += 86400
    return st


def get_group_stream(event, group, client=None, starttime=None, endtime=None):
    """Waveforms for one of the event's channel groups from the master SDS.

    If any file in the group is unreadable, the group is re-read file by file and the
    bad files are skipped with a warning and listed in SKIPPED_FILES.
    """
    starttime = starttime or event.starttime
    endtime = endtime or event.endtime
    client = client or sds_client(event)
    net, sta, loc, cha = event.channel_groups[group]
    try:
        return client.get_waveforms(network=net, station=sta, location=loc, channel=cha,
                                    starttime=starttime, endtime=endtime)
    except Exception:
        return read_sds_files(event.master_sds, net, sta, loc, cha, starttime, endtime)


def get_event_stream(event, client=None, groups=None, starttime=None, endtime=None):
    """Waveforms for the given (default: all) channel groups, merged."""
    client = client or sds_client(event)
    st = Stream()
    for group in groups or event.channel_groups:
        st += get_group_stream(event, group, client, starttime, endtime)
    st.merge()
    return st


def read_restored(event, seed_id, starttime=None, endtime=None):
    """Read a channel from its restored-data SDS folder (event.restored[seed_id])."""
    from obspy.clients.filesystem.sds import Client
    net, sta, loc, cha = seed_id.split(".")
    return Client(str(event.restored[seed_id])).get_waveforms(
        net, sta, loc, cha, starttime or event.starttime, endtime or event.endtime)


def event_stream_raw(event, client=None, groups=("USF", "BSU", "SmartSolo"), starttime=None, endtime=None):
    """Raw stream for the given groups, with any restored channels substituted where missing."""
    st = get_event_stream(event, client, groups=groups, starttime=starttime, endtime=endtime)
    added = False
    for sid in event.restored:
        if not st.select(id=sid):
            st += read_restored(event, sid, starttime, endtime)
            added = True
    if added:
        st.merge()
    return st
