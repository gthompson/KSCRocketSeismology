#!/usr/bin/env python3
import os
import sys
from flovopy.sds.write_sds_archive import write_sds_archive, check_for_collisions
import pandas as pd

def check_for_collisions(log_csv_path):
    # Load the log CSV file
    df = pd.read_csv(log_csv_path)

    # Count how many times each destination file appears
    dest_counts = df['destination_filepath'].value_counts()

    # Filter for collisions (i.e., more than one source per destination)
    collisions = dest_counts[dest_counts > 1]

    if not collisions.empty:
        print("⚠️ Filename collisions detected:")
        for dest_file in collisions.index:
            print(f"\nDestination: {dest_file}")
            sources = df[df['destination_filepath'] == dest_file]['source_filepath'].tolist()
            for src in sources:
                print(f"  ↳ {src}")
    else:
        print("✅ No filename collisions detected. Safe to proceed.")

def main():
    # Define input/output paths and metadata file
    #src_sds = "/data/SDS"
    #dest_sds = "/data/SDS_CONTINUOUS"
    src_sds='/raid/data/SDS'
    dest_sds='/data/SDS_NEWTON'
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"
    log_file = os.path.join(dest_sds,"raid_data_SDS.log")
    csv_log = os.path.join(dest_sds,"raid_data_SDS.csv")

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = None      # e.g., "2020-01-01"
    end_date = None        # e.g., "2022-01-01"
    write = True         # Set to False for dry-run


    # Call the function
    write_sds_archive(
        src_dir=src_sds,
        dest_dir=dest_sds,
        networks=networks,
        stations=stations,
        start_date=start_date,
        end_date=end_date,
        write=write,
        log_file=log_file,
        metadata_excel_path=excel_metadata_file,
        csv_log_path=csv_log,
        use_sds_structure=True,
        custom_file_list=None        
    )

    check_for_collisions(csv_log)

if __name__ == "__main__":
    main()