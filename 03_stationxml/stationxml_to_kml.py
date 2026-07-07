# stationxml_to_kml.py
import os
import math
import traceback
import pandas as pd
from obspy import read_inventory
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString


# ---------- helpers from your original ----------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def create_placemark(name, lat, lon, description, style_url, ondate=None, offdate=None):
    placemark = Element("Placemark")
    SubElement(placemark, "name").text = name
    SubElement(placemark, "description").text = description
    SubElement(placemark, "styleUrl").text = style_url
    if ondate and offdate:
        timespan = SubElement(placemark, "TimeSpan")
        SubElement(timespan, "begin").text = ondate
        SubElement(timespan, "end").text = offdate
    point = SubElement(placemark, "Point")
    SubElement(point, "coordinates").text = f"{lon},{lat},0"
    return placemark

def create_kml_and_csv(stations_df, infra_df, kml_output_path, csv_output_path, speed_of_sound=343.0):
    kml = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = SubElement(kml, "Document")

    # Global time slider (kept identical to your Excel version)
    global_timespan = SubElement(doc, "TimeSpan")
    SubElement(global_timespan, "begin").text = "2016-02-05"
    SubElement(global_timespan, "end").text = "2022-12-06"

    rows_for_csv = []

    seismic_folder = SubElement(doc, "Folder"); SubElement(seismic_folder, "name").text = "Seismic Stations"
    infra_folder = SubElement(doc, "Folder");   SubElement(infra_folder, "name").text = "Infrasound Stations"
    features_folder = SubElement(doc, "Folder");SubElement(features_folder, "name").text = "Infrastructure Features"

    styles = {
        "seismic": ("seismicStyle", "ff0000ff"),
        "infrasound": ("infraStyle", "ffff0000"),
        "infrastructure": ("infraStructStyle", "ff00ff00"),
    }
    for style_id, color in styles.values():
        style = SubElement(doc, "Style", id=style_id)
        icon_style = SubElement(style, "IconStyle")
        SubElement(icon_style, "color").text = color
        icon = SubElement(icon_style, "Icon")
        SubElement(icon, "href").text = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"

    # Optional infrastructure features (can be empty)
    infra_coords = []
    if infra_df is not None and not infra_df.empty:
        for _, row in infra_df.iterrows():
            try:
                name = row.get("Feature") or row.get("name") or row.get("feature")
                lat = float(row.get("Latitude") or row.get("lat"))
                lon = float(str(row.get("Longitude") or row.get("lon")).replace("*", ""))
                infra_coords.append((name, lat, lon))
            except Exception:
                continue
        for feat_name, feat_lat, feat_lon in infra_coords:
            description = f"Feature: {feat_name}"
            style_url = f"#{styles['infrastructure'][0]}"
            placemark = create_placemark(feat_name, feat_lat, feat_lon, description, style_url)
            features_folder.append(placemark)

    # Stations
    for _, row in stations_df.iterrows():
        try:
            net, sta, loc, chan = row["network"], row["station"], row["location"], row["channel"]
            seed_id = f"{net}.{sta}.{loc}.{chan}"
            ondate = pd.to_datetime(row["ondate"]).strftime("%Y-%m-%d")
            off_raw = row.get("offdate")
            offdate = pd.to_datetime(off_raw).strftime("%Y-%m-%d") if pd.notnull(off_raw) and str(off_raw) != "" else "2030-01-01"
            name = f"{seed_id}_{ondate.replace('-', '/')}"

            lat = float(row["lat"])
            lon = float(str(row["lon"]).replace("*", ""))

            # Match your original style logic: H/N = seismic, D = infrasound
            style_key = "seismic" if len(chan) > 1 and chan[1] in "HN" else ("infrasound" if len(chan) > 1 and chan[1] == "D" else "seismic")
            style_url = f"#{styles[style_key][0]}"

            # Description mirrors the "all columns" dump in your Excel flow
            desc_lines = []
            for col in stations_df.columns:
                val = row.get(col)
                if pd.notnull(val):
                    desc_lines.append(f"{col}: {val}")

            csv_row = row.to_dict()

            # Distances to infrastructure features
            for feat_name, feat_lat, feat_lon in infra_coords:
                dist_m = haversine_distance(lat, lon, feat_lat, feat_lon)
                time_s = dist_m / speed_of_sound
                desc_lines.append(f"{feat_name}: {int(dist_m)} m ({time_s:.1f} s)")
                csv_row[f"dist_to_{feat_name}"] = int(dist_m)
                csv_row[f"time_to_{feat_name}"] = round(time_s, 1)

            description = "\n".join(desc_lines)
            placemark = create_placemark(name, lat, lon, description, style_url, ondate, offdate)

            if style_key == "seismic":
                seismic_folder.append(placemark)
            elif style_key == "infrasound":
                infra_folder.append(placemark)
            else:
                doc.append(placemark)

            rows_for_csv.append(csv_row)

        except Exception as e:
            print(f"Skipped a row due to error: {e}")
            traceback.print_exc()
            print(f"row was {row}\n")
            continue

    # Save KML
    kml_str = parseString(tostring(kml)).toprettyxml(indent="  ")
    with open(kml_output_path, "w") as f:
        f.write(kml_str)

    # Save CSV
    pd.DataFrame(rows_for_csv).to_csv(csv_output_path, index=False)


