function sim = simulateAscent2D(varargin)
%SIMULATEASCENT2D Simple 2-D rocket ascent and Doppler toy model.
%
% sim = rocketmodels.simulateAscent2D()
%
% This is a corrected, function-based version of rocketsimulation2d.m.
% The legacy script omitted division by mass in the horizontal acceleration
% term and used a non-Doppler frequency update. This version fixes those
% issues while preserving the conceptual purpose of the original model.

p = inputParser;
p.addParameter('Config', rocketmodels.falcon9Defaults(), @isstruct);
p.addParameter('ObserverX', 0, @isnumeric);
p.addParameter('ObserverY', 0, @isnumeric);
p.parse(varargin{:});
cfg = p.Results.Config;
observer_x = p.Results.ObserverX;
observer_y = p.Results.ObserverY;

dt = cfg.TimeStepSeconds;
t = 0:dt:cfg.BurnTimeSeconds;
n = numel(t);

x_m = zeros(n, 1);
y_m = zeros(n, 1);
vx_mps = zeros(n, 1);
vy_mps = zeros(n, 1);
ax_mps2 = zeros(n, 1);
ay_mps2 = zeros(n, 1);
speed_mps = zeros(n, 1);
acceleration_mps2 = zeros(n, 1);
mass_kg = nan(n, 1);
gravity_mps2 = nan(n, 1);
drag_n = zeros(n, 1);
pitch_from_vertical_deg = nan(n, 1);
sound_speed_mps = nan(n, 1);
radial_velocity_mps = zeros(n, 1);
doppler_frequency_hz = nan(n, 1);

mass_kg(1) = cfg.InitialMassKg;
gravity_mps2(1) = cfg.GravityMps2;
sound_speed_mps(1) = cfg.SeaLevelSoundSpeedMps;
doppler_frequency_hz(1) = cfg.ReferenceFrequencyHz;
pitch_from_vertical_deg(1) = cfg.InitialPitchFromVerticalDeg;

for k = 1:n-1
    frac = min(t(k+1) / cfg.PitchRampSeconds, 1);
    pitch_from_vertical_deg(k+1) = cfg.InitialPitchFromVerticalDeg ...
        + frac * (cfg.FinalPitchFromVerticalDeg - cfg.InitialPitchFromVerticalDeg);

    theta = deg2rad(pitch_from_vertical_deg(k+1));

    mass_next = max( ...
        cfg.InitialMassKg - cfg.MassLossRateKgPerS * t(k+1), ...
        cfg.FirstStageEmptyMassKg + cfg.SecondStageFullMassKg + cfg.PayloadMassKg);
    mass_mean = mean([mass_kg(k), mass_next]);

    gravity_now = rocketmodels.gravityAtAltitude(y_m(k), cfg);

    speed_now = hypot(vx_mps(k), vy_mps(k));
    drag_now = cfg.LinearDragCoefficient2D * speed_now * exp(-y_m(k) / cfg.AtmosphericScaleHeightM);

    thrust_minus_drag = max(cfg.ThrustN - drag_now, 0);

    ax_now = sin(theta) * thrust_minus_drag / mass_mean;
    ay_now = cos(theta) * thrust_minus_drag / mass_mean - gravity_now;

    ax_mps2(k+1) = ax_now;
    ay_mps2(k+1) = ay_now;

    vx_mps(k+1) = vx_mps(k) + mean([ax_mps2(k), ax_mps2(k+1)]) * dt;
    vy_mps(k+1) = vy_mps(k) + mean([ay_mps2(k), ay_mps2(k+1)]) * dt;

    x_m(k+1) = x_m(k) + mean([vx_mps(k), vx_mps(k+1)]) * dt;
    y_m(k+1) = max(0, y_m(k) + mean([vy_mps(k), vy_mps(k+1)]) * dt);

    speed_mps(k+1) = hypot(vx_mps(k+1), vy_mps(k+1));
    acceleration_mps2(k+1) = hypot(ax_mps2(k+1), ay_mps2(k+1));

    mass_kg(k+1) = mass_next;
    gravity_mps2(k+1) = rocketmodels.gravityAtAltitude(y_m(k+1), cfg);
    drag_n(k+1) = cfg.LinearDragCoefficient2D * speed_mps(k+1) * exp(-y_m(k+1) / cfg.AtmosphericScaleHeightM);
    sound_speed_mps(k+1) = rocketmodels.speedOfSoundProfile(y_m(k+1), cfg);

    range_vec = [x_m(k+1) - observer_x, y_m(k+1) - observer_y];
    velocity_vec = [vx_mps(k+1), vy_mps(k+1)];
    range_norm = norm(range_vec);

    if range_norm > 0
        radial_velocity_mps(k+1) = dot(velocity_vec, range_vec) / range_norm;
    else
        radial_velocity_mps(k+1) = 0;
    end

    doppler_frequency_hz(k+1) = rocketmodels.dopplerFrequency( ...
        cfg.ReferenceFrequencyHz, sound_speed_mps(k+1), radial_velocity_mps(k+1));
end

sim.config = cfg;
sim.time_s = t(:);
sim.x_m = x_m;
sim.y_m = y_m;
sim.vx_mps = vx_mps;
sim.vy_mps = vy_mps;
sim.ax_mps2 = ax_mps2;
sim.ay_mps2 = ay_mps2;
sim.speed_mps = speed_mps;
sim.acceleration_mps2 = acceleration_mps2;
sim.mass_kg = mass_kg;
sim.gravity_mps2 = gravity_mps2;
sim.drag_n = drag_n;
sim.pitch_from_vertical_deg = pitch_from_vertical_deg;
sim.sound_speed_mps = sound_speed_mps;
sim.radial_velocity_mps = radial_velocity_mps;
sim.doppler_frequency_hz = doppler_frequency_hz;
end
