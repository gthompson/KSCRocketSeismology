"""Clipping found by comparison with an unclipped, co-located reference sensor.

A clipped sensor (e.g. B20's Chaparral M25 at 1 Vpp) departs from a co-located,
unclipped one (B20's infraBSU) exactly where it clips. `fit_reference_gain` finds the
scale between the two where both are well recorded but small (e.g. the coda after a
shock); `reference_clip_intervals` then flags the samples where the sensor departs
from the scaled reference by more than `nsigma` times the misfit in that window, and
merges them into intervals. Raw-count saturation (`count_saturation_intervals`) gives
an independent check when the digitizer, rather than the sensor, limits the signal.
"""
from __future__ import annotations

import numpy as np


def _common(tr, ref, starttime=None, endtime=None):
    a, b = tr.copy(), ref.copy()
    if a.stats.sampling_rate != b.stats.sampling_rate:
        b.resample(a.stats.sampling_rate)
    t0 = max(a.stats.starttime, b.stats.starttime, starttime or a.stats.starttime)
    t1 = min(a.stats.endtime, b.stats.endtime, endtime or a.stats.endtime)
    a.trim(t0, t1, nearest_sample=True)
    b.trim(t0, t1, nearest_sample=True)
    n = min(len(a.data), len(b.data))
    return a.data[:n].astype(float), b.data[:n].astype(float), t0, a.stats.sampling_rate


def fit_reference_gain(tr, ref, starttime, endtime, max_lag_s=0.05):
    """Least-squares gain g (tr ~ g * ref) and lag (s, ref later than tr if positive) in a window.

    Returns (gain, lag_s, correlation).
    """
    a, b, _, fs = _common(tr, ref, starttime, endtime)
    a, b = a - a.mean(), b - b.mean()
    nl = int(round(max_lag_s * fs))
    best = (0, -np.inf)
    for k in range(-nl, nl + 1):
        bb = np.roll(b, k)
        r = np.dot(a, bb) / np.sqrt(np.dot(a, a) * np.dot(bb, bb))
        if r > best[1]:
            best = (k, r)
    bb = np.roll(b, best[0])
    return float(np.dot(a, bb) / np.dot(bb, bb)), best[0] / fs, float(best[1])


def reference_clip_intervals(tr, ref, gain, fit_window, starttime=None, endtime=None, lag_s=0.0,
                             nsigma=8.0, min_gap_s=0.05):
    """Intervals [(t_start, t_end), ...] where `tr` departs from `gain * ref` beyond `nsigma` x misfit.

    The misfit scale is the rms residual inside `fit_window` (start, end); search is limited to
    starttime..endtime. Both traces should be in the same units and band.
    """
    from obspy import UTCDateTime
    a, b, t0, fs = _common(tr, ref, starttime, endtime)
    k = int(round(lag_s * fs))
    resid = a - gain * np.roll(b, k)
    t = np.arange(len(a)) / fs
    w = (t >= float(UTCDateTime(fit_window[0]) - t0)) & (t <= float(UTCDateTime(fit_window[1]) - t0))
    sig = np.sqrt(np.mean((resid[w] - resid[w].mean()) ** 2)) if w.any() else np.std(resid)
    bad = np.abs(resid - (resid[w].mean() if w.any() else 0.0)) > nsigma * sig
    return _intervals(bad, t0, fs, min_gap_s)


def count_saturation_intervals(raw_tr, frac=0.98, full_scale=None, min_gap_s=0.05):
    """Intervals where raw counts reach `frac` of full scale (default: the trace's own max |counts|)."""
    x = raw_tr.data.astype(float)
    fsc = full_scale if full_scale is not None else np.abs(x).max()
    return _intervals(np.abs(x) >= frac * fsc, raw_tr.stats.starttime, raw_tr.stats.sampling_rate, min_gap_s)


def _intervals(mask, t0, fs, min_gap_s):
    idx = np.flatnonzero(mask)
    if not len(idx):
        return []
    gap = int(round(min_gap_s * fs))
    out, s, p = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - p > gap:
            out.append((t0 + s / fs, t0 + (p + 1) / fs))
            s = i
        p = i
    out.append((t0 + s / fs, t0 + (p + 1) / fs))
    return out
