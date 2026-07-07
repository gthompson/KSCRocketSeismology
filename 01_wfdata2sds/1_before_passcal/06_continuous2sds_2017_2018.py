from flovopy.sds.write_sds_archive_multiprocessing import process_partial_file_list
from obspy import UTCDateTime
import os

dest_sds='/data/SDS_KSC3'

excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"
#log_file = os.path.join(dest_sds,"raid_data_KSC_C.log")
#csv_log = os.path.join(dest_sds,"raid_data_KSC_C.csv")

# Optional filtering parameters (customize if needed)
networks =  ['AM', '1R', 'XA', 'FL']
stations = ['*']
start_date = UTCDateTime("2016-02-01")      # e.g., "2020-01-01"
end_date = UTCDateTime("2026-01-01")        # e.g., "2022-01-01"

unprocessed_dir = os.path.join(dest_sds, 'temp_sds_0', 'unprocessed')
custom_file_list = [
    os.path.join(unprocessed_dir, f)
    for f in os.listdir(unprocessed_dir)
    if os.path.isfile(os.path.join(unprocessed_dir, f))
]
print(custom_file_list)
#file_list = [os.path.join(dest_sds, 'temp_sds_0', 'unprocessed', 'FL.BCHH.00.HD1.D.2016.244')]
temp_dest = os.path.join(dest_sds, 'dummy')
debug = True

process_partial_file_list(custom_file_list, temp_dest, networks, stations, start_date, end_date, debug, excel_metadata_file)