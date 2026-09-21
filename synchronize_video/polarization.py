"""
polarization.py

Three-component seismogram rotation and sliding-window polarization attributes.

Core dependencies:
    numpy
    scipy
    obspy

Optional:
    twistpy   # preferred for complex-signal ellipticity

Coordinate convention used here:
    Z = positive up
    N = north
    E = east
    R = radial, positive away from source for ObsPy's NE->RT convention
    T = transverse
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from obspy import Stream, Trace
from obspy.signal.rotate import rotate_ne_rt, rotate_zne_lqt


@dataclass
class PolarizationSeries:
    """Sliding-window polarization attributes."""
    time_s: np.ndarray
    linearity: np.ndarray
    rectilinearity: np.ndarray
    planarity: np.ndarray
    azimuth_deg: np.ndarray
    incidence_deg: np.ndarray
    lambda1: np.ndarray
    lambda2: np.ndarray
    lambda3: np.ndarray


def _validate_equal_length(*arrays: np.ndarray) -> None:
    lengths = {len(np.asarray(a)) for a in arrays}
    if len(lengths) != 1:
        raise ValueError(f"Component lengths differ: {sorted(lengths)}")


def rotate_zne_to_rt(
    n: np.ndarray,
    e: np.ndarray,
    back_azimuth_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Rotate horizontal North/East components to Radial/Transverse.

    Uses ObsPy's rotate_ne_rt(), so the convention is exactly ObsPy's.
    """
    _validate_equal_length(n, e)
    r, t = rotate_ne_rt(
        np.asarray(n, dtype=float),
        np.asarray(e, dtype=float),
        back_azimuth_deg,
    )
    return r, t


