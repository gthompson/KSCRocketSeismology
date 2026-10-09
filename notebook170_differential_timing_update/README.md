# Notebook 170 differential timing figure update

This bundle contains a complete updated copy of `170_generate_publication_figures.ipynb` with section 14 replaced by a differential timing comparison for the three later named events. The upper-stage event remains only as the zero-time reference.

The new figure places one reviewed USLaunchReport frame beside DD2 and DD3 pressure waveforms for each event. Blue and green marks show arrival times predicted by adding the within-camera event intervals (USLaunchReport and UCS-3, respectively) to each channel's reviewed upper-stage arrival. Red dashed marks show the independently reviewed DD2/DD3 arrival picks. Pressure is plotted in its existing units without per-trace normalization. The notebook also writes a frame audit and a CSV of camera-predicted minus observed intervals.

The timing inputs are transcribed from the reviewed tables in the current supplement. Principal-event bounds are shown as ranges; payload values are nominal reviewed picks, not uncertainty intervals. The predictions assume an unchanged acoustic path. A changing payload position or source-to-receiver path can contribute to residuals, so the figure should be described as a timing comparison under the linear same-path assumption.

Validation performed: notebook JSON parsed successfully and every code cell passed Python syntax compilation. The figure was not executed here because the original project notebook, waveform products, video, and configured project inputs are outside this writable workspace. The supplied notebook is a ready-to-copy replacement; the original at `/Users/thompsong/Developer/KSCRocketSeismology/08_fireball_paper/notebooks/170_generate_publication_figures.ipynb` was not overwritten.
