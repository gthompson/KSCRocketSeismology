from flovopy.sds.write_sds_archive_multiprocessing import write_sds_archive
import os 
import glob
import traceback
import obspy 
import os
import re


def find_mseed_files(prioritized_dirs):

    file_list = []

    for src_dir in prioritized_dirs:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                full_path = os.path.join(root, file)
                file_list.append(full_path)

    return file_list


def main():

    #src_dir='/raid/data/KennedySpaceCenter/beforePASSCAL/CONTINUOUS/2016'
    src_dir = '/data/KSC/duringPASSCAL/fake_mseed_dir'
    dest_sds='/data/SDS_passcal_all_mseed'
    
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = "2016-01-01"      # e.g., "2020-01-01"
    end_date = "2026-01-10"        # e.g., "2022-01-01"



    mseed_file_list = []
    chans = 'Z12'
   
    
    mseedlistfile = os.path.join('37_mseed_file_list.txt')


    if os.path.isfile(mseedlistfile):
        with open(mseedlistfile, "r") as f:
            mseed_file_list = [line.strip() for line in f]

    else:

        prioritized_dirs = [
            "/data/KSC/duringPASSCAL/CENTAUR_DATA/change_days", 
            "/data/KSC/duringPASSCAL/EVENTS", 
            "/data/KSC/duringPASSCAL/misc/obsolete/MSEED", 
            "/data/KSC/duringPASSCAL/misc2/DOWNLOAD/CENTAUR",
            "/data/KSC/duringPASSCAL/misc2/EVENTDB", 
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/DAYFILES",
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/MSEED", 
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/old/DAYFILES", 
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/old/MSEED", 
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/PASSCAL_backup/REFTEK_DATA/DAYFILES", 
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/PASSCAL_backup/REFTEK_DATA/MSEED", 
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/PASSCAL_backup/EVENTDB", 
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/PASSCAL_backup/REFTEK_DATA/MSEED0", 
            "/data/KSC/more_rocketdata/DAYS1",  
            "/data/KSC/duringPASSCAL/misc2/REFTEK_DATA/PASSCAL_backup/REFTEK_DATA/obsolete", 
            "/data/KSC/more_rocketdata/DAYSold", 
            "/data/KSC/more_rocketdata/MSEED", 
            "/data/KSC/more_rocketdata/MSEEDHOUR"
        ]


        mseed_file_list = find_mseed_files(prioritized_dirs)
        with open(mseedlistfile, "w") as f:
            for item in mseed_file_list:
                f.write(f"{item}\n")

    print(f"✅ Found {len(mseed_file_list)} MSEED files")

    try:
        write_sds_archive(
            src_dir=src_dir,
            dest_dir=dest_sds,
            networks=networks,
            stations=stations,
            start_date=start_date,
            end_date=end_date,
            metadata_excel_path=excel_metadata_file,
            use_sds_structure=False,
            custom_file_list=mseed_file_list,
            #recursive=True,
            #file_glob="*.mseed",
            n_processes=6,
            debug=True,                 
        )    
    except Exception as e:
        print(f'Outer most exception caught: {e}')
        traceback.print_exc()

    
if __name__ == "__main__":
    main()