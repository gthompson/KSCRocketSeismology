function plotTrajectoryProxy(metrics, cfg, output_file, title_string)
%PLOTTRAJECTORYPROXY Plot crude velocity/distance proxy from frequency shifts.
%
% This preserves the exploratory logic from ensemble_analysis.m:
% velocity is inferred from a frequency ratio relative to the maximum peak
% frequency. Treat this only as a qualitative Doppler proxy.

if ~isfield(metrics, 'infrasound') || ~isfield(metrics.infrasound, 'peakFrequency')
    return
end

pf = metrics.infrasound.peakFrequency;
T = metrics.infrasound.T;

if iscell(pf)
    pf = pf{1};
end
if iscell(T)
    T = T{1};
end

pf = double(pf(:));
T = double(T(:));

if isempty(pf) || all(~isfinite(pf))
    return
end

[maxf, maxf_index] = max(pf);
velocity = cfg.SoundSpeedMps .* (maxf ./ pf - 1);
velocity(1:maxf_index) = 0;
valid = find(isfinite(velocity) & velocity > 0);

if isempty(valid)
    return
end

velocity = velocity(1:max(valid));
T = T(1:max(valid));

bad = ~isfinite(velocity);
if any(bad) && any(~bad)
    velocity(bad) = interp1(find(~bad), velocity(~bad), find(bad), 'linear', 'extrap');
end

dt = median(diff(T)) * 86400;
if ~isfinite(dt) || dt <= 0
    dt = 1;
end

figure('Color', 'w');

subplot(2,1,1);
plot(T, velocity / 1000, 'LineWidth', 2);
datetick('x', 'HH:MM:SS', 'keeplimits');
ylabel('Speed proxy (km/s)');
grid on;

subplot(2,1,2);
plot(T, cumsum(velocity / 1000) * dt, 'LineWidth', 2);
datetick('x', 'HH:MM:SS', 'keeplimits');
ylabel('Distance proxy (km)');
xlabel('Time');
grid on;

sgtitle(sprintf('Rocket trajectory proxy\n%s', title_string), 'Interpreter', 'none');

saveas(gcf, output_file);
close(gcf);
end
