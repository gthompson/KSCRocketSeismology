#!/usr/bin/env python3
#import os
#import sys
#import pandas as pd
#import glob
#import obspy
from flovopy.sds.write_sds_archive_multiprocessing import write_sds_archive
#from flovopy.sds.sds import SDSobj
#from flovopy.core.miniseed_io import smart_merge, read_mseed
#from pprint import pprint

def main():

    #src_dir='/raid/data/KennedySpaceCenter/beforePASSCAL/CONTINUOUS/2016'
    src_dir='/data/KSC/beforePASSCAL/CONTINUOUS'
    dest_sds='/data/SDS_KSC2'
    
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"
    #log_file = os.path.join(dest_sds,"raid_data_KSC_C.log")
    #csv_log = os.path.join(dest_sds,"raid_data_KSC_C.csv")

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = "2016-01-01"      # e.g., "2020-01-01"
    end_date = "2026-01-10"        # e.g., "2022-01-01"
    #write = True         # Set to False for dry-run

    #file_list = []
    '''
    TOP_INPUT_DIR = os.path.join(src_dir, '2016')
    sdsout = SDSobj(src_dir)
    for MMDIR in sorted(glob.glob(os.path.join(TOP_INPUT_DIR, '[0-9][0-9]'))):
        for DDDIR in sorted(glob.glob(os.path.join(MMDIR, '[0-9][0-9]'))):
            st = obspy.Stream()
            for f in sorted(glob.glob(os.path.join(DDDIR, '*FL*'))):
                print(f'\n\nReading {f}')
                #this_st = obspy.read(f)
                this_st = read_mseed(f)
                        
                for tr in this_st:
                    st.append(tr)
                #print(f'Unmerged Stream is now {st}')
            merged, report = smart_merge(st)
            pprint(report)
            print(f'Merged Stream is now {merged}')
            if report['status']=='ok':
                sdsout.stream = merged
                if sdsout.write(debug=True):
                    pass
                else:
                    raise IOError('Failed to write to SDS')
            else:
                # pprint(report)
                raise IOError('Bad status from smart_merge')


    
    write_sds_archive(
        src_dir=src_dir,
        dest_dir=dest_sds,
        networks=networks,
        stations=stations,
        start_date=start_date,
        end_date=end_date,
        write=write,
        log_file=log_file,
        metadata_excel_path=excel_metadata_file,
        csv_log_path=csv_log,
        use_sds_structure=False,
        custom_file_list=file_list          
    )

    check_for_collisions(csv_log)
    '''

    # Now process the 2016-8 data which is already in an SDS archive
    write_sds_archive(
        src_dir=src_dir,
        dest_dir=dest_sds,
        networks=networks,
        stations=stations,
        start_date=start_date,
        end_date=end_date,
        metadata_excel_path=excel_metadata_file,
        use_sds_structure=True,
        #custom_file_list=None,
        #recursive=True,
        #file_glob="*.mseed",
        n_processes=6,
        debug=False,                 
    )



    #check_for_collisions(csv_log)


if __name__ == "__main__":
    main()