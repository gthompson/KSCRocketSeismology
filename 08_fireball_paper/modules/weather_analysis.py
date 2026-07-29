from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


KNOT_TO_MPS = 0.514444
FOOT_TO_M = 0.3048


@dataclass(frozen=True)
class WindSummary:
    """Vector and scalar summaries of a collection of wind observations."""

    n: int
    scalar_mean_speed_knots: float
    scalar_mean_speed_mps: float
    vector_mean_speed_knots: float
    vector_mean_speed_mps: float
    vector_mean_direction_from_deg: float
    mean_u_east_mps: float
    mean_v_north_mps: float


def load_ksc_weather_excel(
    filename: str | Path,
    *,
    sheet_name: int | str = 0,
) -> pd.DataFrame:
    """Load and normalize the KSC weather-tower spreadsheet."""
    filename = Path(filename)
    dataframe = pd.read_excel(filename, sheet_name=sheet_name)

    required = {
        "UTC Date",
        "UTC Time",
        "Tower Measurement Location",
        "Lat",
        "Lon",
        "Height",
        "Avg Wind Direction",
        "Avg Wind Speed",
        "Temp",
        "Relative Humidity",
    }
    missing = required.difference(dataframe.columns)
    if missing:
        raise KeyError(
            f"Weather spreadsheet is missing required columns: {sorted(missing)}"
        )

    out = dataframe.copy()

    date_text = pd.to_datetime(out["UTC Date"]).dt.strftime("%Y-%m-%d")
    time_text = out["UTC Time"].astype(str)
    out["datetime_utc"] = pd.to_datetime(
        date_text + " " + time_text,
        utc=True,
        errors="coerce",
    )

    if out["datetime_utc"].isna().any():
        bad = out.loc[out["datetime_utc"].isna(), ["UTC Date", "UTC Time"]]
        raise ValueError(
            "Could not parse some UTC date/time values:\n"
            f"{bad.head().to_string(index=False)}"
        )

    out["height_ft"] = pd.to_numeric(out["Height"], errors="coerce")
    out["height_m"] = out["height_ft"] * FOOT_TO_M

    out["wind_direction_from_deg"] = (
        pd.to_numeric(out["Avg Wind Direction"], errors="coerce") % 360.0
    )
    out["wind_speed_knots"] = pd.to_numeric(
        out["Avg Wind Speed"], errors="coerce"
    )
    out["wind_speed_mps"] = out["wind_speed_knots"] * KNOT_TO_MPS

    out["temperature_f"] = pd.to_numeric(out["Temp"], errors="coerce")
    out["temperature_c"] = (out["temperature_f"] - 32.0) * 5.0 / 9.0
    out["relative_humidity_percent"] = pd.to_numeric(
        out["Relative Humidity"], errors="coerce"
    )

    # Meteorological direction is the direction FROM which the wind blows.
    # u and v below describe the vector direction TOWARD which it blows.
    direction_rad = np.deg2rad(out["wind_direction_from_deg"])
    out["wind_u_east_mps"] = (
        -out["wind_speed_mps"] * np.sin(direction_rad)
    )
    out["wind_v_north_mps"] = (
        -out["wind_speed_mps"] * np.cos(direction_rad)
    )

    return out


def subset_time_window(
    dataframe: pd.DataFrame,
    starttime: str | pd.Timestamp,
    endtime: str | pd.Timestamp,
) -> pd.DataFrame:
    """Return observations within an inclusive UTC time window."""
    start = pd.Timestamp(starttime)
    end = pd.Timestamp(endtime)
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    else:
        start = start.tz_convert("UTC")
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    else:
        end = end.tz_convert("UTC")
    if end < start:
        raise ValueError("endtime must not precede starttime")

    return dataframe.loc[
        dataframe["datetime_utc"].between(start, end, inclusive="both")
    ].copy()


