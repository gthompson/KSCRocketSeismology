# Rocket ascent and Doppler toy models

This folder refactors the legacy standalone scripts:

- `rocketsimulation1d.m`
- `rocketsimulation2d.m`

into reusable MATLAB functions in `+rocketmodels/`.

These models are **not** part of the rocket-launch ensemble analysis workflow. They are conceptual simulations for exploring how rocket ascent, changing range velocity, atmospheric sound speed, and Doppler shift might affect observed acoustic frequencies.

## Main runner

```matlab
run_rocket_simulation_models
```

This runs both the 1-D and 2-D models, saves figures, and writes a MAT file containing the simulation structures.

## Package functions

```text
+rocketmodels/falcon9Defaults.m
+rocketmodels/simulateAscent1D.m
+rocketmodels/simulateAscent2D.m
+rocketmodels/dopplerFrequency.m
+rocketmodels/gravityAtAltitude.m
+rocketmodels/speedOfSoundProfile.m
+rocketmodels/plotAscentSummary1D.m
+rocketmodels/plotAscentSummary2D.m
```

## Model assumptions

These are deliberately simple toy models:

- constant thrust during first-stage burn,
- linear mass loss,
- simple altitude-dependent gravity,
- crude speed-of-sound lapse with altitude,
- simple drag terms,
- Doppler shift for a receding acoustic source.

The 2-D refactor fixes two problems in the legacy script:

1. horizontal acceleration is now divided by mass,
2. Doppler frequency is computed using the standard moving-source formula rather than subtracting a velocity/sound-speed ratio from frequency.

## Dependencies

Required:

- MATLAB

No GISMO, Antelope, Mapping Toolbox, or Signal Processing Toolbox dependencies are required.

## Example

```matlab
cfg = rocketmodels.falcon9Defaults();
cfg.ReferenceFrequencyHz = 80;
cfg.FinalPitchFromVerticalDeg = 35;

sim = rocketmodels.simulateAscent2D('Config', cfg);
rocketmodels.plotAscentSummary2D(sim);
```

## Caution

Do not treat these as flight-dynamics models. They are useful for intuition, plotting, and order-of-magnitude discussion only.
