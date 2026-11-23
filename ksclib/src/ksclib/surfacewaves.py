"""Rayleigh-wave dispersion and refraction travel times for flat layered models.

Dispersion uses the thin-layer method (Lysmer 1970; Kausel 2005): each layer is split into
sublayers with linear displacement interpolation (mass matrix averaged between consistent
and lumped, which makes the discretisation error fourth order), the column rests on a rigid base deep
enough to be invisible to the frequencies studied, and at each frequency the Rayleigh
wavenumbers are the eigenvalues of

    (A k^2 + B k + G - w^2 M) phi = 0,

solved as a linear generalised eigenproblem. Modes are returned slowest first (mode 0 is the
fundamental). Group velocity is dw/dk by finite differences in frequency.

Models are given as arrays (thickness_m, vp, vs, rho) in m, m/s, kg/m^3; the last row is the
half-space (its thickness is ignored).

If `disba` (Luu 2021, fast delta-matrix root finding) is installed it is used by default
(`backend="auto"`); otherwise the thin-layer method, which needs only numpy and scipy. The two
agree to within 1% at the default nper=30 (tests/test_surfacewaves.py); at nper=10 the thin-layer
method can be 10% off where a thin, slow top layer meets strong contrasts.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import eig


def _discretise(thick, vp, vs, rho, f, nper=10, depth_factor=3.0):
    """Sublayers for frequency f, in identical pairs (so merging pairs halves the resolution):
    <= 1/nper of the local S wavelength in the layers and to 1.5 wavelengths depth, then
    growing, down to depth_factor times the longest wavelength (half-space Vs)."""
    lam_max = vs[-1] / f
    zmax = max(np.sum(thick[:-1]) + lam_max, depth_factor * lam_max)
    hs, props = [], []
    z = 0.0
    for i in range(len(vs)):
        H = thick[i] if i < len(vs) - 1 else max(zmax - z, 0.0)
        if H <= 0:
            continue
        lam = vs[i] / f
        if i == len(vs) - 1:
            dz, zz = lam / nper, 0.0
            while zz < H:
                hs += [dz, dz]; props += [i, i]; zz += 2 * dz
                if z + zz > 1.5 * lam_max:
                    dz = min(dz * 1.15, lam / 3)
        else:
            n = 2 * max(1, int(np.ceil(H / (2 * lam / nper))))
            hs += [H / n] * n; props += [i] * n
        z += H
    return np.array(hs), np.array(props)


def _solve(h, idx, vp, vs, rho, f, nmodes):
    A, B, G, M = _matrices(h, idx, vp, vs, rho)
    w = 2 * np.pi * f
    N = A.shape[0]
    I, Z = np.eye(N), np.zeros((N, N))
    k = eig(np.block([[Z, I], [-(G - w ** 2 * M), -B]]), np.block([[I, Z], [Z, A]]), right=False)
    k = k[np.isfinite(k)]
    k = k[(np.abs(k.imag) < 1e-6 * np.abs(k.real) + 1e-12) & (k.real > 0)].real
    c = np.sort(w / k)
    c = c[c < vs[-1] * 0.999]          # trapped modes only (slower than the half-space S wave)
    out = np.full(nmodes, np.nan)
    out[:min(nmodes, len(c))] = c[:nmodes]
    return out


def _matrices(h, idx, vp, vs, rho):
    n = len(h) + 1
    A = np.zeros((2 * n, 2 * n)); B = np.zeros_like(A); G = np.zeros_like(A); M = np.zeros_like(A)
    for j, (hj, i) in enumerate(zip(h, idx)):
        mu = rho[i] * vs[i] ** 2
        lam = rho[i] * vp[i] ** 2 - 2 * mu
        l2m = lam + 2 * mu
        a = hj / 6 * np.array([[2 * l2m, 0, l2m, 0], [0, 2 * mu, 0, mu], [l2m, 0, 2 * l2m, 0], [0, mu, 0, 2 * mu]])
        b = 0.5 * np.array([[0, -(lam - mu), 0, lam + mu], [-(lam - mu), 0, -(lam + mu), 0],
                            [0, -(lam + mu), 0, lam - mu], [lam + mu, 0, lam - mu, 0]])
        g = 1 / hj * np.array([[mu, 0, -mu, 0], [0, l2m, 0, -l2m], [-mu, 0, mu, 0], [0, -l2m, 0, l2m]])
        # average of consistent and lumped mass: cancels the leading O((h/lambda)^2) error
        m = 0.5 * rho[i] * hj / 6 * np.array([[2, 0, 1, 0], [0, 2, 0, 1], [1, 0, 2, 0], [0, 1, 0, 2]]) \
            + 0.5 * rho[i] * hj / 2 * np.eye(4)
        s = slice(2 * j, 2 * j + 4)
        A[s, s] += a; B[s, s] += b; G[s, s] += g; M[s, s] += m
    keep = np.arange(2 * n - 2)       # rigid base: drop the last node
    return (X[np.ix_(keep, keep)] for X in (A, B, G, M))


try:
    import disba as _disba
except ImportError:          # optional dependency
    _disba = None


def _disba_curve(model, freqs, nmodes, kind):
    thick, vp, vs, rho = (np.asarray(x, float) / 1000 for x in model)
    f = np.atleast_1d(np.asarray(freqs, float))
    T = np.sort(1 / f)
    cls = _disba.PhaseDispersion if kind == "phase" else _disba.GroupDispersion
    D = cls(thick, vp, vs, rho)
    out = np.full((len(f), nmodes), np.nan)
    for k in range(nmodes):
        try:
            r = D(T, mode=k, wave="rayleigh")
        except Exception:
            continue
        v = dict(zip(np.round(r.period, 10), r.velocity * 1000))
        out[:, k] = [v.get(np.round(1 / fi, 10), np.nan) for fi in f]
    return out


def _use_disba(backend):
    if backend == "disba" and _disba is None:
        raise ImportError("disba is not installed")
    return backend == "disba" or (backend == "auto" and _disba is not None)


def rayleigh_phase(model, freqs, nmodes=1, nper=30, richardson=True, backend="auto"):
    """Rayleigh phase velocities (m/s), shape (len(freqs), nmodes), NaN where a mode is absent.

    backend: "auto" (disba if installed), "disba" or "thinlayer".

    The discretisation error is second order in sublayer thickness; with `richardson` the
    result is extrapolated from the mesh and the same mesh with pairs of sublayers merged,
    (4 c_fine - c_coarse) / 3.
    """
    if _use_disba(backend):
        return _disba_curve(model, freqs, nmodes, "phase")
    thick, vp, vs, rho = (np.asarray(x, float) for x in model)
    freqs = np.atleast_1d(np.asarray(freqs, float))
    out = np.full((len(freqs), nmodes), np.nan)
    for q, f in enumerate(freqs):
        h, idx = _discretise(thick, vp, vs, rho, f, nper=nper)
        c = _solve(h, idx, vp, vs, rho, f, nmodes)
        if richardson:
            cc = _solve(h[0::2] + h[1::2], idx[0::2], vp, vs, rho, f, nmodes)
            c = (4 * c - cc) / 3
        out[q] = c
    return out


def rayleigh_group(model, freqs, nmodes=1, nper=30, df_frac=0.02, richardson=True, backend="auto"):
    """Rayleigh group velocities (m/s): disba's group velocity, or U = dw/dk with a centred
    difference of +/- df_frac in the thin-layer method."""
    if _use_disba(backend):
        return _disba_curve(model, freqs, nmodes, "group")
    f = np.asarray(freqs, float)
    c1 = rayleigh_phase(model, f * (1 - df_frac), nmodes, nper, richardson, "thinlayer")
    c2 = rayleigh_phase(model, f * (1 + df_frac), nmodes, nper, richardson, "thinlayer")
    k1 = 2 * np.pi * (f * (1 - df_frac))[:, None] / c1
    k2 = 2 * np.pi * (f * (1 + df_frac))[:, None] / c2
    return 2 * np.pi * (2 * df_frac * f)[:, None] / (k2 - k1)


def first_arrival_times(model, x_m, wave="P"):
    """First-arrival time (s) at offsets x_m for a surface source: the direct wave in layer 1 or
    the earliest head wave along the top of any faster layer below (flat layers)."""
    thick, vp, vs, rho = (np.asarray(m, float) for m in model)
    v = vp if wave == "P" else vs
    x = np.atleast_1d(np.asarray(x_m, float))
    t = x / v[0]
    for n in range(1, len(v)):
        if np.any(v[:n] >= v[n]):
            continue
        tn = x / v[n] + 2 * np.sum(thick[:n] * np.sqrt(1 / v[:n] ** 2 - 1 / v[n] ** 2))
        t = np.minimum(t, tn)
    return t


def vertical_resonance_hz(model, wave="P"):
    """Quarter-wavelength resonance of the layers above the half-space: 1 / (4 sum(h/v))."""
    thick, vp, vs, rho = (np.asarray(m, float) for m in model)
    v = vp if wave == "P" else vs
    return 1.0 / (4 * np.sum(thick[:-1] / v[:-1]))
