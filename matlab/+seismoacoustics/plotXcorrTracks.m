function plotXcorrTracks(times, delays, varargin)
%PLOTXCORRTRACKS Generic cross-correlation timing-track plot.

p = inputParser;
p.addParameter('Correlations', [], @isnumeric);
p.addParameter('StationLabels', {}, @(x) iscell(x) || isstring(x));
p.addParameter('OutputFile', '', @(x) ischar(x) || isstring(x));
p.addParameter('Title', 'Cross-correlation timing tracks', @(x) ischar(x) || isstring(x));
p.addParameter('YLabel', 'Peak xcorr time (s)', @(x) ischar(x) || isstring(x));
p.addParameter('FlipSign', false, @islogical);
p.parse(varargin{:});
opt = p.Results;

if opt.FlipSign
    delays = -delays;
end

figure('Color', 'w');
hold on;

nchan = size(delays, 2);
corrv = opt.Correlations;
if isempty(corrv)
    corrv = ones(size(delays));
end

for k = 1:nchan
    marker_size = 20 + 40 .* corrv(:, k);
    scatter(times(:), delays(:, k), marker_size, 'x');
end

datetick('x', 'HH:MM:SS', 'keeplimits');
xlabel(sprintf('Time (UTC) on %s', datestr(times(end), 'dd-mmm-yyyy HH:MM:SS')));
ylabel(opt.YLabel);
title(opt.Title);

if ~isempty(opt.StationLabels)
    legend(cellstr(opt.StationLabels), 'Location', 'best');
end

grid on;
hold off;

if strlength(string(opt.OutputFile)) > 0
    saveas(gcf, char(opt.OutputFile));
end
end
