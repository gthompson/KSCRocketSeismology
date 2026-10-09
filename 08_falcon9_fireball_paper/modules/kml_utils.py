"""General utilities for reading geographic points from KML files."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET


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
