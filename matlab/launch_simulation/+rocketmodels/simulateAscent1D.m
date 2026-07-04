function sim = simulateAscent1D(varargin)
%SIMULATEASCENT1D Simple 1-D vertical rocket ascent and Doppler toy model.
%
% sim = rocketmodels.simulateAscent1D()
% sim = rocketmodels.simulateAscent1D('Config', cfg)
%
% This is a cleaned, function-based version of rocketsimulation1d.m.
% It models vertical ascent with decreasing mass, altitude-dependent gravity,
% linear drag, a crude speed-of-sound profile, and Doppler shift for a
% receding source.

p = inputParser;
p.addParameter('Config', rocketmodels.falcon9Defaults(), @isstruct);
p.parse(varargin{:});
cfg = p.Results.Config;

dt = cfg.TimeStepSeconds;
t = 0:dt:cfg.BurnTimeSeconds;
n = numel(t);

mass_kg = nan(n, 1);
gravity_mps2 = nan(n, 1);
drag_n = nan(n, 1);
acceleration_mps2 = nan(n, 1);
velocity_mps = nan(n, 1);
altitude_m = nan(n, 1);
sound_speed_mps = nan(n, 1);
doppler_frequency_hz = nan(n, 1);

mass_kg(1) = cfg.InitialMassKg;
gravity_mps2(1) = cfg.GravityMps2;
acceleration_mps2(1) = 0;
velocity_mps(1) = 0;
altitude_m(1) = 0;
sound_speed_mps(1) = cfg.SeaLevelSoundSpeedMps;
doppler_frequency_hz(1) = cfg.ReferenceFrequencyHz;
drag_n(1) = 0;

for k = 1:n-1
    gravity_now = rocketmodels.gravityAtAltitude(altitude_m(k), cfg);
    mass_next = max( ...
        cfg.InitialMassKg - cfg.MassLossRateKgPerS * t(k+1), ...
        cfg.FirstStageEmptyMassKg + cfg.SecondStageFullMassKg + cfg.PayloadMassKg);

    drag_now = cfg.LinearDragCoefficient1D * velocity_mps(k);
    mass_mean = mean([mass_kg(k), mass_next]);

    acceleration_now = (cfg.ThrustN - drag_now) / mass_mean - gravity_now;

    acceleration_mps2(k+1) = acceleration_now;
    velocity_mps(k+1) = max(0, velocity_mps(k) + acceleration_now * dt);
    altitude_m(k+1) = max(0, altitude_m(k) + mean([velocity_mps(k), velocity_mps(k+1)]) * dt);
    mass_kg(k+1) = mass_next;
    gravity_mps2(k+1) = rocketmodels.gravityAtAltitude(altitude_m(k+1), cfg);
    drag_n(k+1) = cfg.LinearDragCoefficient1D * velocity_mps(k+1);
    sound_speed_mps(k+1) = rocketmodels.speedOfSoundProfile(altitude_m(k+1), cfg);

    % In 1-D, all velocity is radial away from a ground observer.
    doppler_frequency_hz(k+1) = rocketmodels.dopplerFrequency( ...
        cfg.ReferenceFrequencyHz, sound_speed_mps(k+1), velocity_mps(k+1));
end

sim.config = cfg;
sim.time_s = t(:);
sim.mass_kg = mass_kg;
sim.gravity_mps2 = gravity_mps2;
sim.drag_n = drag_n;
sim.acceleration_mps2 = acceleration_mps2;
sim.velocity_mps = velocity_mps;
sim.altitude_m = altitude_m;
sim.sound_speed_mps = sound_speed_mps;
sim.radial_velocity_mps = velocity_mps;
sim.doppler_frequency_hz = doppler_frequency_hz;
end
