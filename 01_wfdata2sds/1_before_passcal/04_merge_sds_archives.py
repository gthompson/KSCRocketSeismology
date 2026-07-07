import os
import glob
from obspy import read, Stream
from flovopy.core.sds.SDS import SDSobj

def merge_sds_archives(src_dir, dest_dir):
    sds_src = SDSobj(src_dir)
    sds_dest = SDSobj(dest_dir)

    # Recursively find all MiniSEED files in the source SDS archive
    for src_path in glob.glob(os.path.join(src_dir, '**', '*.mseed'), recursive=True):
        try:
            st_src = read(src_path)
        except Exception as e:
            print(f"✘ Could not read {src_path}: {e}")
            continue

        for tr_src in st_src:
            try:
                dest_path = sds_dest.get_fullpath(tr_src)
                if os.path.exists(dest_path):
                    st_dest = read(dest_path)
                    st_combined = Stream(traces=[tr_src]) + st_dest
                    st_combined.merge(method=0, fill_value=None)
                    for tr in st_combined:
                        sds_dest.write(tr, overwrite=True)
                    print(f"✔ Merged: {tr_src.id} into {dest_path}")
                else:
                    sds_dest.write(tr_src, overwrite=False)
                    print(f"✔ Copied new: {tr_src.id} to {dest_path}")
            except Exception as e:
                print(f"✘ Error processing {src_path}: {e}")

# Example usage:
src_sds = "/data/SDS_EVENTS"
dest_sds = "/data/SDS_CONTINUOUS"
merge_sds_archives(src_sds, dest_sds)