from flovopy.sds.write_sds_archive_multiprocessing import write_sds_archive
import os 
import glob
import traceback

def main():

    #src_dir='/raid/data/KennedySpaceCenter/beforePASSCAL/CONTINUOUS/2016'
    src_dir = '/data/KSC/duringPASSCAL/CENTAUR_DATA/change_days'
    dest_sds='/data/SDS_passcal_1'
    
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = "2016-01-01"      # e.g., "2020-01-01"
    end_date = "2026-01-10"        # e.g., "2022-01-01"


    file_list = sorted(glob.glob(os.path.join(src_dir, '*')))


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
            custom_file_list=file_list,
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