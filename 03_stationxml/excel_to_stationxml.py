import os
import platform

from flovopy.stationmetadata.infrabsu import get_infrabsu_sensor_template
from flovopy.stationmetadata.wrapper import get_stationXML_inventory
from flovopy.stationmetadata.convert import inventory2dataless_and_resp

# === Define metadata paths ===
home = os.path.expanduser("~")
system = platform.system()

# Use Dropbox path on macOS; otherwise default to /data
metadata_dir = (
    os.path.join(home, "Dropbox", "DATA", "station_metadata")
)
# Not sure where the Dropbox data are now, but this is an older version on hal9000 where /data -> /Volumes/classdata
metadata_dir = "/Volumes/classdata/KSC/EROSION/station_metadata"
os.makedirs(metadata_dir, exist_ok=True)

# Define all relevant paths
xml_file = os.path.join(metadata_dir, "KSC3.xml")
resp_dir = os.path.join(metadata_dir, "RESP3")
nrl_path = None  # keep None to use remote NRL (NRLv1 online)
metadata_excel = os.path.join(metadata_dir, "ksc_stations_master_v2.xlsx")
stationxml_converter_jar = os.path.join(home, "bin", "stationxml-seed-converter.jar")

# Ensure output directories exist
os.makedirs(resp_dir, exist_ok=True)

# === Ensure infraBSU sensor template is cached locally ===
# This returns the path under flovopy/stationmetadata/stationxml_templates/
infraBSU_xml = str(get_infrabsu_sensor_template())

# === Build full inventory with response ===
print("\n### Building full inventory with responses ###")
try:
    inventory = get_stationXML_inventory(
        xmlfile=xml_file,
        excel_file=metadata_excel,
        sheet_name="ksc_stations_master",
        infrabsu_xml=infraBSU_xml,  # use the cached template
        nrl_path=nrl_path,
        overwrite=True,
        verbose=True,
    )
except Exception as e:
    print(f"[ERROR] Failed to build inventory: {e}")
    inventory = None

if inventory:
    print(f"\n\n********\nFinal inventory: {inventory}")

    exit()

    # === Export to dataless SEED + RESP format ===
    print("\n### Exporting to dataless SEED and RESP ###")
    try:
        inventory2dataless_and_resp(
            inventory,
            output_dir=resp_dir,
            stationxml_seed_converter_jar=stationxml_converter_jar,
        )
    except Exception as e:
        print(f"[ERROR] Failed to export to dataless SEED and RESP: {e}")
    else:
        print(f"[INFO] Successfully exported to {resp_dir}")
else:
    print("[ERROR] No inventory available to export.")