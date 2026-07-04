function plotAscentSummary1D(sim, varargin)
%PLOTASCENTSUMMARY1D Plot 1-D rocket ascent summary.

p = inputParser;
p.addParameter('OutputFile', '', @(x) ischar(x) || isstring(x));
p.parse(varargin{:});

t = sim.time_s;

figure('Color', 'w');
subplot(2,2,1);
plot(t, sim.acceleration_mps2);
xlabel('Time (s)'); ylabel('Acceleration (m/s^2)'); grid on;

subplot(2,2,2);
plot(t, sim.velocity_mps / 1000);
xlabel('Time (s)'); ylabel('Velocity (km/s)'); grid on;

subplot(2,2,3);
plot(t, sim.altitude_m / 1000);
xlabel('Time (s)'); ylabel('Altitude (km)'); grid on;

subplot(2,2,4);
plot(t, sim.doppler_frequency_hz);
xlabel('Time (s)'); ylabel('Observed frequency (Hz)'); grid on;
ylim([0, sim.config.ReferenceFrequencyHz]);

sgtitle(sprintf('%s: 1-D toy ascent model', sim.config.VehicleName));

if strlength(string(p.Results.OutputFile)) > 0
    saveas(gcf, char(p.Results.OutputFile));
end
end
