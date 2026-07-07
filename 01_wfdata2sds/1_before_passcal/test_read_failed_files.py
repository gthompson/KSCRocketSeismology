import pandas as pd
from obspy import read
import os

def try_read_and_plot_failed_files(excel_path):
    """
    Attempts to read and plot waveform files listed as 'failed' in a spreadsheet.

    Parameters
    ----------
    excel_path : str
        Path to an .xlsx or .csv file containing columns: filepath, status, etc.
    """
    df = pd.read_excel(excel_path)
    failed_df = df[df["status"].str.lower() == "failed"]

    '''
    for _, row in failed_df.iterrows():
        print('')
        filepath = row["filepath"]
        try:
            st = read(filepath)
            print(f"✅ Successfully read: {filepath}")
            print(st)
            outfile = os.path.join('/home/thompsong/work', os.path.basename(filepath) + ".png")
            st.plot(equal_scale=False, outfile=outfile)
            print(f"🖼️  Saved plot to {outfile}")
        except Exception as e:
            print(f"❌ Failed to read {filepath}: {e}")
    '''
    return failed_df['filepath'].to_list()



from flovopy.sds.write_sds_archive_multiprocessing import write_sds_archive
import os 
import glob
import traceback

def main():

    #src_dir='/raid/data/KennedySpaceCenter/beforePASSCAL/CONTINUOUS/2016'
    src_dir = '/data/KSC/event_files_to_convert_to_sds'
    dest_sds='/data/SDS_failedeventKSChal'
    
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = "2016-01-01"      # e.g., "2020-01-01"
    end_date = "2026-01-10"        # e.g., "2022-01-01"





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

file_list =  sorted(try_read_and_plot_failed_files('/data/SDS_eventKSChal/processing_log.xlsx'))
main()