def wind_from_uv(
    u_east_mps: float | np.ndarray,
    v_north_mps: float | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert east/north wind components to speed and meteorological FROM direction.
    """
    u = np.asarray(u_east_mps, dtype=float)
    v = np.asarray(v_north_mps, dtype=float)
    speed = np.hypot(u, v)

    direction_to_deg = (
        np.degrees(np.arctan2(u, v)) + 360.0
    ) % 360.0
    direction_from_deg = (direction_to_deg + 180.0) % 360.0
    return speed, direction_from_deg


def summarize_wind(dataframe: pd.DataFrame) -> WindSummary:
    """Calculate scalar and vector means for average-wind observations."""
    valid = dataframe.dropna(
        subset=[
            "wind_speed_mps",
            "wind_u_east_mps",
            "wind_v_north_mps",
        ]
    )
    if valid.empty:
        raise ValueError("No valid wind observations")

    mean_u = float(valid["wind_u_east_mps"].mean())
    mean_v = float(valid["wind_v_north_mps"].mean())
    vector_speed_mps, vector_direction_from = wind_from_uv(mean_u, mean_v)

    return WindSummary(
        n=len(valid),
        scalar_mean_speed_knots=float(valid["wind_speed_knots"].mean()),
        scalar_mean_speed_mps=float(valid["wind_speed_mps"].mean()),
        vector_mean_speed_knots=float(vector_speed_mps / KNOT_TO_MPS),
        vector_mean_speed_mps=float(vector_speed_mps),
        vector_mean_direction_from_deg=float(vector_direction_from),
        mean_u_east_mps=mean_u,
        mean_v_north_mps=mean_v,
    )


def make_height_profile(
    dataframe: pd.DataFrame,
    *,
    height_bin_m: float = 10.0,
) -> pd.DataFrame:
    """
    Average weather observations in height bins using vector wind components.
    """
    if height_bin_m <= 0:
        raise ValueError("height_bin_m must be positive")

    work = dataframe.copy()
    work["height_bin_lower_m"] = (
        np.floor(work["height_m"] / height_bin_m) * height_bin_m
    )
    work["height_bin_upper_m"] = (
        work["height_bin_lower_m"] + height_bin_m
    )
    work["height_bin_mid_m"] = (
        work["height_bin_lower_m"] + 0.5 * height_bin_m
    )

    grouped = (
        work.groupby(
            [
                "height_bin_lower_m",
                "height_bin_upper_m",
                "height_bin_mid_m",
            ],
            observed=True,
        )
        .agg(
            n_wind=("wind_speed_mps", "count"),
            mean_height_m=("height_m", "mean"),
            mean_u_east_mps=("wind_u_east_mps", "mean"),
            mean_v_north_mps=("wind_v_north_mps", "mean"),
            scalar_mean_wind_speed_mps=("wind_speed_mps", "mean"),
            scalar_std_wind_speed_mps=("wind_speed_mps", "std"),
            mean_temperature_c=("temperature_c", "mean"),
            std_temperature_c=("temperature_c", "std"),
            n_temperature=("temperature_c", "count"),
            mean_relative_humidity_percent=(
                "relative_humidity_percent",
                "mean",
            ),
            std_relative_humidity_percent=(
                "relative_humidity_percent",
                "std",
            ),
            n_humidity=("relative_humidity_percent", "count"),
        )
        .reset_index()
        .sort_values("height_bin_mid_m")
    )

    vector_speed, vector_direction_from = wind_from_uv(
        grouped["mean_u_east_mps"].to_numpy(),
        grouped["mean_v_north_mps"].to_numpy(),
    )
    grouped["vector_mean_wind_speed_mps"] = vector_speed
    grouped["vector_mean_wind_speed_knots"] = vector_speed / KNOT_TO_MPS
    grouped["vector_mean_wind_direction_from_deg"] = vector_direction_from

    return grouped


def make_time_profile(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Average all towers at each observation time."""
    grouped = (
        dataframe.groupby("datetime_utc", observed=True)
        .agg(
            n_wind=("wind_speed_mps", "count"),
            mean_u_east_mps=("wind_u_east_mps", "mean"),
            mean_v_north_mps=("wind_v_north_mps", "mean"),
            scalar_mean_wind_speed_mps=("wind_speed_mps", "mean"),
            scalar_std_wind_speed_mps=("wind_speed_mps", "std"),
            mean_temperature_c=("temperature_c", "mean"),
            std_temperature_c=("temperature_c", "std"),
            n_temperature=("temperature_c", "count"),
            mean_relative_humidity_percent=(
                "relative_humidity_percent",
                "mean",
            ),
            std_relative_humidity_percent=(
                "relative_humidity_percent",
                "std",
            ),
            n_humidity=("relative_humidity_percent", "count"),
        )
        .reset_index()
        .sort_values("datetime_utc")
    )

    vector_speed, vector_direction_from = wind_from_uv(
        grouped["mean_u_east_mps"].to_numpy(),
        grouped["mean_v_north_mps"].to_numpy(),
    )
    grouped["vector_mean_wind_speed_mps"] = vector_speed
    grouped["vector_mean_wind_speed_knots"] = vector_speed / KNOT_TO_MPS
    grouped["vector_mean_wind_direction_from_deg"] = vector_direction_from

    return grouped


def along_ray_wind_component(
    u_east_mps: float | np.ndarray,
    v_north_mps: float | np.ndarray,
    ray_azimuth_deg: float,
) -> np.ndarray:
    """Project a wind vector onto a ray azimuth measured clockwise from north."""
    azimuth_rad = np.deg2rad(ray_azimuth_deg)
    return (
        np.asarray(u_east_mps) * np.sin(azimuth_rad)
        + np.asarray(v_north_mps) * np.cos(azimuth_rad)
    )


def path_average_wind_profile(
    height_profile: pd.DataFrame,
    *,
    maximum_height_m: float,
    ray_azimuth_deg: float,
    vertical_step_m: float = 0.25,
) -> dict:
    """
    Vertically average the vector wind profile from 0 to maximum_height_m.

    Mean u and v values from populated height bins are linearly interpolated.
    Values below/above the observed profile use the nearest measured value.
    """
    if maximum_height_m <= 0:
        raise ValueError("maximum_height_m must be positive")
    if vertical_step_m <= 0:
        raise ValueError("vertical_step_m must be positive")

    profile = (
        height_profile.dropna(
            subset=[
                "mean_height_m",
                "mean_u_east_mps",
                "mean_v_north_mps",
            ]
        )
        .sort_values("mean_height_m")
    )
    if len(profile) < 2:
        raise ValueError("At least two populated height levels are required")

    z_observed = profile["mean_height_m"].to_numpy(dtype=float)
    u_observed = profile["mean_u_east_mps"].to_numpy(dtype=float)
    v_observed = profile["mean_v_north_mps"].to_numpy(dtype=float)

    z_grid = np.arange(
        0.0,
        maximum_height_m + vertical_step_m,
        vertical_step_m,
    )
    u_grid = np.interp(z_grid, z_observed, u_observed)
    v_grid = np.interp(z_grid, z_observed, v_observed)

    mean_u = float(np.trapezoid(u_grid, z_grid) / maximum_height_m)
    mean_v = float(np.trapezoid(v_grid, z_grid) / maximum_height_m)
    speed_mps, direction_from_deg = wind_from_uv(mean_u, mean_v)
    along_ray_mps = float(
        along_ray_wind_component(
            mean_u,
            mean_v,
            ray_azimuth_deg,
        )
    )

    return {
        "maximum_height_m": float(maximum_height_m),
        "mean_u_east_mps": mean_u,
        "mean_v_north_mps": mean_v,
        "vector_mean_speed_mps": float(speed_mps),
        "vector_mean_speed_knots": float(speed_mps / KNOT_TO_MPS),
        "vector_mean_direction_from_deg": float(direction_from_deg),
        "wind_along_ray_mps": along_ray_mps,
        "z_grid_m": z_grid,
        "u_grid_mps": u_grid,
        "v_grid_mps": v_grid,
    }


def calculate_acoustic_summary(
    dataframe: pd.DataFrame,
    *,
    height_profile: pd.DataFrame,
    maximum_path_height_m: float,
    ray_azimuth_deg: float,
    propagation_distance_m: float,
    compute_speed_of_sound,
) -> dict:
    """Calculate mean atmospheric and acoustic propagation parameters."""
    mean_temperature_f = float(dataframe["temperature_f"].mean())
    mean_temperature_c = float(dataframe["temperature_c"].mean())
    mean_humidity = float(
        dataframe["relative_humidity_percent"].mean()
    )

    still_air_speed = float(
        compute_speed_of_sound(
            mean_temperature_c,
            relative_humidity=mean_humidity,
        )
    )

    path_wind = path_average_wind_profile(
        height_profile,
        maximum_height_m=maximum_path_height_m,
        ray_azimuth_deg=ray_azimuth_deg,
    )
    effective_speed = still_air_speed + path_wind["wind_along_ray_mps"]

    return {
        "n_temperature": int(dataframe["temperature_c"].count()),
        "n_humidity": int(
            dataframe["relative_humidity_percent"].count()
        ),
        "mean_temperature_f": mean_temperature_f,
        "mean_temperature_c": mean_temperature_c,
        "mean_relative_humidity_percent": mean_humidity,
        "still_air_sound_speed_mps": still_air_speed,
        "ray_azimuth_deg": float(ray_azimuth_deg),
        "propagation_distance_m": float(propagation_distance_m),
        "maximum_path_height_m": float(maximum_path_height_m),
        "path_vector_mean_wind_speed_mps": (
            path_wind["vector_mean_speed_mps"]
        ),
        "path_vector_mean_wind_speed_knots": (
            path_wind["vector_mean_speed_knots"]
        ),
        "path_vector_mean_wind_direction_from_deg": (
            path_wind["vector_mean_direction_from_deg"]
        ),
        "wind_along_ray_mps": path_wind["wind_along_ray_mps"],
        "effective_sound_speed_mps": effective_speed,
        "still_air_travel_time_s": (
            propagation_distance_m / still_air_speed
        ),
        "wind_corrected_travel_time_s": (
            propagation_distance_m / effective_speed
        ),
        "wind_travel_time_correction_s": (
            propagation_distance_m / effective_speed
            - propagation_distance_m / still_air_speed
        ),
    }
