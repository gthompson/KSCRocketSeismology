"""
Utilities for generating Figure 1 of the Falcon 9 / BCHH paper.

This module keeps file I/O, metadata extraction, coordinate conversion,
and plotting logic outside the notebook. Project-specific choices remain
explicit in the notebook.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FormatStrFormatter, FuncFormatter, MaxNLocator
from obspy import Inventory, UTCDateTime, read_inventory
from pyproj import Geod, Transformer
from xml.etree import ElementTree as ET


# -----------------------------------------------------------------------------
# KML metadata
# -----------------------------------------------------------------------------


def read_kml_points(kml_file: str | Path) -> dict[str, dict]:
    """
    Read all named Point placemarks from a KML file.

    KML stores coordinates in longitude, latitude, altitude order.
    """
    kml_file = Path(kml_file)
    if not kml_file.exists():
        raise FileNotFoundError(f"KML file not found: {kml_file}")

    namespace = {"kml": "http://www.opengis.net/kml/2.2"}
    root = ET.parse(kml_file).getroot()

    points: dict[str, dict] = {}

    for placemark in root.findall(".//kml:Placemark", namespace):
        name = placemark.findtext("kml:name", namespaces=namespace)
        coordinate_text = placemark.findtext(
            ".//kml:Point/kml:coordinates",
            namespaces=namespace,
        )

        if not name or not coordinate_text:
            continue

        values = coordinate_text.strip().split(",")
        if len(values) < 2:
            raise ValueError(
                f"Unexpected coordinates for placemark {name!r}: "
                f"{coordinate_text!r}"
            )

        lon = float(values[0])
        lat = float(values[1])
        altitude_m = float(values[2]) if len(values) >= 3 else None

        points[name] = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "altitude_m": altitude_m,
        }

    if not points:
        raise ValueError(f"No named Point placemarks found in {kml_file}")

    return points


# -----------------------------------------------------------------------------
# StationXML metadata
# -----------------------------------------------------------------------------


def load_inventory_for_time_range(
    stationxml_file: str | Path,
    starttime: UTCDateTime | str,
    endtime: UTCDateTime | str,
) -> Inventory:
    """Read StationXML and retain metadata epochs overlapping a time range."""
    stationxml_file = Path(stationxml_file)
    if not stationxml_file.exists():
        raise FileNotFoundError(f"StationXML file not found: {stationxml_file}")

    starttime = UTCDateTime(starttime)
    endtime = UTCDateTime(endtime)

    if endtime <= starttime:
        raise ValueError("endtime must be later than starttime")

    inventory = read_inventory(stationxml_file)
    return inventory.select(starttime=starttime, endtime=endtime)


def inventory_stations_to_dataframe(inventory: Inventory) -> pd.DataFrame:
    """Convert an ObsPy Inventory to one row per station epoch."""
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
                    "site_name": station.site.name if station.site else None,
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


def inventory_channels_to_dataframe(inventory: Inventory) -> pd.DataFrame:
    """Convert an ObsPy Inventory to one row per channel epoch."""
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

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values(["network", "station", "location", "channel"])
        .reset_index(drop=True)
    )


def add_projected_coordinates(
    dataframe: pd.DataFrame,
    source_crs: str,
    target_crs: str,
    longitude_column: str = "longitude",
    latitude_column: str = "latitude",
) -> pd.DataFrame:
    """Return a copy with projected ``easting`` and ``northing`` columns."""
    required = {longitude_column, latitude_column}
    missing = required.difference(dataframe.columns)
    if missing:
        raise KeyError(f"Missing coordinate columns: {sorted(missing)}")

    result = dataframe.copy()
    transformer = Transformer.from_crs(
        source_crs,
        target_crs,
        always_xy=True,
    )

    easting, northing = transformer.transform(
        result[longitude_column].to_numpy(),
        result[latitude_column].to_numpy(),
    )
    result["easting"] = easting
    result["northing"] = northing
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
    Build one row per physical sensor from channel-level StationXML metadata.

    Multiple channels mapped to the same physical sensor are collapsed to one
    row. This is why the three seismometer components become one BCHH point.
    """
    selected = channels_df.loc[
        channels_df["station"] == station_code
    ].copy()

    if network_code is not None:
        selected = selected.loc[selected["network"] == network_code].copy()
    if location_code is not None:
        selected = selected.loc[selected["location"] == location_code].copy()

    requested_channels = set(channel_to_sensor)
    selected = selected.loc[
        selected["channel"].isin(requested_channels)
    ].copy()

    if selected.empty:
        raise ValueError(
            f"No matching channels found for station {station_code!r}"
        )

    missing_channels = requested_channels.difference(selected["channel"])
    if missing_channels:
        raise ValueError(
            f"Missing expected channels for {station_code!r}: "
            f"{sorted(missing_channels)}"
        )

    selected["sensor"] = selected["channel"].map(channel_to_sensor)
    selected["label"] = selected["channel"].map(channel_to_label)

    selected = add_projected_coordinates(
        selected,
        source_crs=source_crs,
        target_crs=target_crs,
    ).rename(
        columns={
            "latitude": "lat",
            "longitude": "lon",
        }
    )

    result = (
        selected.drop_duplicates(subset=["sensor"])
        [["sensor", "label", "easting", "northing", "lat", "lon"]]
        .reset_index(drop=True)
    )

    sensor_order = list(dict.fromkeys(channel_to_sensor.values()))
    result["sensor"] = pd.Categorical(
        result["sensor"],
        categories=sensor_order,
        ordered=True,
    )
    result = result.sort_values("sensor").reset_index(drop=True)
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
    """Load time-selected metadata and return inventory, channels, and sensors."""
    inventory = load_inventory_for_time_range(
        stationxml_file=stationxml_file,
        starttime=starttime,
        endtime=endtime,
    )
    channels_df = inventory_channels_to_dataframe(inventory)
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


