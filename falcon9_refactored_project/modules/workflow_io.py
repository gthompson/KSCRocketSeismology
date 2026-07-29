
"""Small reusable I/O and provenance helpers for the Falcon 9 workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Any
import json
from datetime import datetime, timezone

import numpy as np
from obspy import Stream


def robust_scale(data, percentile: float = 99.5) -> float:
    values = np.asarray(data, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return 1.0
    scale = np.percentile(np.abs(values), percentile)
    return float(scale) if np.isfinite(scale) and scale > 0 else 1.0


def order_stream(stream: Stream, channel_order: Iterable[str]) -> Stream:
    ordered = Stream()
    for channel in channel_order:
        matches = stream.select(channel=str(channel))
        if len(matches):
            ordered += matches[0].copy()
    return ordered


def trace_time_array_datetime64(trace):
    start = np.datetime64(trace.stats.starttime.datetime)
    dt_ns = int(round(trace.stats.delta * 1e9))
    return start + np.arange(trace.stats.npts) * np.timedelta64(dt_ns, "ns")


def write_provenance(
    path: str | Path,
    *,
    notebook: str,
    inputs: Mapping[str, Any],
    parameters: Mapping[str, Any],
    outputs: Mapping[str, Any],
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "notebook": notebook,
        "inputs": {key: str(value) for key, value in inputs.items()},
        "parameters": dict(parameters),
        "outputs": {key: str(value) for key, value in outputs.items()},
    }

    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return target
