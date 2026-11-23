from pathlib import Path

import numpy as np
import pytest

import ksclib

REPO = Path(__file__).resolve().parents[2]
ARTEMIS = REPO / "09_artemis2_paper" / "artemis2.yaml"


@pytest.fixture(scope="module")
def ev():
    if not ARTEMIS.exists():
        pytest.skip("artemis2.yaml not found")
    try:
        return ksclib.load_event(ARTEMIS)
    except FileNotFoundError as exc:     # station spreadsheet on Box not available
        pytest.skip(str(exc))


def test_windows(ev):
    assert str(ev.origin_time) == "2026-04-01T22:35:12.000000Z"
    assert ev.endtime - ev.starttime == 1800 + 900 + 1800
    assert ev.kind == "launch" and ev.site_name == "LC39B"
    assert abs(ev.site_lat - 28.62722) < 1e-4


def test_geometry(ev):
    tab = ksclib.station_table(ev)
    assert abs(tab.loc["B01", "distance_km"] - 1.53) < 0.01
    g = ksclib.source_geometry(ev, "B29", stations=tab)
    assert np.all(np.diff(g.t_obs) > 0)              # single-valued arrival times
    assert abs(g.t_obs.iloc[0] - tab.loc["B29", "distance_km"] * 1000 / 343) < 1e-6


def test_static_source_has_no_motion(ev):
    from dataclasses import replace
    st = replace(ev, kind="static")
    g = ksclib.source_geometry(st, "B01")
    assert np.allclose(g.r_m, g.r_m.iloc[0]) and np.allclose(g.alt_km, 0)
