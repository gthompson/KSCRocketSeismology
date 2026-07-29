from __future__ import annotations

from pathlib import Path

import pandas as pd
from obspy import Inventory, UTCDateTime, read_inventory


def write_geometry_products(
    *,
    inventory: Inventory,
    channels_df: pd.DataFrame,
    stations_df: pd.DataFrame,
    locations_df: pd.DataFrame,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write standardized geometry products shared by analysis and Figure 1."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    paths = {
        "inventory": output_directory / "BCHH_20160901_event_inventory.xml",
        "channels": output_directory / "bchh_channels.csv",
        "stations": output_directory / "bchh_stations.csv",
        "locations": output_directory / "launchpad_camera_locations.csv",
    }
    inventory.write(str(paths["inventory"]), format="STATIONXML", validate=True)
    channels_df.to_csv(paths["channels"], index=False)
    stations_df.to_csv(paths["stations"], index=False)
    locations_df.to_csv(paths["locations"], index=False)
    return paths


def read_geometry_products(
    derived_directory: str | Path,
) -> tuple[Inventory, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read standardized geometry products written by Notebook 02."""
    derived_directory = Path(derived_directory)
    inventory = read_inventory(
        str(derived_directory / "BCHH_20160901_event_inventory.xml")
    )
    channels = pd.read_csv(derived_directory / "bchh_channels.csv")
    stations = pd.read_csv(derived_directory / "bchh_stations.csv")
    locations = pd.read_csv(
        derived_directory / "launchpad_camera_locations.csv"
    )
    return inventory, channels, stations, locations
