from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from obspy import Stream
from scipy.signal import correlate, correlation_lags


@dataclass
class PairwiseLag:
    channel_i: str
    channel_j: str
    lag_s: float
    correlation: float


def _demean_normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    x = x - np.nanmean(x)
    scale = np.sqrt(np.nansum(x * x))
    if not np.isfinite(scale) or scale == 0:
        raise ValueError("Cannot normalize a zero-energy waveform")
    return x / scale


def _parabolic_peak(y: np.ndarray, index: int) -> float:
    """Return a sub-sample correction around a discrete correlation peak."""
    if index <= 0 or index >= len(y) - 1:
        return 0.0
    ym1, y0, yp1 = y[index - 1], y[index], y[index + 1]
    denom = ym1 - 2.0 * y0 + yp1
    if denom == 0:
        return 0.0
    return 0.5 * (ym1 - yp1) / denom


def pairwise_cross_correlations(
    stream: Stream,
    *,
    channels: Sequence[str] = ("HD1", "HD2", "HD3"),
    max_lag_s: float = 0.15,
    use_absolute_peak: bool = False,
    subsample: bool = True,
) -> pd.DataFrame:
    """Measure normalized pairwise lags among three array channels."""
    traces = {}
    for channel in channels:
        matches = stream.select(channel=channel)
        if len(matches) != 1:
            raise ValueError(f"Expected one {channel} trace; found {len(matches)}")
        traces[channel] = matches[0]

    sampling_rates = {float(tr.stats.sampling_rate) for tr in traces.values()}
    if len(sampling_rates) != 1:
        raise ValueError("All traces must have the same sampling rate")
    fs = sampling_rates.pop()
    max_lag_samples = int(round(max_lag_s * fs))

    rows = []
    for i, chi in enumerate(channels):
        for chj in channels[i + 1:]:
            xi = _demean_normalize(traces[chi].data)
            xj = _demean_normalize(traces[chj].data)
            n = min(len(xi), len(xj))
            xi, xj = xi[:n], xj[:n]

            cc = correlate(xj, xi, mode="full", method="fft")
            lags = correlation_lags(len(xj), len(xi), mode="full")
            keep = np.abs(lags) <= max_lag_samples
            cc, lags = cc[keep], lags[keep]

            score = np.abs(cc) if use_absolute_peak else cc
            index = int(np.nanargmax(score))
            correction = _parabolic_peak(score, index) if subsample else 0.0
            lag_samples = float(lags[index]) + correction
            lag_s = lag_samples / fs

            rows.append(
                {
                    "channel_i": chi,
                    "channel_j": chj,
                    "lag_s": lag_s,
                    "correlation": float(cc[index]),
                    "abs_correlation": float(abs(cc[index])),
                }
            )
    return pd.DataFrame(rows)


def fit_plane_wave(
    pairwise_lags: pd.DataFrame,
    coordinates_m: Mapping[str, tuple[float, float]],
) -> dict:
    """Fit east/north horizontal slowness from pairwise delays."""
    a_rows, b, weights = [], [], []
    for row in pairwise_lags.itertuples(index=False):
        xi, yi = coordinates_m[row.channel_i]
        xj, yj = coordinates_m[row.channel_j]
        # lag = t_j - t_i = s dot (x_j - x_i)
        a_rows.append([xj - xi, yj - yi])
        b.append(row.lag_s)
        weights.append(max(row.abs_correlation, 1e-6) ** 2)

    A = np.asarray(a_rows, dtype=float)
    b = np.asarray(b, dtype=float)
    W = np.diag(np.asarray(weights, dtype=float))
    slowness = np.linalg.solve(A.T @ W @ A, A.T @ W @ b)
    sx, sy = slowness
    norm = float(np.hypot(sx, sy))
    speed = np.inf if norm == 0 else 1.0 / norm

    # Propagation direction points toward the array; back azimuth points to source.
    propagation_azimuth = (np.degrees(np.arctan2(sx, sy)) + 360.0) % 360.0
    back_azimuth = (propagation_azimuth + 180.0) % 360.0

    predicted = A @ slowness
    residuals = b - predicted
    return {
        "slowness_east_s_per_m": float(sx),
        "slowness_north_s_per_m": float(sy),
        "apparent_speed_mps": float(speed),
        "propagation_azimuth_deg": float(propagation_azimuth),
        "back_azimuth_deg": float(back_azimuth),
        "rms_lag_residual_s": float(np.sqrt(np.mean(residuals ** 2))),
        "observed_lags_s": b,
        "predicted_lags_s": predicted,
        "residuals_s": residuals,
    }


def fit_spherical_speed_fixed_source(
    pairwise_lags: pd.DataFrame,
    sensor_coordinates_m: Mapping[str, tuple[float, float]],
    source_xy_m: tuple[float, float],
) -> dict:
    """Fit effective speed for a spherical wave from a fixed source."""
    xs, ys = source_xy_m
    ranges = {
        channel: float(np.hypot(x - xs, y - ys))
        for channel, (x, y) in sensor_coordinates_m.items()
    }

    dr, dt, weights = [], [], []
    for row in pairwise_lags.itertuples(index=False):
        # lag = t_j - t_i = (r_j-r_i)/c
        dr.append(ranges[row.channel_j] - ranges[row.channel_i])
        dt.append(row.lag_s)
        weights.append(max(row.abs_correlation, 1e-6) ** 2)

    dr = np.asarray(dr)
    dt = np.asarray(dt)
    w = np.asarray(weights)
    # Fit slowness q=1/c through the origin.
    q = float(np.sum(w * dr * dt) / np.sum(w * dr * dr))
    speed = np.inf if q == 0 else abs(1.0 / q)
    predicted = dr * q
    residuals = dt - predicted
    return {
        "effective_speed_mps": float(speed),
        "signed_slowness_s_per_m": q,
        "ranges_m": ranges,
        "rms_lag_residual_s": float(np.sqrt(np.mean(residuals ** 2))),
        "observed_lags_s": dt,
        "predicted_lags_s": predicted,
        "residuals_s": residuals,
    }


def analyze_array_event(
    stream: Stream,
    sensor_coordinates_m: Mapping[str, tuple[float, float]],
    *,
    channels: Sequence[str] = ("HD1", "HD2", "HD3"),
    max_lag_s: float = 0.15,
    fixed_source_xy_m: tuple[float, float] | None = None,
) -> dict:
    """Run pairwise correlation, plane-wave fit, and optional spherical fit."""
    lags = pairwise_cross_correlations(
        stream,
        channels=channels,
        max_lag_s=max_lag_s,
        subsample=True,
    )
    result = {
        "pairwise_lags": lags,
        "plane_wave": fit_plane_wave(lags, sensor_coordinates_m),
    }
    if fixed_source_xy_m is not None:
        result["spherical_fixed_source"] = fit_spherical_speed_fixed_source(
            lags,
            sensor_coordinates_m,
            fixed_source_xy_m,
        )
    return result
