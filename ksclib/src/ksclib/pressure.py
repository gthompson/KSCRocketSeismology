"""Baseline-corrected pressure extrema and distance-reduced pressures.

Copied from the AMOS-6 paper (amos6_paper/modules/event_measurements.py, Zenodo release)
and generalised: traces are matched to distances by channel (AMOS-6's single array),
station or full SEED id (`key`), and `event_reduced_pressures` takes distances from a
ksclib Event's station table with times measured from the origin time.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd
from obspy import Stream, UTCDateTime


def measure_reduced_pressures(
    st_event: Stream,
    sensor_distances_m: Mapping[str, float],
    *,
    reference_distance_m: float = 1000.0,
    event_name: str | None = None,
    baseline_start_s: float = 0.0,
    baseline_end_s: float = 0.75,
    signal_start_s: float | None = None,
    signal_end_s: float | None = None,
    key: str = "channel",
) -> pd.DataFrame:
    """Measure local-baseline-corrected pressure extrema and reduced pressure.

    Times are seconds from each trace's start. `sensor_distances_m` maps the trace's
    `key` ("channel", "station" or "id") to its source distance; reduced pressure is
    pressure * distance / reference_distance_m (spherical spreading).
    """
    keyof = {"channel": lambda tr: str(tr.stats.channel).upper(),
             "station": lambda tr: tr.stats.station,
             "id": lambda tr: tr.id}[key]
    if reference_distance_m <= 0:
        raise ValueError("reference_distance_m must be positive")
    if baseline_end_s <= baseline_start_s:
        raise ValueError("baseline_end_s must exceed baseline_start_s")
    if signal_start_s is None:
        signal_start_s = baseline_end_s

    rows = []
    for tr in st_event:
        channel = keyof(tr)
        if channel not in sensor_distances_m:
            continue

        data = np.asarray(tr.data, dtype=float)
        times = tr.times()
        finite = np.isfinite(data)

        baseline_mask = (
            finite
            & (times >= baseline_start_s)
            & (times < baseline_end_s)
        )
        if not baseline_mask.any():
            raise ValueError(
                f"{tr.id}: no samples in baseline interval "
                f"{baseline_start_s}–{baseline_end_s} s"
            )

        baseline_pa = float(np.nanmedian(data[baseline_mask]))
        corrected = data - baseline_pa

        signal_mask = finite & (times >= signal_start_s)
        if signal_end_s is not None:
            signal_mask &= times <= signal_end_s
        if not signal_mask.any():
            raise ValueError(f"{tr.id}: no samples in requested signal interval")

        y = corrected[signal_mask]
        t = times[signal_mask]
        ipos = int(np.nanargmax(y))
        ineg = int(np.nanargmin(y))
        positive = float(y[ipos])
        negative = float(y[ineg])
        p2p = positive - negative

        distance_m = float(sensor_distances_m[channel])
        factor = distance_m / reference_distance_m

        rows.append(
            {
                "event": event_name,
                "id": tr.id,
                "channel": channel,
                "distance_m": distance_m,
                "baseline_pa": baseline_pa,
                "positive_peak_time_s": float(t[ipos]),
                "negative_peak_time_s": float(t[ineg]),
                "positive_peak_pa": positive,
                "negative_peak_pa": negative,
                "peak_to_peak_pa": p2p,
                "positive_reduced_pa": positive * factor,
                "negative_reduced_pa": negative * factor,
                "peak_to_peak_reduced_pa": p2p * factor,
            }
        )

    if not rows:
        raise ValueError("No pressure traces matched sensor_distances_m")

    result = pd.DataFrame(rows).sort_values("channel").reset_index(drop=True)
    if key != "channel":
        result = result.rename(columns={"channel": key})
        result.insert(2, "channel", [i.split(".")[-1] for i in result["id"]])
    summary_cols = [
        "distance_m", "baseline_pa", "positive_peak_pa", "negative_peak_pa",
        "peak_to_peak_pa", "positive_reduced_pa", "negative_reduced_pa",
        "peak_to_peak_reduced_pa",
    ]
    summary = {
        "event": event_name,
        "id": "ARRAY_MEDIAN",
        key: "MEDIAN",
        "positive_peak_time_s": np.nan,
        "negative_peak_time_s": np.nan,
    }
    for col in summary_cols:
        summary[col] = float(result[col].median())

    return pd.concat([result, pd.DataFrame([summary])], ignore_index=True)


def measure_reduced_pressures_in_window(
    stream: Stream,
    starttime: UTCDateTime | str,
    endtime: UTCDateTime | str,
    sensor_distances_m: Mapping[str, float],
    **kwargs,
) -> tuple[Stream, pd.DataFrame]:
    """Trim a longer stream and call measure_reduced_pressures."""
    t0, t1 = UTCDateTime(starttime), UTCDateTime(endtime)
    if t1 <= t0:
        raise ValueError("endtime must follow starttime")
    event_stream = stream.copy().trim(t0, t1, pad=False)
    key = kwargs.get("key", "channel")
    keyof = {"channel": lambda tr: tr.stats.channel.upper(), "station": lambda tr: tr.stats.station,
             "id": lambda tr: tr.id}[key]
    event_stream = Stream([tr for tr in event_stream if keyof(tr) in sensor_distances_m])
    results = measure_reduced_pressures(
        event_stream,
        sensor_distances_m,
        **kwargs,
    )
    return event_stream, results


def pressure_results_for_paper(results: pd.DataFrame) -> pd.DataFrame:
    """Return a compact publication-oriented pressure table."""
    columns = [
        "event", "channel", "distance_m", "positive_peak_pa",
        "negative_peak_pa", "peak_to_peak_pa", "positive_reduced_pa",
        "negative_reduced_pa", "peak_to_peak_reduced_pa",
    ]
    out = results.loc[:, columns].copy()
    out["distance_m"] = out["distance_m"].round(1)
    pressure_cols = [c for c in out.columns if c.endswith("_pa")]
    out[pressure_cols] = out[pressure_cols].round(1)
    return out


def event_reduced_pressures(stream: Stream, event, *, stations=None, baseline=(-20.0, -1.0),
                            signal=None, reference_distance_m: float = 1000.0) -> pd.DataFrame:
    """Reduced pressures for each pressure trace, with distances from the event site.

    `baseline` and `signal` are (start, end) in seconds after the origin time; `signal`
    defaults to the baseline end through the end of the trace. Peak times in the result
    are seconds after the origin time.
    """
    from .geometry import station_table
    tab = stations if stations is not None else station_table(event)
    dist = {s: float(d) * 1000.0 for s, d in tab["distance_km"].items()}
    st = Stream([tr for tr in stream if tr.stats.station in dist]).copy()
    t0 = event.origin_time + baseline[0]
    st.trim(starttime=t0)
    off = lambda tr: float(tr.stats.starttime - event.origin_time)  # noqa: E731
    frames = []
    for tr in st:
        o = off(tr)
        res = measure_reduced_pressures(
            Stream([tr]), dist, reference_distance_m=reference_distance_m, event_name=event.name,
            baseline_start_s=baseline[0] - o, baseline_end_s=baseline[1] - o,
            signal_start_s=(signal[0] if signal else baseline[1]) - o,
            signal_end_s=(signal[1] - o) if signal else None, key="station")
        res = res.iloc[:-1].copy()       # drop the one-trace median row
        res[["positive_peak_time_s", "negative_peak_time_s"]] += o
        frames.append(res)
    return pd.concat(frames, ignore_index=True).sort_values("distance_m").reset_index(drop=True)
