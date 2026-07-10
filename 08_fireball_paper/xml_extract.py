from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd
from obspy import Inventory, UTCDateTime, read_inventory
from pyproj import Transformer


def load_inventory_for_time_range(
    stationxml_file: str | Path,
    starttime: UTCDateTime | str,
    endtime: UTCDateTime | str,
) -> Inventory:
    """
    Read StationXML and retain metadata epochs overlapping a time range.

    Parameters
    ----------
    stationxml_file
        Path to the StationXML file.
    starttime
        Beginning of the requested interval.
    endtime
        End of the requested interval.

    Returns
    -------
    obspy.Inventory
        Inventory containing epochs that overlap the requested interval.
    """
    stationxml_file = Path(stationxml_file)

    if not stationxml_file.exists():
        raise FileNotFoundError(
            f"StationXML file not found: {stationxml_file}"
        )

    starttime = UTCDateTime(starttime)
    endtime = UTCDateTime(endtime)

    if endtime <= starttime:
        raise ValueError(
            f"endtime must be later than starttime: "
            f"{starttime} to {endtime}"
        )

    inventory = read_inventory(stationxml_file)

    return inventory.select(
        starttime=starttime,
        endtime=endtime,
    )


def inventory_stations_to_dataframe(
    inventory: Inventory,
) -> pd.DataFrame:
    """
    Convert an ObsPy Inventory to one row per station epoch.

    Station-level coordinates are used.
    """
    rows = []

    for network in inventory:
        for station in network:
            rows.append(
                {
                    "network": network.code,
                    "station": station.code,
                    "latitude": station.latitude,
                    "longitude": station.longitude,
                    "elevation_m": station.elevation,
                    "site_name": (
                        station.site.name
                        if station.site is not None
                        else None
                    ),
                    "station_start": (
                        station.start_date.datetime
                        if station.start_date is not None
                        else None
                    ),
                    "station_end": (
                        station.end_date.datetime
                        if station.end_date is not None
                        else None
                    ),
                    "n_channels": len(station.channels),
                }
            )

    columns = [
        "network",
        "station",
        "latitude",
        "longitude",
        "elevation_m",
        "site_name",
        "station_start",
        "station_end",
        "n_channels",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values(["network", "station"])
        .reset_index(drop=True)
    )


def inventory_channels_to_dataframe(
    inventory: Inventory,
) -> pd.DataFrame:
    """
    Convert an ObsPy Inventory to one row per channel epoch.

    Channel coordinates are retained because separate sensors belonging
    to the same station may occupy different positions.
    """
    rows = []

    for network in inventory:
        for station in network:
            for channel in station:
                location = channel.location_code or ""

                rows.append(
                    {
                        "network": network.code,
                        "station": station.code,
                        "location": location,
                        "channel": channel.code,
                        "seed_id": (
                            f"{network.code}.{station.code}."
                            f"{location}.{channel.code}"
                        ),
                        "latitude": channel.latitude,
                        "longitude": channel.longitude,
                        "elevation_m": channel.elevation,
                        "depth_m": channel.depth,
                        "azimuth_deg": channel.azimuth,
                        "dip_deg": channel.dip,
                        "sample_rate_hz": channel.sample_rate,
                        "sensor_description": (
                            channel.sensor.description
                            if channel.sensor is not None
                            else None
                        ),
                        "channel_start": (
                            channel.start_date.datetime
                            if channel.start_date is not None
                            else None
                        ),
                        "channel_end": (
                            channel.end_date.datetime
                            if channel.end_date is not None
                            else None
                        ),
                        "station_latitude": station.latitude,
                        "station_longitude": station.longitude,
                        "station_elevation_m": station.elevation,
                    }
                )

    columns = [
        "network",
        "station",
        "location",
        "channel",
        "seed_id",
        "latitude",
        "longitude",
        "elevation_m",
        "depth_m",
        "azimuth_deg",
        "dip_deg",
        "sample_rate_hz",
        "sensor_description",
        "channel_start",
        "channel_end",
        "station_latitude",
        "station_longitude",
        "station_elevation_m",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values(
            ["network", "station", "location", "channel"]
        )
        .reset_index(drop=True)
    )


def add_projected_coordinates(
    dataframe: pd.DataFrame,
    source_crs: str,
    target_crs: str,
    longitude_column: str = "longitude",
    latitude_column: str = "latitude",
    easting_column: str = "easting",
    northing_column: str = "northing",
) -> pd.DataFrame:
    """
    Add projected easting and northing columns to a coordinate table.

    A copy is returned; the input DataFrame is not modified.
    """
    required_columns = {
        longitude_column,
        latitude_column,
    }

    missing = required_columns.difference(dataframe.columns)

    if missing:
        raise KeyError(
            f"Missing coordinate columns: {sorted(missing)}"
        )

    result = dataframe.copy()

    if result.empty:
        result[easting_column] = pd.Series(dtype=float)
        result[northing_column] = pd.Series(dtype=float)
        return result

    if result[
        [longitude_column, latitude_column]
    ].isna().any().any():
        raise ValueError(
            "Cannot project rows containing missing latitude or "
            "longitude values."
        )

    transformer = Transformer.from_crs(
        source_crs,
        target_crs,
        always_xy=True,
    )

    easting, northing = transformer.transform(
        result[longitude_column].to_numpy(),
        result[latitude_column].to_numpy(),
    )

    result[easting_column] = easting
    result[northing_column] = northing

    return result


