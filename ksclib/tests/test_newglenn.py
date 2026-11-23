"""New Glenn explosion event (static source at LC-36) and the Centaur fallback module."""
from pathlib import Path

import numpy as np
import pytest

import ksclib
from ksclib import centaur

REPO = Path(__file__).resolve().parents[2]
NEWGLENN = REPO / "10_NewGlenn_paper" / "newglenn.yaml"


@pytest.fixture(scope="module")
def ev():
    if not NEWGLENN.exists():
        pytest.skip("newglenn.yaml not found")
    try:
        return ksclib.load_event(NEWGLENN)
    except (FileNotFoundError, KeyError) as exc:     # station spreadsheet on Box not available
        pytest.skip(str(exc))


def test_event(ev):
    assert ev.kind == "static" and ev.site_name == "LC36"
    assert abs(ev.site_lat - 28.470556) < 1e-5 and abs(ev.site_lon + 80.5422) < 1e-5
    assert ev.origin_time.julday == 149
    assert centaur.chaparral_config(ev) == {"channels": ("DDF",), "V_per_Pa": 0.4}


def test_geometry(ev):
    tab = ksclib.station_table(ev)
    assert 10 < tab.distance_km.min() < tab.distance_km.max() < 25     # network is 12-20 km north
    g = ksclib.source_geometry(ev, "B20", stations=tab)
    assert np.allclose(g.t_obs - g.t_s, tab.loc["B20", "distance_km"] * 1000 / 343)


def test_response_fallback(ev):
    if not all(Path(d).is_dir() for d in ev.centaur_response_dirs[:1]):
        pytest.skip("response folders not mounted")
    with pytest.warns(UserWarning, match="no Centaur response before"):
        p = centaur.centaur_response_file_nearest(ev, "B14")
    assert p.name.startswith("1R.B14_20260614")
    assert centaur.centaur_response_file_nearest(ev, "B01").name == "1R.B01_20260528T204512Z.xml"
    with pytest.warns(UserWarning):
        b14 = centaur.centaur_inventory_nearest(ev, "B14")
    assert b14.select(channel="DHZ", time=ev.origin_time)            # epoch backdated
    inv = centaur.centaur_inventory_nearest(ev, "B20")
    ddf = inv.select(channel="DDF")[0][0][0].response
    assert ddf.instrument_sensitivity.input_units == "Pa"
    assert ddf.instrument_sensitivity.value == pytest.approx(0.4 * 16e6, rel=1e-3)
