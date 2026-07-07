from flovopy.sds.write_sds_archive_multiprocessing import write_sds_archive

def main():

    #src_dir='/raid/data/KennedySpaceCenter/beforePASSCAL/CONTINUOUS/2016'
    src_dir='/data/KSC/beforePASSCAL/CONTINUOUS'
    dest_sds='/data/SDS_dailyKSChal_v2'
    
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = "2016-01-01"      # e.g., "2020-01-01"
    end_date = "2026-01-10"        # e.g., "2022-01-01"

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

if __name__ == "__main__":
    main()
