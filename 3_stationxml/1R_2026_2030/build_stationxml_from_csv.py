#!/usr/bin/env python3
"""
Build a StationXML inventory from a CSV containing station coordinates.

Expected CSV columns (case-sensitive, as written):
  - Site Name
  - Latitude
  - Longitude

Your rules:
  - Network code: 1R
  - Station code: from 'Site Name' (e.g., B01, B03, ...)
  - Always create seismic channels: DHZ, DH1, DH2
  - Create infrasound channels: DD1, DD2, DD3 for all stations EXCEPT B07, B12, B23

Defaults/Placeholders:
  - elevation, depth, sample_rate, and location_code are set below—edit them to match your deployment.
  - No instrument response metadata is added (you can add later via Response/Equipment if you have it).
"""

import argparse
import pandas as pd

from obspy.core.inventory import Inventory, Network, Station, Channel, Site


NETWORK_CODE = "1R"
NO_INFRASOUND = {"B07", "B12", "B23"}

# ---- Placeholder defaults (edit these!) ----
DEFAULT_ELEV_M = 0.0          # station elevation (meters)
DEFAULT_DEPTH_M = 0.0         # channel depth below surface (meters)
DEFAULT_SAMPLE_RATE = 100.0   # Hz
DEFAULT_LOC = ""            # SEED location code ("" is common)
# ------------------------------------------


def build_inventory_from_csv(csv_path: str) -> Inventory:
    df = pd.read_csv(csv_path)

    net = Network(
        code=NETWORK_CODE,
        description="Generated from station list CSV"
    )

    for _, row in df.iterrows():
        sta_code = str(row.get("Site Name", "")).strip()
        if not sta_code or sta_code.lower() == "nan":
            continue

        lat = row.get("Latitude", None)
        lon = row.get("Longitude", None)

        # Skip rows without valid coordinates
        if pd.isna(lat) or pd.isna(lon):
            continue

        station = Station(
            code=sta_code,
            latitude=float(lat),
            longitude=float(lon),
            elevation=DEFAULT_ELEV_M,
            site=Site(name=f"Site {sta_code}"),
        )

        # Seismic channels (always)
        for chan_code in ("DHZ", "DH1", "DH2"):
            station.channels.append(Channel(
                code=chan_code,
                location_code=DEFAULT_LOC,
                latitude=station.latitude,
                longitude=station.longitude,
                elevation=station.elevation,
                depth=DEFAULT_DEPTH_M,
                sample_rate=DEFAULT_SAMPLE_RATE,
            ))

        # Infrasound channels (most)
        if sta_code not in NO_INFRASOUND:
            for chan_code in ("DD1", "DD2", "DD3"):
                station.channels.append(Channel(
                    code=chan_code,
                    location_code=DEFAULT_LOC,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    elevation=station.elevation,
                    depth=DEFAULT_DEPTH_M,
                    sample_rate=DEFAULT_SAMPLE_RATE,
                ))

        net.stations.append(station)

    inv = Inventory(networks=[net], source="ObsPy generated StationXML")
    return inv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Input CSV path (must include Site Name, Latitude, Longitude)")
    ap.add_argument("--out", default="1R_stations.xml", help="Output StationXML filename")
    args = ap.parse_args()

    inv = build_inventory_from_csv(args.csv)
    inv.write(args.out, format="STATIONXML", validate=True)

    nsta = sum(len(n.stations) for n in inv.networks)
    print(f"Wrote {args.out} with {nsta} stations (network {NETWORK_CODE}).")


if __name__ == "__main__":
    main()
