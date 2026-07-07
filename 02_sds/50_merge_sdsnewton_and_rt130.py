from flovopy.sds.merge_sds import merge_multiple_sds_archives

source_sds_dirs = [
'/raid/data/SDS_KSC_newton', 
'/data/SDS_passcal_all_rt130', 
]
dest_sds_dir = '/data/SDS_KSC_newton_rt130'

merge_multiple_sds_archives(source_sds_dirs, dest_sds_dir, 
                            db_path="merge_tracking.sqlite", 
                            merge_strategy='obspy')