# ---------- StationXML ➜ DataFrame ----------
def inventory_to_dataframe(inv):
    """
    Flatten ObsPy Inventory -> rows like your Excel sheet:
    columns: network, station, location, channel, ondate, offdate, lat, lon, elev, sitename, etc.
    One row per channel epoch (so TimeSpan works like before).
    """
    rows = []
    for net in inv.networks:
        ncode = net.code
        for sta in net.stations:
            scode = sta.code
            slat = sta.latitude
            slon = sta.longitude
            selev = sta.elevation
            sname = (sta.site.name or "").strip() if sta.site else ""
            s_on = sta.start_date
            s_off = sta.end_date

            # If no channels, still emit a station row with blanks for chan/loc
            if not sta.channels:
                rows.append({
                    "network": ncode,
                    "station": scode,
                    "location": "--",
                    "channel": "???",
                    "ondate": str(s_on.date()) if s_on else "2000-01-01",
                    "offdate": str(s_off.date()) if s_off else "",
                    "lat": slat, "lon": slon, "elev_m": selev,
                    "site_name": sname, "sample_rate": "",
                    "azimuth": "", "dip": ""
                })
                continue

            for ch in sta.channels:
                loc = ch.location_code or "--"
                ccode = ch.code
                c_on = ch.start_date or s_on
                c_off = ch.end_date or s_off

                rows.append({
                    "network": ncode,
                    "station": scode,
                    "location": loc if loc != "-" else "--",
                    "channel": ccode,
                    "ondate": str(c_on.date()) if c_on else "2000-01-01",
                    "offdate": str(c_off.date()) if c_off else "",
                    "lat": ch.latitude if ch.latitude is not None else slat,
                    "lon": ch.longitude if ch.longitude is not None else slon,
                    "elev_m": ch.elevation if ch.elevation is not None else selev,
                    "site_name": sname,
                    "sample_rate": getattr(ch, "sample_rate", ""),
                    "azimuth": getattr(ch, "azimuth", ""),
                    "dip": getattr(ch, "dip", "")
                })
    return pd.DataFrame(rows)


# ---------- CLI-ish example ----------
if __name__ == "__main__":
    # INPUTS
    home = os.path.expanduser("~")
    metadata_dir = os.path.join(home, "Dropbox", "DATA", "station_metadata")
    stationxml_path = os.path.join(metadata_dir, "KSC2.xml")  # change as needed

    # Optional infrastructure sheet (same as your Excel workflow)
    infra_path = os.path.join(metadata_dir, "ksc_stations_master_v2.xlsx")
    infra_sheet = "infrastructure"  # or None if you don't want distances

    # OUTPUTS
    base = os.path.splitext(stationxml_path)[0]
    output_kml = base + "from_stationxml.kml"
    output_csv = base + "from_stationxml_with_distances.csv"

    # Load StationXML -> DF
    inv = read_inventory(stationxml_path)
    stations_df = inventory_to_dataframe(inv)

    # Load infrastructure features (optional)
    infra_df = None
    if os.path.exists(infra_path):
        try:
            xls = pd.ExcelFile(infra_path)
            infra_df = xls.parse(infra_sheet)
        except Exception:
            infra_df = None

    # Generate KML/CSV with the same logic/styles as your Excel flow
    create_kml_and_csv(stations_df, infra_df, output_kml, output_csv)

    print(f"✅ Wrote KML: {output_kml}")
    print(f"✅ Wrote CSV: {output_csv}")