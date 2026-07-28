
"""Read and write standardized geometry products."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
from obspy import read_inventory


def write_geometry_products(
    *,
    inventory,
    channels_df,
    stations_df,
    locations_df,
    output_directory,
    prefix="",
):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    prefix = f"{prefix}_" if prefix and not str(prefix).endswith("_") else str(prefix)

    paths = {
        "inventory": output_directory / f"{prefix}event_inventory.xml",
        "channels": output_directory / f"{prefix}geometry_channels.csv",
        "stations": output_directory / f"{prefix}geometry_stations.csv",
        "locations": output_directory / f"{prefix}geometry_locations.csv",
    }

    inventory.write(str(paths["inventory"]), format="STATIONXML", validate=True)
    channels_df.to_csv(paths["channels"], index=False)
    stations_df.to_csv(paths["stations"], index=False)
    locations_df.to_csv(paths["locations"], index=False)
    return paths


def read_geometry_products(output_directory, prefix=""):
    output_directory = Path(output_directory)
    prefix = f"{prefix}_" if prefix and not str(prefix).endswith("_") else str(prefix)

    inventory = read_inventory(output_directory / f"{prefix}event_inventory.xml")
    channels = pd.read_csv(output_directory / f"{prefix}geometry_channels.csv")
    stations = pd.read_csv(output_directory / f"{prefix}geometry_stations.csv")
    locations = pd.read_csv(output_directory / f"{prefix}geometry_locations.csv")
    return inventory, channels, stations, locations