def get_sensor_location(
    sensors_df: pd.DataFrame,
    sensor_name: str,
    display_name: str | None = None,
) -> dict:
    """Return one physical sensor position as a simple location dictionary."""
    matches = sensors_df.loc[sensors_df["sensor"] == sensor_name]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one row for sensor {sensor_name!r}; "
            f"found {len(matches)}"
        )

    row = matches.iloc[0]
    return {
        "name": display_name or sensor_name,
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
    }


# -----------------------------------------------------------------------------
# Mapping helpers
# -----------------------------------------------------------------------------


def equal_scale_lonlat_limits(
    center_lon: float,
    center_lat: float,
    width_lon: float | None = None,
    height_lat: float | None = None,
):
    """Return lon/lat limits with approximately equal ground scale."""
    if width_lon is None and height_lat is None:
        raise ValueError("Provide either width_lon or height_lat")

    coslat = np.cos(np.deg2rad(center_lat))
    if width_lon is not None:
        height_lat = width_lon * coslat
    else:
        width_lon = height_lat / coslat

    return (
        (center_lon - width_lon / 2, center_lon + width_lon / 2),
        (center_lat - height_lat / 2, center_lat + height_lat / 2),
    )


def set_equal_ground_aspect(ax) -> None:
    """Make x and y axes represent approximately equal ground distances."""
    lat_mid = np.mean(ax.get_ylim())
    ax.set_aspect(1 / np.cos(np.deg2rad(lat_mid)), adjustable="box")


def add_basemap(
    ax,
    provider: str = "voyager",
    alpha: float = 0.85,
    zoom: str | int = "auto",
) -> None:
    """Add a Contextily basemap to an axis whose coordinates are lon/lat."""
    providers = {
        "osm": cx.providers.OpenStreetMap.Mapnik,
        "positron": cx.providers.CartoDB.Positron,
        "voyager": cx.providers.CartoDB.Voyager,
    }
    if provider not in providers:
        raise ValueError(
            f"Unknown basemap provider {provider!r}; "
            f"choose from {sorted(providers)}"
        )

    cx.add_basemap(
        ax,
        source=providers[provider],
        crs="EPSG:4326",
        reset_extent=False,
        attribution_size=7,
        alpha=alpha,
        zoom=zoom,
    )


def _plain_utm_formatter(value, _position):
    return f"{value:.0f}"


