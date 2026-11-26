"""SEED band-code handling during the D -> C/H rename (ksclib.seedcodes)."""
import numpy as np
from obspy import Stream, Trace

from ksclib.seedcodes import (alias_patterns, centaur_response_codes, is_centaur, normalize_id,
                              normalize_stream, same_code, seed_channel)


def tr(loc, cha, sr):
    from obspy import UTCDateTime
    return Trace(np.zeros(10), header=dict(network="1R", station="B20", location=loc, channel=cha,
                                           sampling_rate=sr, starttime=UTCDateTime(2026, 4, 1)))


def test_seed_channel():
    assert seed_channel("00", "DD1", 500) == "CD1"
    assert seed_channel("00", "DHZ", 250) == "CHZ"
    assert seed_channel("00", "DDF", 100) == "HDF"       # B20 2026-04-04..06-14
    assert seed_channel("", "DPZ", 500) == "DPZ"         # SmartSolo stays D
    assert seed_channel("", "HDF", 100) == "HDF"         # Gem
    assert seed_channel("00", "CHZ", 500) == "CHZ"       # already renamed
    assert seed_channel("00", "EHZ", 200) == "EHZ"


def test_is_centaur_and_normalize():
    assert is_centaur(tr("00", "HDF", 100)) and not is_centaur(tr("", "HDF", 100))
    assert not is_centaur(tr("10", "HDI", 100))          # 2026 Gem at location 10 (B20, B07)
    st = normalize_stream(Stream([tr("00", "DH1", 500), tr("00", "DD2", 100), tr("", "DPN", 500)]))
    assert [t.stats.channel for t in st] == ["CH1", "HD2", "DPN"]
    assert normalize_id("1R.B29.00.DHZ") == "1R.B29.00.CHZ"


def test_aliases():
    assert alias_patterns("*", "D[DH]?") == [("*", "D[DH]?"), ("*", "C[DH]?"), ("00", "H[DH]?")]
    assert alias_patterns("", "HD?") == [("", "HD?")]
    assert same_code("DD1", "CD1") and same_code("HD1", "DD1") and not same_code("DD1", "DP1")
    assert centaur_response_codes("DHZ") == ["DHZ", "CHZ", "HHZ"] and centaur_response_codes("LHZ") == ["LHZ"]
