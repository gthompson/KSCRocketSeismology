# Beamforming animation cleanup

Keep:

- `animate_beamforming_demo.m`

Delete/archive:

- `animate_beamforming.m`
- `animate_beamforming_simple.m`

Reason:

- `animate_beamforming.m` appears incomplete and contains a bug: it uses `t2` before `t2` is defined in the circle plotting lines.
- `animate_beamforming_simple.m` is the more useful AGU-talk demo because it loops over back-azimuth and speed and can export PNG frames, but it is still workspace-dependent and writes `frame%03d` files in the current directory.
- The consolidated version preserves the useful demo behavior, adds name-value parameters, optional frame export to a chosen directory, basic input validation, and comments that distinguish this visualization from the real `falcon9.beamform2d` processing function.
