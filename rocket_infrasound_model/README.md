# Rocket Infrasound Model

A small starter package for modelling infrasound amplitudes and arrival times from an ascending, pitching rocket.

This first version models a rocket as a moving, directional acoustic source in a 2D vertical plane:

- horizontal coordinate `x` points east
- vertical coordinate `z` points up
- stations are fixed points `(x, z=0)`
- the rocket ascends, accelerates, and pitches eastward with time
- sound amplitude decays as `1 / distance`
- directivity is represented by a Gaussian cone around the exhaust axis
- observed time is emission time plus acoustic travel time

It predicts, for each station:

- peak arrival time
- peak amplitude
- full synthetic arrival-time / amplitude curves
- Doppler shift through time

See `example_usage.py` for a runnable example.