def build_station_sensor_dataframe(
    channels_df: pd.DataFrame,
    station_code: str,
    channel_to_sensor: Mapping[str, str],
    channel_to_label: Mapping[str, str],
    source_crs: str,
    target_crs: str,
    network_code: str | None = None,
    location_code: str | None = None,
) -> pd.DataFrame:
    """
    Build one row per physical sensor for one station.

    Parameters
    ----------
    channels_df
        Channel-level table created by
        ``inventory_channels_to_dataframe``.
    station_code
        Station code to select, for example ``"BCHH"``.
    channel_to_sensor
        Mapping from channel code to physical sensor name.
        Channels mapped to the same sensor are reduced to one row.
    channel_to_label
        Mapping from channel code to plotting/display label.
    source_crs
        CRS of the input longitude and latitude coordinates.
    target_crs
        CRS used to calculate easting and northing.
    network_code
        Optional network-code restriction.
    location_code
        Optional location-code restriction.

    Returns
    -------
    pandas.DataFrame
        Columns are sensor, label, easting, northing, lat, and lon.
    """
    required_columns = {
        "network",
        "station",
        "location",
        "channel",
        "latitude",
        "longitude",
    }

    missing = required_columns.difference(channels_df.columns)

    if missing:
        raise KeyError(
            f"Channel DataFrame is missing columns: "
            f"{sorted(missing)}"
        )

    selected = channels_df.loc[
        channels_df["station"] == station_code
    ].copy()

    if network_code is not None:
        selected = selected.loc[
            selected["network"] == network_code
        ].copy()

    if location_code is not None:
        selected = selected.loc[
            selected["location"] == location_code
        ].copy()

    requested_channels = set(channel_to_sensor)
    selected = selected.loc[
        selected["channel"].isin(requested_channels)
    ].copy()

    if selected.empty:
        raise ValueError(
            f"No matching channels found for station "
            f"{station_code!r}."
        )

    found_channels = set(selected["channel"])
    missing_channels = requested_channels.difference(found_channels)

    if missing_channels:
        raise ValueError(
            f"Channels missing for station {station_code!r}: "
            f"{sorted(missing_channels)}"
        )

    selected["sensor"] = selected["channel"].map(
        channel_to_sensor
    )
    selected["label"] = selected["channel"].map(
        channel_to_label
    )

    if selected["sensor"].isna().any():
        bad_channels = selected.loc[
            selected["sensor"].isna(),
            "channel",
        ].tolist()

        raise ValueError(
            f"No sensor mapping for channels: {bad_channels}"
        )

    if selected["label"].isna().any():
        bad_channels = selected.loc[
            selected["label"].isna(),
            "channel",
        ].tolist()

        raise ValueError(
            f"No label mapping for channels: {bad_channels}"
        )

    selected = add_projected_coordinates(
        dataframe=selected,
        source_crs=source_crs,
        target_crs=target_crs,
        longitude_column="longitude",
        latitude_column="latitude",
        easting_column="easting",
        northing_column="northing",
    )

    selected = selected.rename(
        columns={
            "latitude": "lat",
            "longitude": "lon",
        }
    )

    # DHE, DHN, and DHZ share one physical seismometer position.
    result = (
        selected
        .drop_duplicates(subset=["sensor"])
        [
            [
                "sensor",
                "label",
                "easting",
                "northing",
                "lat",
                "lon",
            ]
        ]
        .reset_index(drop=True)
    )

    # Preserve the order defined by channel_to_sensor.
    sensor_order = list(dict.fromkeys(channel_to_sensor.values()))

    result["sensor"] = pd.Categorical(
        result["sensor"],
        categories=sensor_order,
        ordered=True,
    )

    result = (
        result
        .sort_values("sensor")
        .reset_index(drop=True)
    )

    result["sensor"] = result["sensor"].astype(str)

    return result

def load_station_sensor_dataframe(
    stationxml_file: str | Path,
    starttime: UTCDateTime | str,
    endtime: UTCDateTime | str,
    station_code: str,
    channel_to_sensor: Mapping[str, str],
    channel_to_label: Mapping[str, str],
    source_crs: str,
    target_crs: str,
    network_code: str | None = None,
    location_code: str | None = None,
) -> tuple[Inventory, pd.DataFrame, pd.DataFrame]:
    """
    Load time-appropriate StationXML metadata and build channel and
    physical-sensor tables.

    Returns
    -------
    inventory
        Time-selected ObsPy Inventory.
    channels_df
        One row per channel epoch.
    sensors_df
        One row per physical sensor.
    """
    inventory = load_inventory_for_time_range(
        stationxml_file=stationxml_file,
        starttime=starttime,
        endtime=endtime,
    )

    channels_df = inventory_channels_to_dataframe(
        inventory=inventory
    )

    sensors_df = build_station_sensor_dataframe(
        channels_df=channels_df,
        station_code=station_code,
        channel_to_sensor=channel_to_sensor,
        channel_to_label=channel_to_label,
        source_crs=source_crs,
        target_crs=target_crs,
        network_code=network_code,
        location_code=location_code,
    )

    return inventory, channels_df, sensors_df