def rotate_zne_to_lqt(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    back_azimuth_deg: float,
    incidence_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Rotate Z/N/E into ray coordinates L/Q/T using ObsPy.
    """
    _validate_equal_length(z, n, e)
    l, q, t = rotate_zne_lqt(
        np.asarray(z, dtype=float),
        np.asarray(n, dtype=float),
        np.asarray(e, dtype=float),
        back_azimuth_deg,
        incidence_deg,
    )
    return l, q, t


def rotate_stream_to_zne(st: Stream, inventory) -> Stream:
    """
    Rotate a 3-C ObsPy Stream to Z/N/E using StationXML metadata.

    Handles common Z12 / 123 component naming via Stream.rotate().
    """
    out = st.copy()
    out.rotate(method="->ZNE", inventory=inventory)
    return out


def rotate_stream_ne_rt(st: Stream, back_azimuth_deg: float) -> Stream:
    """
    Rotate an already-ZNE ObsPy Stream to Z/R/T.
    """
    out = st.copy()
    out.rotate(method="NE->RT", back_azimuth=back_azimuth_deg)
    return out


def _principal_axis_az_inc(v1_zne: np.ndarray) -> tuple[float, float]:
    """
    Convert a principal eigenvector in [Z, N, E] coordinates to
    azimuth (clockwise from north) and incidence (0=vertical).

    Axis polarity is intrinsically ambiguous, so azimuth is folded to [0, 180).
    """
    z, n, e = v1_zne

    # Choose a consistent hemisphere to avoid arbitrary eigenvector sign flips.
    if z < 0:
        z, n, e = -z, -n, -e

    horizontal = np.hypot(n, e)
    incidence = np.degrees(np.arctan2(horizontal, abs(z)))
    azimuth = np.degrees(np.arctan2(e, n)) % 360.0
    azimuth = azimuth % 180.0
    return azimuth, incidence


def covariance_polarization_series(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    sampling_rate: float,
    window_seconds: float = 0.5,
    step_seconds: Optional[float] = None,
    demean: bool = True,
) -> PolarizationSeries:
    """
    Compute classic real-covariance 3-C polarization attributes in sliding windows.

    Eigenvalues are sorted lambda1 >= lambda2 >= lambda3 >= 0.

    Definitions:
        linearity      = (lambda1 - lambda2) / lambda1
        rectilinearity = 1 - (lambda2 + lambda3) / (2 lambda1)
        planarity      = (lambda2 - lambda3) / lambda1

    These are deliberately explicit because polarization literature/packages use
    several related definitions. They should not be silently equated with the
    complex-signal ellipticity returned by TwistPy.

    Returns one value per window center.
    """
    z = np.asarray(z, dtype=float)
    n = np.asarray(n, dtype=float)
    e = np.asarray(e, dtype=float)
    _validate_equal_length(z, n, e)

    if sampling_rate <= 0:
        raise ValueError("sampling_rate must be positive")
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")

    if step_seconds is None:
        step_seconds = 1.0 / sampling_rate

    nwin = max(3, int(round(window_seconds * sampling_rate)))
    nstep = max(1, int(round(step_seconds * sampling_rate)))

    centers = []
    lin = []
    rect = []
    plan = []
    az = []
    inc = []
    l1s = []
    l2s = []
    l3s = []

    x = np.column_stack([z, n, e])

    for i0 in range(0, len(x) - nwin + 1, nstep):
        xx = x[i0:i0 + nwin].copy()

        finite = np.isfinite(xx).all(axis=1)
        xx = xx[finite]
        if len(xx) < 3:
            vals = [np.nan] * 8
            center = (i0 + 0.5 * (nwin - 1)) / sampling_rate
            centers.append(center)
            lin.append(vals[0]); rect.append(vals[1]); plan.append(vals[2])
            az.append(vals[3]); inc.append(vals[4])
            l1s.append(vals[5]); l2s.append(vals[6]); l3s.append(vals[7])
            continue

        if demean:
            xx -= xx.mean(axis=0, keepdims=True)

        cov = np.cov(xx, rowvar=False, bias=False)
        evals, evecs = np.linalg.eigh(cov)
        order = np.argsort(evals)[::-1]
        evals = np.maximum(evals[order], 0.0)
        evecs = evecs[:, order]

        l1, l2, l3 = evals
        eps = np.finfo(float).eps

        if l1 <= eps:
            linearity = rectilinearity = planarity = np.nan
            azi = inci = np.nan
        else:
            linearity = (l1 - l2) / l1
            rectilinearity = 1.0 - (l2 + l3) / (2.0 * l1)
            planarity = (l2 - l3) / l1
            azi, inci = _principal_axis_az_inc(evecs[:, 0])

        centers.append((i0 + 0.5 * (nwin - 1)) / sampling_rate)
        lin.append(linearity)
        rect.append(rectilinearity)
        plan.append(planarity)
        az.append(azi)
        inc.append(inci)
        l1s.append(l1); l2s.append(l2); l3s.append(l3)

    return PolarizationSeries(
        time_s=np.asarray(centers),
        linearity=np.asarray(lin),
        rectilinearity=np.asarray(rect),
        planarity=np.asarray(plan),
        azimuth_deg=np.asarray(az),
        incidence_deg=np.asarray(inc),
        lambda1=np.asarray(l1s),
        lambda2=np.asarray(l2s),
        lambda3=np.asarray(l3s),
    )


def twistpy_ellipticity_series(
    z: Trace,
    n: Trace,
    e: Trace,
    window_seconds: float = 0.5,
    overlap: float = 1.0,
    timeaxis: str = "rel",
):
    """
    Compute TwistPy complex-signal polarization attributes.

    Returns the TwistPy TimeDomainAnalysis3C object so callers can access:
        analysis.t_windows
        analysis.elli
        analysis.dop
        analysis.inc1, analysis.inc2
        analysis.azi1, analysis.azi2

    TwistPy expects arguments in N, E, Z order.
    """
    try:
        from twistpy.polarization import TimeDomainAnalysis3C
    except ImportError as exc:
        raise ImportError(
            "TwistPy is not installed. Install it separately to compute "
            "complex-signal ellipticity."
        ) from exc

    analysis = TimeDomainAnalysis3C(
        N=n,
        E=e,
        Z=z,
        window={
            "window_length_seconds": float(window_seconds),
            "overlap": float(overlap),
        },
        timeaxis=timeaxis,
    )
    analysis.polarization_analysis()
    return analysis


def traces_from_zne(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    sampling_rate: float,
    starttime,
    network: str = "",
    station: str = "",
    location: str = "",
    band_code: str = "BH",
) -> Stream:
    """Convenience helper to package arrays as an ObsPy Z/N/E Stream."""
    _validate_equal_length(z, n, e)

    traces = []
    for comp, data in zip("ZNE", (z, n, e)):
        tr = Trace(np.asarray(data, dtype=np.float64))
        tr.stats.network = network
        tr.stats.station = station
        tr.stats.location = location
        tr.stats.channel = f"{band_code}{comp}"
        tr.stats.sampling_rate = sampling_rate
        tr.stats.starttime = starttime
        traces.append(tr)
    return Stream(traces)
