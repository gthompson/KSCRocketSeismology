import pandas as pd
from obspy import read, Stream
import matplotlib.pyplot as plt
import os
import json

from flovopy.core.miniseed_io import smart_merge, unmask_gaps
from flovopy.core.trace_utils import streams_equal
import numpy as np

def diagnose_conflict(conflict_csv_path):
    df = pd.read_csv(conflict_csv_path)
    if df.empty:
        print("❌ No rows found in the conflict file.")
        return

    for rownum,row in df.iterrows():
    
        print(row)
        source_file = row["source_file"]
        dest_file = row["dest_file"]
        rel_path = row["relative_path"]

        print(f"\n🔍 Diagnosing merge conflict for: {rel_path}")
        print(f"📄 Source file: {source_file}")
        print(f"📄 Dest file:   {dest_file}")

        if not os.path.exists(source_file):
            print("❌ Source file not found.")
            return

        print('\nSOURCE')
        st2 = read(source_file)
        summarize_stream(st2)


        if os.path.exists(dest_file):
            print('\nDESTINATION')
            st1 = read(dest_file)
            summarize_stream(st1)
        else:
            print("⚠️ Destination file does not exist. Skipping merge.")
            return

        # Attempt merge the usual way
        print('\nNORMAL MERGE')
        st_merged = st1 + st2
        report = smart_merge(st_merged)
        summarize_stream(st_merged)


        print(f"\n🧪 Merge Report:\n{json.dumps(report, indent=2)}")

        if report["status"] == "ok":
            print("✅ Merge OK")
        else:
            print("❌ Merge FAILED")
            #print("You may inspect `status_by_id` or merge reasons more closely.")

        # Attempt merge the max way
        print('\nMAX MERGE')
        st_merged2 = st1 + st2
        report = smart_merge(st_merged2, strategy='max')
        summarize_stream(st_merged2)

        print(f"\n🧪 Merge Report:\n{json.dumps(report, indent=2)}")

        if report["status"] == "ok":
            print("✅ Merge OK")
        else:
            print("❌ Merge FAILED")
            #print("You may inspect `status_by_id` or merge reasons more closely.")
            input()


            print('\nSee any differences between destination and merged')
            maxstime = max((st1[0].stats.starttime, st_merged[0].stats.starttime))
            minstime = min((st1[0].stats.endtime, st_merged[0].stats.endtime))
            st1.trim(starttime=maxstime, endtime=minstime)
            st_merged.trim(starttime=maxstime, endtime=minstime)
            tr_diff = st1[0].copy()
            tr_diff.data = st_merged[0].data - st1[0].data
            st1[0].plot()
            st2[0].plot()
            st_merged[0].plot()
            tr_diff.plot()
            print(f'merged vs st1: different in {np.count_nonzero(tr_diff.data)}')

            
            st_merged2.trim(starttime=maxstime, endtime=minstime)
            tr_diff2 = st1[0].copy()
            tr_diff2.data = st_merged2[0].data - st1[0].data    
            tr_diff2.plot()  
            print(f'merged2 vs st1: different in {np.count_nonzero(tr_diff2.data)}')
            print(f'merged2 vs merged: different in {np.count_nonzero(tr_diff.data-tr_diff2.data)}')

        input()
        print('\n**************\n')

def summarize_stream(st):
    def summarize(st):
        summary = []
        for tr in st:
            stats = tr.stats
            data = tr.data
            summary.append({
                "id": tr.id,
                "starttime": str(stats.starttime),
                "endtime": str(stats.endtime),
                "sampling_rate": stats.sampling_rate,
                "npts": stats.npts,
                "min": float(np.min(data)) if len(data) else None,
                "max": float(np.max(data)) if len(data) else None,
                "mean": float(np.mean(data)) if len(data) else None,
                "median": float(np.median(data)) if len(data) else None,
                "masked": hasattr(data, 'mask'),
                "zero_count": int(np.sum(data == 0)) if len(data) else None,
                "masked_count": np.ma.count_masked(data),
                "real_zero_count": np.sum(data == 0.0),

            })
            print(tr)
            print(summary)
            #tr.plot()
    summarize(st)
    print('After unmasking...')
    for tr in st:
        unmask_gaps(tr)
    summarize(st)

if __name__ == "__main__":
    diagnose_conflict("/data/SDS_KSC_v2/conflicts_unresolved_session_6.csv")
