import sys
from obspy import read_inventory
from flovopy.stationmetadata.build import merge_inventories  # Adjust path as needed

def merge_and_patch_stationxml(input_file, output_file):
    """
    Read a StationXML file, merge and patch all overlapping or fragmented
    station/channel metadata, and write out a clean StationXML.

    Parameters:
    -----------
    input_file : str
        Path to input StationXML file.

    output_file : str
        Path to output StationXML file (merged and patched).
    """
    inv = read_inventory(input_file)
    patched = merge_inventories(inv)
    patched.write(output_file, format="stationxml")
    print(f"[SUCCESS] Merged and patched StationXML saved to:\n  {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python merge_and_patch_stationxml.py input.xml output.xml")
        sys.exit(1)

    merge_and_patch_stationxml(sys.argv[1], sys.argv[2])
