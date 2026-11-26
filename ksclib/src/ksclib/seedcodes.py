"""SEED band codes for the Centaur broadband channels, during and after the D -> C/H rename (2026-11-26).

The Centaurs name their channels with band code D at 250/500 sps (DH? Trillium, DD? infraBSU/Chaparral).
D is for sensors with a corner period below 10 s; these sensors are broadband, so the SEED codes are C at
250-999 sps and H at 80-249 sps. 03_stationxml/KSC.xml uses the SEED codes; the archives are renamed by
03_stationxml/archive_fix/rename_band_codes.py, and new Centaur downloads still arrive as D??.

ksclib therefore
  * reads both spellings (`alias_patterns`): a group pattern "D[DH]?" also reads "C[DH]?" and, on
    Centaur location codes only, "H[DH]?";
  * renames traces to the SEED code (`normalize_stream`) for StationXML eras (KSC.xml uses SEED codes)
    and for event YAMLs that set `seed_band_codes: true`; otherwise traces keep the archive's spelling
    (the 2026 paper notebooks still select DD0/DHZ), and the correction code accepts both;
  * matches D-named Centaur response files to C/H-named traces (`centaur_response_codes`).

Centaur channels are told apart from Gem (HD?) and SmartSolo (DP?) channels by location code: in 2026
Centaurs use 00, Gems '' or 10, SmartSolos ''.
"""
from __future__ import annotations

from obspy import Stream


def is_centaur(tr) -> bool:
    """True for a 1R Centaur broadband channel (band C, D or H; ?H? seismic or ?D? pressure).

    Location codes (03_stationxml master sheet): Centaurs 00 (2016-2026) and 10/20 (BCHH, 2016);
    Gems '' or 10 and SmartSolos '' (2026 only). So in 2023 and later only location 00 is a Centaur.
    """
    st = tr.stats
    cha, loc = st.channel, st.location
    if st.network not in ("1R", "") or len(cha) != 3 or cha[0] not in "CDH" or cha[1] not in "DH":
        return False
    if loc == "00":
        return True
    return loc in ("10", "20") and st.starttime.year < 2023


def seed_channel(location: str, channel: str, sampling_rate: float) -> str:
    """SEED channel code for a Centaur D?? channel (others unchanged; only Centaurs write D[DH]?)."""
    if not location or location == "--" or len(channel) != 3 or channel[0] != "D" or channel[1] not in "DH":
        return channel
    if sampling_rate >= 250:
        return "C" + channel[1:]
    if sampling_rate >= 80:
        return "H" + channel[1:]
    return channel


def normalize_stream(st: Stream) -> Stream:
    """Rename D-band Centaur traces to their SEED code, in place; returns st."""
    for tr in st:
        tr.stats.channel = seed_channel(tr.stats.location, tr.stats.channel, tr.stats.sampling_rate)
    return st


def normalize_id(seed_id: str, sampling_rate: float = 500.0) -> str:
    n, s, l, c = seed_id.split(".")
    return f"{n}.{s}.{l}.{seed_channel(l, c, sampling_rate)}"


def alias_patterns(location: str, channel: str) -> list[tuple[str, str]]:
    """(location, channel) patterns that read a group in either spelling.

    "D[DH]?" -> D[DH]? and C[DH]? on the same location, plus H[DH]? on location 00 (Centaurs at 100 sps
    after the rename; Gem HD? use '' or 10).
    """
    out = [(location, channel)]
    if channel[:1] == "D" and channel[1:2] in ("D", "H", "["):
        out.append((location, "C" + channel[1:]))
        out.append(("00" if location in ("*", "??") else location, "H" + channel[1:]))
    return out


def same_code(a: str, b: str) -> bool:
    """True if two Centaur channel codes differ only in the band letter (D/C/H)."""
    return len(a) == len(b) == 3 and a[1:] == b[1:] and {a[0], b[0]} <= set("CDH")


def centaur_response_codes(code: str) -> list[str]:
    """Codes a D-named Centaur response channel may carry in renamed data."""
    if code[:1] == "D" and code[1:2] in "DH":
        return [code, "C" + code[1:], "H" + code[1:]]
    return [code]
