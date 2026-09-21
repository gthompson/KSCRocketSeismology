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
) -> pd.DataFrame:
    """Measure local-baseline-corrected pressure extrema and reduced pressure."""
    if reference_distance_m <= 0:
        raise ValueError("reference_distance_m must be positive")
    if baseline_end_s <= baseline_start_s:
        raise ValueError("baseline_end_s must exceed baseline_start_s")
    if signal_start_s is None:
        signal_start_s = baseline_end_s

    rows = []
    for tr in st_event:
        channel = str(tr.stats.channel).upper()
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
    summary_cols = [
        "distance_m", "baseline_pa", "positive_peak_pa", "negative_peak_pa",
        "peak_to_peak_pa", "positive_reduced_pa", "negative_reduced_pa",
        "peak_to_peak_reduced_pa",
    ]
    summary = {
        "event": event_name,
        "id": "ARRAY_MEDIAN",
        "channel": "MEDIAN",
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
    event_stream = Stream(
        [tr for tr in event_stream if tr.stats.channel.upper() in sensor_distances_m]
    )
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
