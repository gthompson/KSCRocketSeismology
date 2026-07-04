function ax = plotArrayMap(stationEastM, stationNorthM, varargin)
%PLOTARRAYMAP Generic rocket/seismic array map.
%
% ax = rocketseis.plotArrayMap(stationEastM, stationNorthM, ...)
%
% Name-value options:
%   StationLabels      cellstr/string array of labels
%   SourceEastM        source east coordinate(s), default 0
%   SourceNorthM       source north coordinate(s), default 0
%   SourceLabels       source labels
%   OutputFile         optional file to save
%   Title              plot title
%   ShowArrowsToSource true/false, default true
%   EqualAxis          true/false, default true
%
% This is deliberately generic so it can be reused by Falcon 9, huddle
% deployments, and future rocket-event array geometries.

p = inputParser;
p.addParameter('StationLabels', {}, @(x) iscell(x) || isstring(x));
p.addParameter('SourceEastM', 0, @isnumeric);
p.addParameter('SourceNorthM', 0, @isnumeric);
p.addParameter('SourceLabels', {}, @(x) iscell(x) || isstring(x));
p.addParameter('OutputFile', '', @(x) ischar(x) || isstring(x));
p.addParameter('Title', 'Array geometry', @(x) ischar(x) || isstring(x));
p.addParameter('ShowArrowsToSource', true, @islogical);
p.addParameter('EqualAxis', true, @islogical);
p.parse(varargin{:});
opt = p.Results;

stationEastM = stationEastM(:);
stationNorthM = stationNorthM(:);
nsta = numel(stationEastM);

if isempty(opt.StationLabels)
    labels = arrayfun(@(k) sprintf('S%d', k), 1:nsta, 'UniformOutput', false);
else
    labels = cellstr(opt.StationLabels);
end

sourceEastM = opt.SourceEastM(:);
sourceNorthM = opt.SourceNorthM(:);
nsrc = numel(sourceEastM);

if isempty(opt.SourceLabels)
    sourceLabels = arrayfun(@(k) sprintf('Source %d', k), 1:nsrc, 'UniformOutput', false);
else
    sourceLabels = cellstr(opt.SourceLabels);
end

figure('Color', 'w');
ax = axes;
hold(ax, 'on');

plot(ax, stationEastM, stationNorthM, 'ko', ...
    'MarkerFaceColor', 'k', 'MarkerSize', 7);

for k = 1:nsta
    text(ax, stationEastM(k), stationNorthM(k), ['  ' labels{k}], ...
        'Interpreter', 'none', 'VerticalAlignment', 'middle');
end

plot(ax, sourceEastM, sourceNorthM, 'rp', ...
    'MarkerFaceColor', 'r', 'MarkerSize', 12);

for k = 1:nsrc
    text(ax, sourceEastM(k), sourceNorthM(k), ['  ' sourceLabels{k}], ...
        'Interpreter', 'none', 'VerticalAlignment', 'middle', 'FontWeight', 'bold');
end

if opt.ShowArrowsToSource && nsrc >= 1
    for k = 1:nsta
        quiver(ax, stationEastM(k), stationNorthM(k), ...
            sourceEastM(1)-stationEastM(k), sourceNorthM(1)-stationNorthM(k), ...
            0, 'Color', [0.3 0.3 0.3], 'MaxHeadSize', 0.15);
    end
end

grid(ax, 'on');
xlabel(ax, 'East offset (m)');
ylabel(ax, 'North offset (m)');
title(ax, opt.Title);

if opt.EqualAxis
    axis(ax, 'equal');
end

hold(ax, 'off');

if strlength(string(opt.OutputFile)) > 0
    saveas(gcf, char(opt.OutputFile));
end
end
