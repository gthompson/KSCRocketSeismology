import pandas as pd
import math
import traceback
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
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
    # Add global time slider limits (optional)
    global_timespan = SubElement(doc, "TimeSpan")
    SubElement(global_timespan, "begin").text = "2016-02-05"
    SubElement(global_timespan, "end").text = "2022-12-06"
    rows_for_csv = []

    seismic_folder = SubElement(doc, "Folder")
    SubElement(seismic_folder, "name").text = "Seismic Stations"

    infra_folder = SubElement(doc, "Folder")
    SubElement(infra_folder, "name").text = "Infrasound Stations"

    features_folder = SubElement(doc, "Folder")
    SubElement(features_folder, "name").text = "Infrastructure Features"

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

    infra_coords = []
    for _, row in infra_df.iterrows():
        try:
            name = row["Feature"]
            lat = float(row["Latitude"])
            lon = float(str(row["Longitude"]).replace("*", ""))
            infra_coords.append((name, lat, lon))
        except Exception:
            continue
    for feat_name, feat_lat, feat_lon in infra_coords:
        description = f"Feature: {feat_name}"
        style_url = f"#{styles['infrastructure'][0]}"
        placemark = create_placemark(feat_name, feat_lat, feat_lon, description, style_url)
        features_folder.append(placemark)

    for _, row in stations_df.iterrows():
        try:
            net, sta, loc, chan = row["network"], row["station"], row["location"], row["channel"]
            seed_id = f"{net}.{sta}.{loc}.{chan}"
            ondate = pd.to_datetime(row["ondate"]).strftime("%Y-%m-%d")
            offdate = pd.to_datetime(row["offdate"]).strftime("%Y-%m-%d") if pd.notnull(row["offdate"]) else "2030-01-01"
            name = f"{seed_id}_{ondate.replace('-', '/')}"
            lat = float(row["lat"])
            lon = float(str(row["lon"]).replace("*", ""))
            style_key = "seismic" if chan[1] in "HN" else "infrasound" if chan[1] == "D" else "unknown"
            style_url = f"#{styles[style_key][0]}"

            desc_lines = [f"{col}: {row[col]}" for col in stations_df.columns if pd.notnull(row[col])]
            csv_row = row.to_dict()
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
                doc.append(placemark)  # fallback
            rows_for_csv.append(csv_row)

        except Exception as e:
            print(f"Skipped a row due to error: {e}")
            traceback.print_exc()
            print(f"row was {row}")
            print()
            continue

    # Save KML
    kml_str = parseString(tostring(kml)).toprettyxml(indent="  ")
    with open(kml_output_path, "w") as f:
        f.write(kml_str)

    # Save CSV
    pd.DataFrame(rows_for_csv).to_csv(csv_output_path, index=False)

# === Example usage ===
if __name__ == "__main__":
    import os
    homedir = os.path.expanduser('~')
    metadata_dir = os.path.join(homedir, "Dropbox/DATA/station_metadata")
    excel_path = os.path.join(metadata_dir, "ksc_stations_master_v2.xlsx")
    output_kml = excel_path.replace('.xlsx', '.kml') 
    output_csv = output_kml.replace('.kml', '_with_distances.csv')

    # Load data
    xls = pd.ExcelFile(excel_path)
    stations_df = xls.parse("ksc_stations_master")
    infra_df = xls.parse("infrastructure")

    # Create KML

    create_kml_and_csv(
        stations_df,
        infra_df,
        output_kml,
        output_csv
    )