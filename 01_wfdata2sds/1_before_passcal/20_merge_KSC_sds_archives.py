from flovopy.sds.merge_sds import merge_multiple_sds_archives
#import os 
#import glob
import traceback

def main():

    source_sds_dirs = [
        '/data/SDS_dailyKSChal_v2',
        '/data/SDS_hourlyKSChal_v2',
        '/data/SDS_eventKSChal_v2'
    ]

    dest_sds_dir = '/data/SDS_KSC_v3'
    

    try:
        merge_multiple_sds_archives(source_sds_dirs, dest_sds_dir)               
    except Exception as e:
        print(f'Outer most exception caught: {e}')
        traceback.print_exc()

    source_sds_dirs_u = [
        '/data/SDS_dailyKSChal_v2/unmatched',
        '/data/SDS_hourlyKSChal_v2/unmatched',
        '/data/SDS_eventKSChal_v2/unmatched'
    ]

    dest_sds_dir_u = '/data/SDS_KSC_v2/unmatched'
    

    try:
        merge_multiple_sds_archives(source_sds_dirs_u, dest_sds_dir_u)               
    except Exception as e:
        print(f'Outer most exception caught: {e}')
        traceback.print_exc()


if __name__ == "__main__":
    main()

