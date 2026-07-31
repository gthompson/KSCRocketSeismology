#!/bin/bash
FIGDIR=/Users/thompsong/Developer/KSCRocketSeismology/08_fireball_paper/writing/latex/figures/
mkdir $FIGDIR

# Association-window sensitivity:  
cp  /Users/thompsong/Library/CloudStorage/Box-Box/thompsong/3_Project_Documents/NASAprojects/201602_Rocket_Seismology/writing/spacex_paper/data/figures/04_reduced_time_event_count_vs_window.png $FIGDIR

# Event-centred Bartlett validation:  
cp  /Users/thompsong/Library/CloudStorage/Box-Box/thompsong/3_Project_Documents/NASAprojects/201602_Rocket_Seismology/writing/spacex_paper/data/figures/S03_infrapy_bartlett_validation/S03_event_centred_bartlett_validation.png $FIGDIR

# Blind continuous Bartlett scan:  
cp  /Users/thompsong/Library/CloudStorage/Box-Box/thompsong/3_Project_Documents/NASAprojects/201602_Rocket_Seismology/writing/spacex_paper/data/figures/S03_infrapy_bartlett_validation_cont/S03_continuous_full_beam_results.png $FIGDIR

# The continuous-run directory also contains its own copy of the event-centred figure:
cp /Users/thompsong/Library/CloudStorage/Box-Box/thompsong/3_Project_Documents/NASAprojects/201602_Rocket_Seismology/writing/spacex_paper/data/figures/S03_infrapy_bartlett_validation_cont/S03_event_centred_bartlett_validation.png $FIGDIR