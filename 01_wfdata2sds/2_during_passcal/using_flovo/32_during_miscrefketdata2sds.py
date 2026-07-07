from flovopy.sds.write_sds_archive_multiprocessing import write_sds_archive
import os 
import glob
import traceback
import obspy 
def main():

    #src_dir='/raid/data/KennedySpaceCenter/beforePASSCAL/CONTINUOUS/2016'
    src_dir = '/data/KSC/duringPASSCAL/misc/reftekdata'
    dest_sds='/data/SDS_passcal_3'
    
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = "2016-01-01"      # e.g., "2020-01-01"
    end_date = "2026-01-10"        # e.g., "2022-01-01"



    file_list = []
    chans = 'Z12'
    mseeddir = '~/work/mseed_tmp_32'
    os.makedirs(mseeddir, exist_ok=True)

    for root, dirs, files in os.walk(src_dir):
        parts = root.split('/')
        if parts[-1]=='1':
            digitizer = parts[-2]
            yyyyjjj = parts[-3]
            for file in files:
                full_path = os.path.join(root, file)
                try:
                    st = obspy.read(full_path, format='REFTEK130')
                    for i, tr in enumerate(st):
                        tr.stats.network = '1R'
                        if 'BCHH' in tr.stats.station:
                            tr.stats.station = digitizer
                        if not 'EH' in tr.stats.channel:
                            tr.stats.channel = 'EH'+chans[i]
                        stime = tr.stats.starttime
                        etime = tr.stats.endtime
                        mseed = os.path.join(mseeddir, f"{tr.id}_{stime.strftime('%Y%m%d_%H%M%S')}_{etime.strftime('%H%M%S')}.mseed")
                        print(f'Writing {mseed}')
                        tr.write(mseed, format='MSEED')
                        file_list.append(mseed)
                except Exception as e:
                    print(e)
                    continue


    print(f"Found {len(file_list)} files.")

    

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