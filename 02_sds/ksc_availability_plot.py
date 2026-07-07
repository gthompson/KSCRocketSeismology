# ksc_availability_plot.py
import os
from obspy.core.utcdatetime import UTCDateTime
from flovopy.sds.sds import SDSobj   # your class
import pandas as pd

# --- config ---
SDS_ROOT = "/data/remastered/SDS_KSC"
START = UTCDateTime("2019-01-01")    # <- change me
END   = UTCDateTime("2019-02-01")    # <- change me
OUT_PNG = "ksc_availability_2019-01.png"
OUT_CSV = "ksc_availability_2019-01.csv"

def main():
    sds = SDSobj(SDS_ROOT, sds_type="D", format="MSEED")

    # speed:
    #   1 -> read files, count samples (slowest, most accurate for nans)
    #   2 -> client.get_waveforms + merge (faster)
    #   3 -> client.get_availability_percentage (fastest, uses SDS client’s index)
    availability_df, trace_ids = sds.get_percent_availability(
        startday=START,
        endday=END,
        skip_low_rate_channels=True,
        trace_ids=None,         # or provide a curated list of NSLCs
        speed=3,                # start with 3; drop to 2/1 if you need stricter accuracy
        verbose=False,
        progress=True,
        merge_strategy="obspy",
        max_workers=8
    )

    # Save the raw matrix (percentages) if you want a record
    availability_df.to_csv(OUT_CSV, index=False)
    print(f"✅ Wrote CSV: {OUT_CSV}")

    # Plot (your method uses matplotlib under the hood)
    sds.plot_availability(
        availability_df,
        outfile=OUT_PNG,
        figsize=(14, 8),
        fontsize=9,
        labels=trace_ids,     # use same order as pivoted columns
        cmap="viridis"
    )
    print(f"✅ Wrote plot: {OUT_PNG}")

if __name__ == "__main__":
    main()