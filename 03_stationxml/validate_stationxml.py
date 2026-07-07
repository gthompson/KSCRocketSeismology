# Example usage:
if __name__ == "__main__":
    from obspy import read_inventory
    from flovopy.stationmetadata.utils import validate_inventory
    stationxml_file = sys.argv[1] if len(sys.argv) > 1 else "station.xml"

    inv = read_inventory(stationxml_file)
    issues = validate_inventory(inv)

    if issues:
        print(f"\nFound {len(issues)} issues.")
    else:
        print("✅ Inventory is clean.")