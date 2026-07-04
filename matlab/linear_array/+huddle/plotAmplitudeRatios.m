function plotAmplitudeRatios(amp, output_file)
%PLOTAMPLITUDERATIOS Plot amplitude ratio and calibration diagnostics.

figure('Color', 'w');
imagesc(amp.mean_ratio);
axis image;
colorbar;
title('Mean amplitude ratio matrix');
xlabel('Haystack station index');
ylabel('Needle station index');

if isfield(amp, 'station_names') && ~isempty(amp.station_names)
    xticks(1:numel(amp.station_names));
    yticks(1:numel(amp.station_names));
    xticklabels(amp.station_names);
    yticklabels(amp.station_names);
end

if nargin >= 2 && ~isempty(output_file)
    saveas(gcf, output_file);
end

figure('Color', 'w');
bar(amp.final_calibration_coefficients);
grid on;
title(sprintf('Relative calibration coefficients, reference station %d', ...
    amp.reference_station_index));
xlabel('Station index');
ylabel('Relative coefficient');

if isfield(amp, 'station_names') && ~isempty(amp.station_names)
    xticks(1:numel(amp.station_names));
    xticklabels(amp.station_names);
end

if nargin >= 2 && ~isempty(output_file)
    [p, n, e] = fileparts(output_file);
    saveas(gcf, fullfile(p, [n '_coefficients' e]));
end
end
