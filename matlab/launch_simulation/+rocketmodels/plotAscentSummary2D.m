function plotAscentSummary2D(sim, varargin)
%PLOTASCENTSUMMARY2D Plot 2-D rocket ascent summary.

p = inputParser;
p.addParameter('OutputPrefix', '', @(x) ischar(x) || isstring(x));
p.parse(varargin{:});

t = sim.time_s;
prefix = string(p.Results.OutputPrefix);

figure('Color', 'w');
subplot(2,2,1);
plot(t, sim.acceleration_mps2);
xlabel('Time (s)'); ylabel('Acceleration (m/s^2)'); grid on;

subplot(2,2,2);
plot(t, sim.speed_mps / 1000);
xlabel('Time (s)'); ylabel('Speed (km/s)'); grid on;

subplot(2,2,3);
plot(t, hypot(sim.x_m, sim.y_m) / 1000);
xlabel('Time (s)'); ylabel('Distance from pad (km)'); grid on;

subplot(2,2,4);
plot(t, sim.doppler_frequency_hz);
xlabel('Time (s)'); ylabel('Observed frequency (Hz)'); grid on;

sgtitle(sprintf('%s: 2-D toy ascent model', sim.config.VehicleName));

if strlength(prefix) > 0
    saveas(gcf, char(prefix + "_summary.png"));
end

figure('Color', 'w');
subplot(3,2,1); plot(t, sim.ax_mps2); xlabel('Time (s)'); ylabel('Horizontal acceleration (m/s^2)'); grid on;
subplot(3,2,2); plot(t, sim.ay_mps2); xlabel('Time (s)'); ylabel('Vertical acceleration (m/s^2)'); grid on;
subplot(3,2,3); plot(t, sim.vx_mps); xlabel('Time (s)'); ylabel('Horizontal speed (m/s)'); grid on;
subplot(3,2,4); plot(t, sim.vy_mps); xlabel('Time (s)'); ylabel('Vertical speed (m/s)'); grid on;
subplot(3,2,5); plot(t, sim.x_m); xlabel('Time (s)'); ylabel('Horizontal distance (m)'); grid on;
subplot(3,2,6); plot(t, sim.y_m); xlabel('Time (s)'); ylabel('Altitude (m)'); grid on;

sgtitle('2-D model components');

if strlength(prefix) > 0
    saveas(gcf, char(prefix + "_components.png"));
end

figure('Color', 'w');
subplot(3,2,1); plot(t, sim.pitch_from_vertical_deg); xlabel('Time (s)'); ylabel('Pitch from vertical (deg)'); grid on;
subplot(3,2,2); plot(t, atan2d(sim.vy_mps, sim.vx_mps)); xlabel('Time (s)'); ylabel('Velocity angle from horizontal (deg)'); grid on;
subplot(3,2,3); plot(t, atan2d(sim.y_m, sim.x_m)); xlabel('Time (s)'); ylabel('Position angle from horizontal (deg)'); grid on;
subplot(3,2,4); plot(sim.x_m / 1000, sim.y_m / 1000); xlabel('Horizontal distance (km)'); ylabel('Altitude (km)'); axis equal; grid on;
subplot(3,2,5); plot(t, sim.sound_speed_mps); xlabel('Time (s)'); ylabel('Sound speed (m/s)'); grid on;
subplot(3,2,6); plot(t, sim.doppler_frequency_hz); xlabel('Time (s)'); ylabel('Observed frequency (Hz)'); grid on;

sgtitle('2-D model geometry and Doppler');

if strlength(prefix) > 0
    saveas(gcf, char(prefix + "_geometry_doppler.png"));
end
end
