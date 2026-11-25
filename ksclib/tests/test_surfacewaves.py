"""Rayleigh dispersion (thin-layer method) and refraction travel times."""
import numpy as np
import pytest

from ksclib import surfacewaves as sw


def test_halfspace_rayleigh_speed():
    # Poisson solid (vp = sqrt(3) vs): c_R = 0.91940 vs, independent of frequency
    m = ([100.0, 0.0], [1732.05, 1732.05], [1000.0, 1000.0], [2000.0, 2000.0])
    c = sw.rayleigh_phase(m, [1.0, 5.0, 20.0], backend='thinlayer').ravel()
    assert c == pytest.approx(919.40, rel=1e-3)


def test_layer_over_halfspace_limits_and_modes():
    m = ([20.0, 0.0], [600.0, 2000.0], [300.0, 1000.0], [1800.0, 2100.0])
    f = np.array([0.5, 4.0, 32.0])
    c = sw.rayleigh_phase(m, f, nmodes=2, backend='thinlayer', nper=10)
    # low frequency -> half-space Rayleigh speed (nu = 0.333: 0.9325 vs); high -> layer's
    assert c[0, 0] == pytest.approx(932.5, rel=0.015)        # slightly below: the slow layer still loads it
    assert c[2, 0] == pytest.approx(0.9325 * 300, rel=0.01)
    assert np.all(np.diff(c[:, 0]) < 0)                    # normal dispersion
    assert np.isnan(c[0, 1]) and c[2, 1] > c[2, 0]           # first higher mode only at high f
    U = sw.rayleigh_group(m, f, backend='thinlayer', nper=10).ravel()
    assert np.all(U[:2] < c[:2, 0])                         # group slower than phase where dispersive
    fine = sw.rayleigh_phase(m, f, nper=20, backend='thinlayer')
    assert np.allclose(c[:, 0], fine[:, 0], rtol=0.006)


def test_first_arrivals_and_resonance():
    m = ([30.0, 0.0], [1500.0, 3000.0], [300.0, 1500.0], [1900.0, 2300.0])
    x = np.array([10.0, 20000.0])
    t = sw.first_arrival_times(m, x)
    assert t[0] == pytest.approx(10 / 1500)                  # direct wave near the source
    head = 20000 / 3000 + 2 * 30 * np.sqrt(1 / 1500 ** 2 - 1 / 3000 ** 2)
    assert t[1] == pytest.approx(head)
    assert sw.vertical_resonance_hz(m, 'S') == pytest.approx(300 / 120)


def test_backends_agree():
    pytest.importorskip("disba")
    m = ([25.0, 150.0, 0.0], [1600.0, 1900.0, 2850.0], [220.0, 550.0, 1500.0], [1800.0, 1950.0, 2250.0])
    f = np.geomspace(0.5, 15, 12)
    a = sw.rayleigh_phase(m, f, nmodes=2, backend="disba")
    b = sw.rayleigh_phase(m, f, nmodes=2, backend="thinlayer")
    ok = np.isfinite(a) & np.isfinite(b)
    assert np.allclose(a[ok], b[ok], rtol=0.015)
    ga = sw.rayleigh_group(m, f, backend="disba").ravel()
    gb = sw.rayleigh_group(m, f, backend="thinlayer").ravel()
    assert np.nanmax(np.abs(gb / ga - 1)) < 0.05


def test_love_and_ellipticity():
    pytest.importorskip("disba")
    m = ([20.0, 0.0], [600.0, 2000.0], [300.0, 1000.0], [1800.0, 2100.0])
    f = np.array([0.5, 4.0, 32.0])
    L = sw.love_group(m, f).ravel()
    assert L[0] == pytest.approx(1000.0, rel=0.02)          # low f: half-space Vs
    assert L[2] == pytest.approx(300.0, rel=0.02)           # high f: layer Vs
    e = sw.rayleigh_ellipticity(([100.0, 0.0], [1732.05, 1732.05], [1000.0, 1000.0], [2000.0, 2000.0]), [1.0])
    assert e[0] == pytest.approx(0.6812, rel=0.01)          # Poisson half-space H/V
