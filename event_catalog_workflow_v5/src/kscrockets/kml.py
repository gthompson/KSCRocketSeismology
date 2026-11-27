"""KML of the pad table (data/raw/launchpads.csv) for checking coordinates in Google Earth/Maps.

    ksc-rockets launchpads-kml            # writes data/raw/launchpads.kml
"""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

# KML colours are aabbggrr
_STYLES = {"launch": ("ff0000ff", "http://maps.google.com/mapfiles/kml/shapes/triangle.png"),
           "landing": ("ffffaa00", "http://maps.google.com/mapfiles/kml/shapes/target.png")}


def launchpads_kml(pads: pd.DataFrame, name: str = "KSC / Cape Canaveral pads") -> str:
    """KML document with one labelled placemark per row (columns pad, lat, lon; optional kind, source)."""
    pads = pads.fillna("")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2">', "<Document>", f"<name>{escape(name)}</name>"]
    for kind, (colour, icon) in _STYLES.items():
        out.append(f'<Style id="{kind}"><IconStyle><color>{colour}</color><scale>1.1</scale>'
                   f"<Icon><href>{icon}</href></Icon></IconStyle>"
                   "<LabelStyle><scale>0.9</scale></LabelStyle></Style>")
    for r in pads.itertuples(index=False):
        kind = getattr(r, "kind", "") or ("landing" if str(r.pad).startswith("LZ") else "launch")
        desc = f"{float(r.lat):.6f}, {float(r.lon):.6f}"
        if getattr(r, "source", ""): desc += f"\n{r.source}"
        out.append(f"<Placemark><name>{escape(str(r.pad))}</name>"
                   f"<description>{escape(desc)}</description><styleUrl>#{kind}</styleUrl>"
                   f"<Point><coordinates>{float(r.lon):.6f},{float(r.lat):.6f},0</coordinates></Point></Placemark>")
    out += ["</Document>", "</kml>"]
    return "\n".join(out) + "\n"


def write_launchpads_kml(csv_path: str | Path, kml_path: str | Path | None = None) -> Path:
    csv_path = Path(csv_path)
    kml_path = Path(kml_path) if kml_path else csv_path.with_suffix(".kml")
    kml_path.write_text(launchpads_kml(pd.read_csv(csv_path, dtype={"pad": str})))
    return kml_path
