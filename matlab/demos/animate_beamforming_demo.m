function animate_beamforming_demo(varargin)
%ANIMATE_BEAMFORMING_DEMO Demonstrate 2-D plane-wave beamforming geometry.
%
% This script/function is intended for talks and teaching. It visualizes the
% search over back-azimuth and apparent speed for a small infrasound array.
%
% Usage examples:
%   animate_beamforming_demo
%   animate_beamforming_demo('Lat',lat,'Lon',lon,'Source',source)
%   animate_beamforming_demo('OutputDir','frames','SaveFrames',true)
%
% Inputs are optional name-value pairs:
%   Lat         station latitudes, degrees
%   Lon         station longitudes, degrees
%   Source      struct with fields .lat and .lon
%   BackAzRange back-azimuth search values, degrees
%   SpeedRange  apparent speeds, m/s
%   Radius      arrow-start radius around array centroid, m
%   SaveFrames  true/false, save PNG frames
%   OutputDir   directory for PNG frames
%
% Notes:
%   - This is a visualization only. It does not compute the best beam.
%   - For actual beamforming used in the paper workflow, use falcon9.beamform2d.
%   - Requires Mapping Toolbox functions DISTANCE/DEG2KM if Lat/Lon are used.
%
% Glenn Thompson / Falcon 9 explosion analysis cleanup.

p = inputParser;
p.addParameter('Lat', [], @(x) isnumeric(x) && isvector(x));
p.addParameter('Lon', [], @(x) isnumeric(x) && isvector(x));
p.addParameter('Source', struct('lat',[],'lon',[]), @(x) isstruct(x));
p.addParameter('BackAzRange', 190:3:220, @(x) isnumeric(x) && isvector(x));
p.addParameter('SpeedRange', 300:10:500, @(x) isnumeric(x) && isvector(x));
p.addParameter('Radius', 60, @(x) isnumeric(x) && isscalar(x) && x > 0);
p.addParameter('SaveFrames', false, @(x) islogical(x) || isnumeric(x));
p.addParameter('OutputDir', 'beamforming_frames', @(x) ischar(x) || isstring(x));
p.parse(varargin{:});
cfg = p.Results;

% Fall back to workspace variables for compatibility with the old AGU demo.
if isempty(cfg.Lat) && evalin('base','exist(''lat'',''var'')')
    cfg.Lat = evalin('base','lat');
end
if isempty(cfg.Lon) && evalin('base','exist(''lon'',''var'')')
    cfg.Lon = evalin('base','lon');
end
if (isempty(cfg.Source.lat) || isempty(cfg.Source.lon)) && evalin('base','exist(''source'',''var'')')
    cfg.Source = evalin('base','source');
end

if isempty(cfg.Lat) || isempty(cfg.Lon) || isempty(cfg.Source.lat) || isempty(cfg.Source.lon)
    error(['Provide Lat, Lon, and Source, or define lat, lon, and source ', ...
           'in the base workspace before running this demo.']);
end

[easting, northing] = local_latlon_to_offsets_m(cfg.Lat, cfg.Lon, cfg.Source);

if cfg.SaveFrames && ~exist(cfg.OutputDir, 'dir')
    mkdir(cfg.OutputDir);
end

fig = figure('Color','w');
ax = axes(fig, 'Position', [0.15 0.15 0.75 0.75]);
hold(ax, 'on');

stationColors = local_station_colors(numel(easting));
for k = 1:numel(easting)
    plot(ax, easting(k), northing(k), 'o', ...
        'MarkerFaceColor', stationColors{k}, ...
        'MarkerEdgeColor', 'k', ...
        'MarkerSize', 10);
    text(ax, easting(k) + 5, northing(k), sprintf('%d', k), ...
        'FontSize', 11, 'VerticalAlignment', 'middle');
end

grid(ax, 'on');
axis(ax, 'equal');
xlabel(ax, 'Metres east of source');
ylabel(ax, 'Metres north of source');
title(ax, 'Beamforming search: back-azimuth and apparent speed');

