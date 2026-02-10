#!/bin/bash

python compute_launch_peaks_physical.py \
--events-csv all_florida_launches_with_seed_ids.csv \
--stationxml /Users/glennthompson/Dropbox/KSC_RocketSeis_responses_computed.xml \
--sds-root /Volumes/data/remastered/SDS_KSC \
--from 2016-02-20 --to 2022-12-05 \
--outdir event_outputs \
--index-out launch_metrics_index.csv \
--pad-s 60 \
-vv

#--stations "BCHH" \
#--channels "??Z,??N,??E,?D?" \