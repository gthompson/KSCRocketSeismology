"""KSC weather-tower data: loading, wind vectors, height profiles and along-ray acoustic speeds.

Copied from the AMOS-6 paper (amos6_paper/modules/weather_analysis.py, Zenodo release).
`event_weather_window` selects observations around a ksclib Event's origin time, and
`calculate_acoustic_summary` now defaults to ksclib.physics.compute_speed_of_sound.
"""
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

    # Normalize spreadsheet headers before checking them. KSC exports may
    # contain leading/trailing spaces or slightly different latitude/longitude
    # labels. Latitude and longitude are optional because they are not required
    # for the atmospheric profile or acoustic-speed calculations.
    dataframe = dataframe.copy()
    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    aliases = {
        "Latitude": "Lat",
        "Longitude": "Lon",
        "Tower Latitude": "Lat",
        "Tower Longitude": "Lon",
        "Average Wind Direction": "Avg Wind Direction",
        "Average Wind Speed": "Avg Wind Speed",
        "Temperature": "Temp",
        "RH": "Relative Humidity",
    }
    dataframe = dataframe.rename(
        columns={
            source: target
            for source, target in aliases.items()
            if source in dataframe.columns and target not in dataframe.columns
        }
    )

    required = {
        "UTC Date",
        "UTC Time",
        "Tower Measurement Location",
        "Height",
        "Avg Wind Direction",
        "Avg Wind Speed",
        "Temp",
        "Relative Humidity",
    }
    missing = required.difference(dataframe.columns)
    if missing:
        raise KeyError(
            "Weather spreadsheet is missing required columns: "
            f"{sorted(missing)}\n"
            f"Available columns: {dataframe.columns.tolist()}"
        )

    out = dataframe.copy()

    # Preserve tower coordinates when supplied, but do not require them.
    if "Lat" in out.columns:
        out["tower_latitude"] = pd.to_numeric(
            out["Lat"], errors="coerce"
        )
    else:
        out["tower_latitude"] = np.nan

    if "Lon" in out.columns:
        out["tower_longitude"] = pd.to_numeric(
            out["Lon"], errors="coerce"
        )
    else:
        out["tower_longitude"] = np.nan

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
    compute_speed_of_sound=None,
    sound_speed_kwargs: dict | None = None,
) -> dict:
    """Calculate mean atmospheric and acoustic propagation parameters."""
    if compute_speed_of_sound is None:
        from .physics import compute_speed_of_sound
    mean_temperature_f = float(dataframe["temperature_f"].mean())
    mean_temperature_c = float(dataframe["temperature_c"].mean())
    mean_humidity = float(
        dataframe["relative_humidity_percent"].mean()
    )

    still_air_speed = float(
        compute_speed_of_sound(
            mean_temperature_c,
            relative_humidity=mean_humidity,
            **(sound_speed_kwargs or {}),
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
        "sound_speed_model": getattr(compute_speed_of_sound, "__name__", "custom"),
        "sound_speed_parameters": dict(sound_speed_kwargs or {}),
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


def event_weather_window(dataframe: pd.DataFrame, event, before_s: float = 1800.0,
                         after_s: float = 1800.0) -> pd.DataFrame:
    """Observations from `before_s` before to `after_s` after the event origin time."""
    t0 = pd.Timestamp(event.origin_time.datetime, tz="UTC")
    return subset_time_window(dataframe, t0 - pd.Timedelta(seconds=before_s),
                              t0 + pd.Timedelta(seconds=after_s))


def event_acoustic_summary(dataframe: pd.DataFrame, event, station, *, stations=None,
                           maximum_path_height_m: float = 100.0, height_bin_m: float = 10.0,
                           **kwargs) -> dict:
    """`calculate_acoustic_summary` for the ray from the event site to `station`.

    Ray azimuth and propagation distance come from ksclib.station_table(event);
    `dataframe` should already be limited in time (e.g. by event_weather_window).
    """
    from .geometry import station_table
    row = (stations if stations is not None else station_table(event)).loc[station]
    out = calculate_acoustic_summary(
        dataframe, height_profile=make_height_profile(dataframe, height_bin_m=height_bin_m),
        maximum_path_height_m=maximum_path_height_m, ray_azimuth_deg=float(row.azimuth_deg),
        propagation_distance_m=float(row.distance_km) * 1000.0, **kwargs)
    out["station"] = station
    return out


def load_iem_asos_csv(filename: str | Path, *, sensor_height_m: float = 10.0) -> pd.DataFrame:
    """Load an Iowa Environmental Mesonet ASOS/METAR download into the same columns as
    `load_ksc_weather_excel` (one height level, `sensor_height_m`).

    Expects the IEM `asos.py` comma format with columns station, valid, lon, lat, tmpf,
    relh, drct, sknt (optionally dwpf, mslp, alti). Calm (drct 0, sknt 0) gives zero wind;
    missing values ("M") become NaN. Times are UTC.
    """
    df = pd.read_csv(filename, na_values=["M", "T"])
    out = pd.DataFrame({
        "station": df["station"],
        "datetime_utc": pd.to_datetime(df["valid"], utc=True),
        "tower_latitude": pd.to_numeric(df.get("lat"), errors="coerce"),
        "tower_longitude": pd.to_numeric(df.get("lon"), errors="coerce"),
        "height_m": float(sensor_height_m),
        "temperature_f": pd.to_numeric(df["tmpf"], errors="coerce"),
        "relative_humidity_percent": pd.to_numeric(df["relh"], errors="coerce"),
        "wind_direction_from_deg": pd.to_numeric(df["drct"], errors="coerce") % 360.0,
        "wind_speed_knots": pd.to_numeric(df["sknt"], errors="coerce"),
    })
    if "mslp" in df:
        out["sea_level_pressure_pa"] = pd.to_numeric(df["mslp"], errors="coerce") * 100.0
    out["height_ft"] = out["height_m"] / FOOT_TO_M
    out["temperature_c"] = (out["temperature_f"] - 32.0) * 5.0 / 9.0
    out["wind_speed_mps"] = out["wind_speed_knots"] * KNOT_TO_MPS
    d = np.deg2rad(out["wind_direction_from_deg"])
    out["wind_u_east_mps"] = -out["wind_speed_mps"] * np.sin(d)
    out["wind_v_north_mps"] = -out["wind_speed_mps"] * np.cos(d)
    return out


def load_ksc_tower_1min(filenames, *, prevailing_side_only: bool = True) -> pd.DataFrame:
    """Load KSC Spaceport Weather Archive 1-minute tower files (``WT_1MIN_YYYYMMDDHHMM.dat``,
    product midds/WINDS_TOWER) into the columns of `load_iem_asos_csv`, one row per tower,
    sensor height and minute.

    Each file has a title line (with the UTC time, e.g. "0100Z"), a header and a units line.
    Tower IDs with a side suffix (NW, SE, ...) carry sensors on two sides of the tower; with
    ``prevailing_side_only`` only the side named in PREVAILING (upwind, per the archive) is kept.
    999 marks missing values. The archive data are not quality controlled.
    """
    if isinstance(filenames, (str, Path)):
        filenames = [filenames]
    frames = []
    for f in sorted(Path(x) for x in filenames):
        stamp = f.stem.split("_")[-1]
        df = pd.read_csv(f, skiprows=[0, 2], dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        df["datetime_utc"] = pd.Timestamp(stamp[:8] + "T" + stamp[8:12], tz="UTC")
        frames.append(df)
    d = pd.concat(frames, ignore_index=True)
    tower = d["TOWER"].astype(str).str.strip()
    side = tower.str[4:]
    prevailing = d["PREVAILING"].fillna("").astype(str).str.strip()
    if prevailing_side_only:
        keep = (side == "") | (side == prevailing)
        d, tower, side = d[keep], tower[keep], side[keep]

    def num(col):
        return pd.to_numeric(d[col], errors="coerce").mask(lambda s: s == 999)

    out = pd.DataFrame({
        "station": tower.str[:4],
        "sensor_side": side,
        "datetime_utc": d["datetime_utc"],
        "tower_latitude": num("LAT"),
        "tower_longitude": num("LON"),
        "height_ft": num("HGT"),
        "temperature_f": num("TMP"),
        "relative_humidity_percent": num("RH"),
        "wind_direction_from_deg": num("01 MIN AVG DIR") % 360.0,
        "wind_speed_knots": num("01 MIN AVG SPD"),
    })
    out["height_m"] = out["height_ft"] * FOOT_TO_M
    out["temperature_c"] = (out["temperature_f"] - 32.0) * 5.0 / 9.0
    out["wind_speed_mps"] = out["wind_speed_knots"] * KNOT_TO_MPS
    rad = np.deg2rad(out["wind_direction_from_deg"])
    out["wind_u_east_mps"] = -out["wind_speed_mps"] * np.sin(rad)
    out["wind_v_north_mps"] = -out["wind_speed_mps"] * np.cos(rad)
    return out.reset_index(drop=True)


def tower_means(towers: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    """Time-mean of each tower and sensor height between ``start`` and ``end`` (UTC, inclusive):
    temperature, RH and vector-mean wind components."""
    t = towers
    if start is not None:
        t = t[t.datetime_utc >= pd.Timestamp(start, tz="UTC") if pd.Timestamp(start).tzinfo is None
              else t.datetime_utc >= pd.Timestamp(start)]
    if end is not None:
        t = t[t.datetime_utc <= pd.Timestamp(end, tz="UTC") if pd.Timestamp(end).tzinfo is None
              else t.datetime_utc <= pd.Timestamp(end)]
    return (t.groupby(["station", "height_ft"])
             .agg(lat=("tower_latitude", "first"), lon=("tower_longitude", "first"),
                  height_m=("height_m", "first"), temperature_c=("temperature_c", "mean"),
                  relative_humidity_percent=("relative_humidity_percent", "mean"),
                  wind_u_east_mps=("wind_u_east_mps", "mean"), wind_v_north_mps=("wind_v_north_mps", "mean"),
                  n=("datetime_utc", "size"))
             .reset_index())


def _idw(tbl: pd.DataFrame, col: str, lat: float, lon: float, smoothing_m: float) -> float:
    t = tbl.dropna(subset=[col])
    if t.empty:
        return np.nan
    dx = (t["lon"] - lon) * 111.32e3 * np.cos(np.radians(lat))
    dy = (t["lat"] - lat) * 110.57e3
    w = 1.0 / (np.hypot(dx, dy) + smoothing_m) ** 2
    return float((t[col] * w).sum() / w.sum())


def tower_path_sound_speed(means: pd.DataFrame, lat0: float, lon0: float, lat1: float, lon1: float, *,
                           height_ft_temperature: float, height_ft_wind: float | None = None,
                           pressure_pa: float = 101325.0, co2_ppm: float = 425.0, n: int = 200,
                           smoothing_m: float = 500.0) -> dict:
    """Effective sound speed along the straight path (lat0, lon0) -> (lat1, lon1) from tower means.

    At ``n`` points along the path, temperature and RH (at ``height_ft_temperature``) and the wind
    components (at ``height_ft_wind``, default the same height) are interpolated from the towers by
    inverse-distance-squared weighting (distance + ``smoothing_m``). The still-air speed follows
    Cramer (1993); the wind is projected on the path direction. Returns the travel time over the
    path length, the path-average (harmonic) speed and the means of c0 and of the along-path wind.
    """
    from .physics import compute_speed_of_sound_cramer
    height_ft_wind = height_ft_temperature if height_ft_wind is None else height_ft_wind
    T = means[means.height_ft == height_ft_temperature]
    W = means[means.height_ft == height_ft_wind]
    ex = (lon1 - lon0) * 111.32e3 * np.cos(np.radians(lat0))
    ny = (lat1 - lat0) * 110.57e3
    length = float(np.hypot(ex, ny))
    e = np.array([ex, ny]) / length
    f = np.linspace(0.0, 1.0, n)
    c0, wa = [], []
    for la, lo in zip(lat0 + f * (lat1 - lat0), lon0 + f * (lon1 - lon0)):
        c0.append(float(compute_speed_of_sound_cramer(_idw(T, "temperature_c", la, lo, smoothing_m),
                                                      _idw(T, "relative_humidity_percent", la, lo, smoothing_m),
                                                      pressure_pa, co2_ppm)))
        wa.append(_idw(W, "wind_u_east_mps", la, lo, smoothing_m) * e[0]
                  + _idw(W, "wind_v_north_mps", la, lo, smoothing_m) * e[1])
    c = np.array(c0) + np.array(wa)
    tt = length * float(np.mean(1.0 / c))
    return {"length_m": length, "travel_time_s": tt, "c_path_mps": length / tt,
            "c0_mean_mps": float(np.mean(c0)), "wind_along_path_mps": float(np.mean(wa))}