x0 = mean(easting, 'omitnan');
y0 = mean(northing, 'omitnan');

theta = deg2rad(0:0.5:359.5);
plot(ax, x0 + cfg.Radius*cos(theta), y0 + cfg.Radius*sin(theta), 'k:');

axisLimits = axis(ax);
frameNum = 1;

for backAz = cfg.BackAzRange
    theta = deg2rad(backAz);

    % Back-azimuth is the direction from array toward source.
    arrowStartX = x0 + cfg.Radius * sin(theta);
    arrowStartY = y0 + cfg.Radius * cos(theta);

    baseU = x0 - arrowStartX;
    baseV = y0 - arrowStartY;

    for speed = cfg.SpeedRange
        scale = speed / mean(cfg.SpeedRange);
        hq = quiver(ax, arrowStartX, arrowStartY, baseU*scale, baseV*scale, ...
            0, 'k', 'LineWidth', 2, 'MaxHeadSize', 0.8);

        ht1 = text(ax, axisLimits(1) + 0.05*range(axisLimits(1:2)), ...
            axisLimits(4) - 0.10*range(axisLimits(3:4)), ...
            sprintf('Back-azimuth: %5.1f^\\circ', backAz), 'FontSize', 16);
        ht2 = text(ax, axisLimits(1) + 0.05*range(axisLimits(1:2)), ...
            axisLimits(4) - 0.17*range(axisLimits(3:4)), ...
            sprintf('Apparent speed: %d m/s', speed), 'FontSize', 16);

        axis(ax, axisLimits);
        drawnow;

        if cfg.SaveFrames
            filename = fullfile(cfg.OutputDir, sprintf('beamforming_frame_%04d.png', frameNum));
            print(fig, filename, '-dpng', '-r150');
        end

        frameNum = frameNum + 1;
        delete([hq ht1 ht2]);
    end
end

% Leave final arrow visible.
backAz = cfg.BackAzRange(end);
speed = cfg.SpeedRange(end);
theta = deg2rad(backAz);
arrowStartX = x0 + cfg.Radius * sin(theta);
arrowStartY = y0 + cfg.Radius * cos(theta);
baseU = x0 - arrowStartX;
baseV = y0 - arrowStartY;
scale = speed / mean(cfg.SpeedRange);
quiver(ax, arrowStartX, arrowStartY, baseU*scale, baseV*scale, ...
    0, 'k', 'LineWidth', 2, 'MaxHeadSize', 0.8);
text(ax, axisLimits(1) + 0.05*range(axisLimits(1:2)), ...
    axisLimits(4) - 0.10*range(axisLimits(3:4)), ...
    sprintf('Back-azimuth: %5.1f^\\circ', backAz), 'FontSize', 16);
text(ax, axisLimits(1) + 0.05*range(axisLimits(1:2)), ...
    axisLimits(4) - 0.17*range(axisLimits(3:4)), ...
    sprintf('Apparent speed: %d m/s', speed), 'FontSize', 16);

end

function [easting, northing] = local_latlon_to_offsets_m(lat, lon, source)
deg2m = deg2km(1) * 1000;
easting = zeros(size(lat));
northing = zeros(size(lat));
for k = 1:numel(lat)
    easting(k) = distance(lat(k), lon(k), lat(k), source.lon) * deg2m;
    northing(k) = distance(lat(k), lon(k), source.lat, lon(k)) * deg2m;

    % Preserve east/west and north/south signs.
    if lon(k) < source.lon
        easting(k) = -easting(k);
    end
    if lat(k) < source.lat
        northing(k) = -northing(k);
    end
end
end

function colors = local_station_colors(n)
base = {'r','w','b','g','c','m','y'};
colors = cell(1,n);
for k = 1:n
    colors{k} = base{1 + mod(k-1, numel(base))};
end
end
