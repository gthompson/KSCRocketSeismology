function cfg = falcon9Defaults()
%FALCON9DEFAULTS Default parameters for simple Falcon 9 ascent toy models.
%
% These values are approximate and intended for conceptual Doppler/ascent
% experiments, not flight-dynamics prediction.

cfg.VehicleName = 'Falcon 9 approximate first-stage burn';

cfg.ThrustN = 7.607e6;
cfg.InitialMassKg = 549054;
cfg.FirstStageEmptyMassKg = 22200;
cfg.SecondStageFullMassKg = 115000;
cfg.PayloadMassKg = 1700;
cfg.BurnTimeSeconds = 162;

cfg.PropellantMassKg = cfg.InitialMassKg ...
    - cfg.FirstStageEmptyMassKg ...
    - cfg.SecondStageFullMassKg ...
    - cfg.PayloadMassKg;
cfg.MassLossRateKgPerS = cfg.PropellantMassKg / cfg.BurnTimeSeconds;

cfg.GravityMps2 = 9.8055;
cfg.EarthRadiusM = 6.371e6;

cfg.ReferenceFrequencyHz = 60;
cfg.SeaLevelSoundSpeedMps = 340;
cfg.MinimumSoundSpeedMps = 300;
cfg.SoundSpeedLapseMpsPerM = 2 / 500;

% Linear drag coefficients retained from the legacy scripts.
cfg.LinearDragCoefficient1D = 0.4 * cfg.MassLossRateKgPerS;
cfg.LinearDragCoefficient2D = 0.001 * cfg.MassLossRateKgPerS;
cfg.AtmosphericScaleHeightM = 8000;

% 2-D pitch model.
cfg.InitialPitchFromVerticalDeg = 0;
cfg.FinalPitchFromVerticalDeg = 27;
cfg.PitchRampSeconds = 80;

cfg.TimeStepSeconds = 1;
end
