# Experimental Notebook 155 diagnostics

Notebook 155 remains separate from production notebooks 060 and 070. It uses the configured input paths and writes analysis products under `PAPER_DIR/outputs/155_experimental_pressure_dhz_array/` when run in the project environment.

The added diagnostics are:

- `experimental_dd2_transfer_phase_coherence.png`: complex DD2-to-DHZ transfer phase and training coherence after the geometry-based DHZ advance.
- `experimental_steered_array_response_frequency_azimuth.png` and `experimental_steered_array_response_polar.png`: the exact three-microphone response for the SLC-40 steering delays, across frequency and azimuth.
- `experimental_quiet_beam_noise_reduction.png`: measured pressure power in the aligned three-sensor beam relative to DD2 during pre-event and other quiet windows. CSV files contain the band summary and spectra.

In these quiet windows, the beam's median power exceeded DD2 by about 13 dB at 1–3 Hz, 9–11 dB at 3.5–10 Hz, and 4–6 dB at 10–25 Hz; it approached DD2 at 25–40 Hz. Thus the current aligned beam does not suppress background relative to the clean DD2 channel. The −4.77 dB reference applies only to three equal, independent noise sources and is not a prediction for this site.

The surveyed channel coordinates span 39.5 m at their widest pair, despite the nominal ~30 m array aperture. The 12 Hz wavelength/aperture comparison is therefore only a rough scale; the computed response map shows the actual directional lobes and ambiguity. The map does not imply a sharp frequency cutoff.

DHZ is advanced by the SLC-40 differential travel time (currently 0.03290 s) before transfer estimation. The residual includes direct seismic motion, noise, and transfer error; it is not by itself an estimate of direct-seismic energy. The present held-out prediction scores do not support adding a quantitative transfer or direct-wave claim to the paper.