def setup_dual_axes(
    ax,
    lonlim,
    latlim,
    ll_to_utm: Transformer,
    utm_to_ll: Transformer,
    lonfmt: str = "%.3f",
    latfmt: str = "%.3f",
    xlabel: str = "Longitude (°W)",
    ylabel: str = "Latitude (°N)",
    top_xlabel: str = "Easting (m, UTM 17N)",
    right_ylabel: str = "Northing (m, UTM 17N)",
    top_nbins: int = 5,
    right_nbins: int = 6,
):
    """Configure lon/lat axes with secondary UTM axes."""
    ax.set_xlim(lonlim)
    ax.set_ylim(latlim)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(FormatStrFormatter(lonfmt))
    ax.yaxis.set_major_formatter(FormatStrFormatter(latfmt))
    ax.xaxis.get_offset_text().set_visible(False)
    ax.yaxis.get_offset_text().set_visible(False)

    lon_mid = float(np.mean(lonlim))
    lat_mid = float(np.mean(latlim))
    e_mid, n_mid = ll_to_utm.transform(lon_mid, lat_mid)

    def lon_to_easting(lon):
        lon = np.asarray(lon, dtype=float)
        easting, _ = ll_to_utm.transform(
            lon,
            np.full_like(lon, lat_mid),
        )
        return easting

    def easting_to_lon(easting):
        easting = np.asarray(easting, dtype=float)
        lon, _ = utm_to_ll.transform(
            easting,
            np.full_like(easting, n_mid),
        )
        return lon

    def lat_to_northing(lat):
        lat = np.asarray(lat, dtype=float)
        _, northing = ll_to_utm.transform(
            np.full_like(lat, lon_mid),
            lat,
        )
        return northing

    def northing_to_lat(northing):
        northing = np.asarray(northing, dtype=float)
        _, lat = utm_to_ll.transform(
            np.full_like(northing, e_mid),
            northing,
        )
        return lat

    ax_top = ax.secondary_xaxis(
        "top",
        functions=(lon_to_easting, easting_to_lon),
    )
    ax_top.set_xlabel(top_xlabel)
    ax_top.xaxis.set_major_formatter(FuncFormatter(_plain_utm_formatter))
    ax_top.xaxis.set_major_locator(
        MaxNLocator(nbins=top_nbins, integer=True)
    )
    ax_top.xaxis.get_offset_text().set_visible(False)

    ax_right = ax.secondary_yaxis(
        "right",
        functions=(lat_to_northing, northing_to_lat),
    )
    ax_right.set_ylabel(right_ylabel)
    ax_right.yaxis.set_major_formatter(FuncFormatter(_plain_utm_formatter))
    ax_right.yaxis.set_major_locator(
        MaxNLocator(nbins=right_nbins, integer=True)
    )
    ax_right.yaxis.get_offset_text().set_visible(False)

    return ax_top, ax_right


def add_label(
    ax,
    lon: float,
    lat: float,
    text: str,
    dx: float = 0.0002,
    dy: float = 0.00015,
    size: float = 9,
    ha: str = "left",
    va: str = "center",
) -> None:
    """Add a readable map label with a semi-opaque white background."""
    ax.text(
        lon + dx,
        lat + dy,
        text,
        fontsize=size,
        ha=ha,
        va=va,
        bbox={
            "facecolor": "white",
            "edgecolor": "0.8",
            "alpha": 0.90,
            "pad": 1.4,
        },
        zorder=30,
    )


def add_north_arrow_axes(
    ax,
    xy=(0.93, 0.78),
    length: float = 0.10,
) -> None:
    """Draw a north arrow using axis-fraction coordinates."""
    x, y = xy
    ax.annotate(
        "",
        xy=(x, y + length),
        xytext=(x, y),
        xycoords="axes fraction",
        arrowprops={
            "facecolor": "black",
            "edgecolor": "black",
            "width": 4,
            "headwidth": 13,
        },
        zorder=50,
        clip_on=True,
    )
    ax.text(
        x,
        y + length + 0.018,
        "N",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        zorder=51,
        clip_on=True,
    )


