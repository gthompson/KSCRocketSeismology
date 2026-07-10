from pathlib import Path
from xml.etree import ElementTree as ET


def read_kml_points(kml_file: str | Path) -> dict[str, dict]:
    """
    Read all Point placemarks from a KML file.

    Returns
    -------
    dict
        Dictionary keyed by placemark name. Each value contains:
        name, lat, lon, and altitude_m.
    """
    kml_file = Path(kml_file)

    if not kml_file.exists():
        raise FileNotFoundError(f"KML file not found: {kml_file}")

    namespace = {"kml": "http://www.opengis.net/kml/2.2"}

    root = ET.parse(kml_file).getroot()
    points = {}

    for placemark in root.findall(".//kml:Placemark", namespace):
        name = placemark.findtext("kml:name", namespaces=namespace)

        coordinates_text = placemark.findtext(
            ".//kml:Point/kml:coordinates",
            namespaces=namespace,
        )

        # Skip placemarks that are not named points.
        if not name or not coordinates_text:
            continue

        values = coordinates_text.strip().split(",")

        if len(values) < 2:
            raise ValueError(
                f"Unexpected coordinates for placemark {name!r}: "
                f"{coordinates_text!r}"
            )

        # KML coordinate order is longitude, latitude, altitude.
        lon = float(values[0])
        lat = float(values[1])
        altitude_m = float(values[2]) if len(values) >= 3 else None

        points[name] = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "altitude_m": altitude_m,
        }

    return points