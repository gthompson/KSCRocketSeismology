#!/bin/bash
python compute_launch_peaks_physical.py \
  --events-csv all_florida_launches_with_seed_ids.csv \
  --stationxml /Users/glennthompson/Dropbox/KSC_RocketSeis_responses_computed.xml \
  --sds-root /Volumes/data/remastered/SDS_KSC \
  --pad-s 300 \
  --out launch_peaks_physical.csv