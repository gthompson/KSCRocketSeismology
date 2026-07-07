from flovopy.sds.write_sds_archive_multiprocessing import write_sds_archive
import os 
import glob
import traceback
import obspy 
import os
import re


def find_unique_reftek130_files(prioritized_dirs, check_size=True):
    """
    Walks multiple directories in order, adding only unique YYYYJJJ/4CHAR/1/filename entries,
    with optional duplicate content checking by file size.

    Parameters
    ----------
    prioritized_dirs : list of str
        Ordered list of root directories to walk, with higher priority ones first.

    check_size : bool
        If True, keep multiple copies of files with same path key but different size.

    Returns
    -------
    reftek_files : list of str
        List of full paths to uniquely identified REFTEK130 files.
    """
    yyyyddd_pattern = re.compile(r"^\d{7}$")
    fourchar_pattern = re.compile(r"^[A-Z0-9]{4}$")

    seen = {}  # key = (yyyyjjj, fourchar, fname), value = set of file sizes
    reftek_files = []

    for root_dir in prioritized_dirs:
        for dirpath, _, filenames in os.walk(root_dir):
            parts = os.path.normpath(dirpath).split(os.sep)

            if len(parts) >= 3:
                yyyyjjj = parts[-3]
                fourchar = parts[-2]
                subdir = parts[-1]

                if (
                    yyyyddd_pattern.match(yyyyjjj)
                    and fourchar_pattern.match(fourchar.upper())
                    and subdir == "1"
                ):
                    for fname in filenames:
                        full_path = os.path.join(dirpath, fname)
                        file_key = (yyyyjjj, fourchar.upper(), fname)
                        try:
                            file_size = os.path.getsize(full_path)
                        except Exception as e:
                            print(f"⚠️ Could not access {full_path}: {e}")
                            continue

                        if file_key not in seen:
                            seen[file_key] = {file_size}
                            reftek_files.append(full_path)
                        elif check_size and file_size not in seen[file_key]:
                            seen[file_key].add(file_size)
                            reftek_files.append(full_path)
                        # else: duplicate, skip it

    return reftek_files


def main():

    #src_dir='/raid/data/KennedySpaceCenter/beforePASSCAL/CONTINUOUS/2016'
    src_dir = '/data/KSC/duringPASSCAL/misc/reftekdata'
    dest_sds='/data/SDS_passcal_all_rt130'
    
    excel_metadata_file = "/home/thompsong/Dropbox/DATA/station_metadata/ksc_stations_master_v2.xls"

    # Optional filtering parameters (customize if needed)
    networks =  ['AM', '1R', 'XA', 'FL']
    stations = '*'
    start_date = "2016-01-01"      # e.g., "2020-01-01"
    end_date = "2026-01-10"        # e.g., "2022-01-01"



    mseed_file_list = []
    chans = 'Z12'
    mseeddir = '/home/thompsong/work/mseed_tmp_36'
    listfile = os.path.join(mseeddir, '36_rt130_file_list.txt')
    mseedlistfile = os.path.join(mseeddir, '36_mseed_file_list.txt')
    os.makedirs(mseeddir, exist_ok=True)

    if os.path.isfile(listfile):
        with open(listfile, "r") as f:
            rt130_file_list = [line.strip() for line in f]

    else:

        prioritized_dirs = [
            "/home/thompsong/work/PROJECTS/KSCpasscal/10_ORGANIZED/RAW",
            "/home/thompsong/work/PROJECTS/KSCpasscal",
            "/data/KSC/duringPASSCAL"
        ]


        rt130_file_list = find_unique_reftek130_files(prioritized_dirs)
        with open(listfile, "w") as f:
            for item in rt130_file_list:
                f.write(f"{item}\n")

    print(f"✅ Found {len(rt130_file_list)} unique REFTEK130 files")








    if os.path.isfile(mseedlistfile):
        with open(listfile, "r") as f:
            mseed_file_list = [line.strip() for line in f]

    else:

        numfiles = len(rt130_file_list)
        for filenum, full_path in enumerate(rt130_file_list):
            print(f'Processing {filenum+1} of {numfiles}')
            parts = full_path.split('/')
            if parts[-2]=='1':
                digitizer = parts[-3]
                yyyyjjj = parts[-4]
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
                    if os.path.isfile(mseed):
                        mseed = mseed.replace('.mseed', obspy.UTCDateTime().strftime('%S') + '.mseed')
                    print(f'Writing {mseed}')
                    tr.write(mseed, format='MSEED')
                    mseed_file_list.append(mseed)
            except Exception as e:
                print(e)
                continue


        with open(mseedlistfile, "w") as f:
            for item in mseed_file_list:
                f.write(f"{item}\n")

    print(f"Found {len(mseed_file_list)} files.")

    

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