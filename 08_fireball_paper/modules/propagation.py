from __future__ import annotations

import numpy as np
import pandas as pd


def add_acoustic_propagation_columns(
    dataframe: pd.DataFrame,
    *,
    temperature_f: float,
    relative_humidity_percent: float,
    wind_direction_from_deg: float,
    wind_speed_knots: float,
    reference_overpressure_pa: float,
    distance_column: str = "distance_m",
    azimuth_column: str = "ray_azimuth_deg",
) -> pd.DataFrame:
    """Add receiver-specific acoustic speeds and travel times."""
    from physics import effective_sound_speed_along_ray

    required = {distance_column, azimuth_column}
    missing = required.difference(dataframe.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if not dataframe.columns.is_unique:
        raise ValueError("Input DataFrame contains duplicate column names")

    rows = []
    for _, row in dataframe.iterrows():
        result = effective_sound_speed_along_ray(
            temperature_f,
            relative_humidity_percent=relative_humidity_percent,
            wind_direction_from_deg=wind_direction_from_deg,
            wind_speed_knots=wind_speed_knots,
            ray_azimuth_deg=float(row[azimuth_column]),
            reference_distance=float(row[distance_column]),
            reference_overpressure=reference_overpressure_pa,
        )
        still = float(result["speed_of_sound_still_air_mps"])
        wind = float(result["wind_along_ray_mps"])
        acoustic = float(result.get("acoustic_speed_with_wind_mps", still + wind))
        effective = float(result["effective_sound_speed_mps"])
        rows.append(
            {
                "still_air_sound_speed_mps": still,
                "wind_along_ray_mps": wind,
                "acoustic_speed_with_wind_mps": acoustic,
                "effective_sound_speed_mps": effective,
                "acoustic_travel_time_s": float(row[distance_column]) / acoustic,
                "shockwave_travel_time_s": float(row[distance_column]) / effective,
            }
        )

    return pd.concat(
        [dataframe.reset_index(drop=True), pd.DataFrame(rows)],
        axis=1,
    )


def reduced_pressure(
    pressure_pa: float | np.ndarray,
    distance_m: float | np.ndarray,
    reference_distance_m: float = 1000.0,
):
    """Reduce pressure using spherical 1/r geometric spreading."""
    if reference_distance_m <= 0:
        raise ValueError("reference_distance_m must be positive")
    return np.asarray(pressure_pa) * np.asarray(distance_m) / reference_distance_m