def add_scalebar_lonlat(
    ax,
    lon: float,
    lat: float,
    length_m: float,
    label_text: str,
    geod: Geod,
) -> None:
    """Add an east-west scale bar to a lon/lat axis."""
    lon2, lat2, _ = geod.fwd(lon, lat, 90, length_m)
    tick_h = 0.018 * (ax.get_ylim()[1] - ax.get_ylim()[0])

    ax.plot(
        [lon, lon2],
        [lat, lat2],
        "k-",
        lw=3,
        solid_capstyle="butt",
        zorder=40,
    )
    ax.plot(
        [lon, lon],
        [lat - tick_h / 2, lat + tick_h / 2],
        "k-",
        lw=2,
        zorder=40,
    )
    ax.plot(
        [lon2, lon2],
        [lat - tick_h / 2, lat + tick_h / 2],
        "k-",
        lw=2,
        zorder=40,
    )
    ax.text(
        (lon + lon2) / 2,
        lat + 1.15 * tick_h,
        label_text,
        ha="center",
        va="bottom",
        fontsize=9,
        bbox={
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.85,
            "pad": 1,
        },
        zorder=41,
    )


# -----------------------------------------------------------------------------
# Figure construction
# -----------------------------------------------------------------------------


def make_figure1(
    slc40: Mapping[str, float],
    slc41: Mapping[str, float],
    bchh: Mapping[str, float],
    bchh_sensors: pd.DataFrame,
    geod: Geod,
    ll_to_utm: Transformer,
    utm_to_ll: Transformer,
):
    """Create the two-panel SLC-40/BCHH location figure."""
    required_sensor_columns = {
        "sensor",
        "label",
        "easting",
        "northing",
        "lat",
        "lon",
    }
    missing = required_sensor_columns.difference(bchh_sensors.columns)
    if missing:
        raise KeyError(
            f"BCHH sensor table is missing columns: {sorted(missing)}"
        )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12.4, 5.8),
        gridspec_kw={"width_ratios": [1.0, 1.12]},
    )
    fig.subplots_adjust(
        left=0.065,
        right=0.975,
        bottom=0.105,
        top=0.89,
        wspace=0.48,
    )

    # Panel A: regional source-to-array geometry
    ax = axes[0]
    ax.set_title("A", loc="left", fontsize=14, fontweight="bold")

    center_lon = 0.5 * (slc40["lon"] + bchh["lon"]) - 0.003
    center_lat = 0.5 * (slc40["lat"] + bchh["lat"]) + 0.0015
    lonlim, latlim = equal_scale_lonlat_limits(
        center_lon,
        center_lat,
        width_lon=0.037,
    )

    setup_dual_axes(
        ax=ax,
        lonlim=lonlim,
        latlim=latlim,
        ll_to_utm=ll_to_utm,
        utm_to_ll=utm_to_ll,
        lonfmt="%.3f",
        latfmt="%.3f",
        right_ylabel="",
        top_nbins=5,
        right_nbins=5,
    )
    set_equal_ground_aspect(ax)
    add_basemap(ax, provider="voyager", alpha=0.82, zoom="auto")
    ax.set_xlim(lonlim)
    ax.set_ylim(latlim)

    azimuth_deg, _, distance_m = geod.inv(
        slc40["lon"],
        slc40["lat"],
        bchh["lon"],
        bchh["lat"],
    )

    ax.plot(
        [slc40["lon"], bchh["lon"]],
        [slc40["lat"], bchh["lat"]],
        "k-",
        lw=2.2,
        zorder=10,
    )

    ax.scatter(
        slc40["lon"],
        slc40["lat"],
        marker="^",
        s=185,
        c="yellow",
        edgecolor="black",
        zorder=20,
    )
    ax.scatter(
        slc41["lon"],
        slc41["lat"],
        marker="^",
        s=145,
        c="white",
        edgecolor="black",
        zorder=20,
    )
    ax.scatter(
        bchh["lon"],
        bchh["lat"],
        marker="o",
        s=145,
        c="black",
        edgecolor="black",
        zorder=20,
    )

    add_label(
        ax,
        slc40["lon"],
        slc40["lat"],
        "SLC-40",
        dx=0.00028,
        dy=0.00025,
    )
    add_label(
        ax,
        slc41["lon"],
        slc41["lat"],
        "SLC-41",
        dx=0.00028,
        dy=0.00025,
    )
    add_label(
        ax,
        bchh["lon"],
        bchh["lat"],
        "BCHH",
        dx=0.00035,
        dy=0.00015,
    )

    midlon = 0.5 * (slc40["lon"] + bchh["lon"])
    midlat = 0.5 * (slc40["lat"] + bchh["lat"])
    add_label(
        ax,
        midlon,
        midlat,
        f"{distance_m / 1000:.2f} km\naz. {azimuth_deg:.0f}°",
        dx=0.0010,
        dy=0.00015,
    )

    ax.text(
        -80.5920,
        28.5662,
        "Indian\nRiver\nLagoon",
        fontsize=8,
        color="tab:blue",
        style="italic",
        zorder=35,
    )
    ax.text(
        -80.5660,
        28.5640,
        "Atlantic\nOcean",
        fontsize=8,
        color="tab:blue",
        style="italic",
        zorder=35,
    )

    add_scalebar_lonlat(
        ax=ax,
        lon=lonlim[0] + 0.0065,
        lat=latlim[0] + 0.0043,
        length_m=1000,
        label_text="1 km",
        geod=geod,
    )
    add_north_arrow_axes(ax, xy=(0.93, 0.80), length=0.095)

    # Panel B: local BCHH sensor geometry
    ax = axes[1]
    ax.set_title("B", loc="left", fontsize=14, fontweight="bold")

    center_lon = bchh["lon"] + 0.00002
    center_lat = bchh["lat"] + 0.00010
    lonlim, latlim = equal_scale_lonlat_limits(
        center_lon,
        center_lat,
        width_lon=0.00090,
    )

    setup_dual_axes(
        ax=ax,
        lonlim=lonlim,
        latlim=latlim,
        ll_to_utm=ll_to_utm,
        utm_to_ll=utm_to_ll,
        lonfmt="%.5f",
        latfmt="%.5f",
        ylabel="",
        top_nbins=5,
        right_nbins=6,
    )
    set_equal_ground_aspect(ax)
    add_basemap(ax, provider="osm", alpha=0.72, zoom="auto")
    ax.set_xlim(lonlim)
    ax.set_ylim(latlim)

    infrasound = bchh_sensors[
        bchh_sensors["sensor"].str.startswith("HD")
    ]
    triangle = (
        infrasound.set_index("sensor")
        .loc[["HD1", "HD2", "HD3", "HD1"]]
    )
    ax.plot(
        triangle["lon"],
        triangle["lat"],
        color="0.45",
        lw=1.0,
        zorder=10,
    )

    for row in bchh_sensors.itertuples(index=False):
        if row.sensor == "Seismometer":
            ax.scatter(
                row.lon,
                row.lat,
                marker="s",
                s=145,
                c="black",
                edgecolor="black",
                zorder=20,
            )
        else:
            ax.scatter(
                row.lon,
                row.lat,
                marker="o",
                s=115,
                c="white",
                edgecolor="black",
                zorder=20,
            )

    label_offsets = {
        "HD1": (0.00001, 0.00003),
        "HD2": (0.000015, -0.00002),
        "HD3": (-0.00004, -0.00003),
        "Seismometer": (0.000015, 0.000035),
    }

    for row in bchh_sensors.itertuples(index=False):
        dx, dy = label_offsets[row.sensor]
        add_label(
            ax,
            row.lon,
            row.lat,
            row.label,
            dx=dx,
            dy=dy,
            size=8,
        )

    add_scalebar_lonlat(
        ax=ax,
        lon=lonlim[0] + 0.00015,
        lat=latlim[0] + 0.00007,
        length_m=30,
        label_text="30 m",
        geod=geod,
    )
    add_north_arrow_axes(ax, xy=(0.23, 0.80), length=0.10)

    legend_handles = [
        plt.Line2D(
            [],
            [],
            marker="s",
            ls="",
            ms=8,
            mfc="black",
            mec="black",
            label="Seismometer (3C)",
        ),
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            ms=8,
            mfc="white",
            mec="black",
            label="Infrasound (HD)",
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower right",
        fontsize=8,
        framealpha=0.9,
    )

    return fig, axes


def save_figure(
    fig,
    output_directory: str | Path,
    filename_stem: str,
    extensions=("png", "pdf"),
    dpi: int = 300,
) -> list[Path]:
    """Save one figure in each requested format and return output paths."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    output_paths = []
    for extension in extensions:
        path = output_directory / f"{filename_stem}.{extension}"
        fig.savefig(
            path,
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.05,
        )
        output_paths.append(path)

    return output_paths
