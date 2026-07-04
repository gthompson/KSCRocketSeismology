function [travelTimes, w] = predictTravelTimes(stations, source, speedOfSound, varargin)
%PREDICTTRAVELTIMES Predict acoustic travel times from source to stations.
%
% [T, w] = falcon9.predictTravelTimes(stations, source, speedOfSound)
% [T, w] = falcon9.predictTravelTimes(..., 'Waveforms', w, 'OutputFile', file)
%
% Supports either geographic station/source coordinates or local Cartesian
% offsets. Geographic mode requires MATLAB Mapping Toolbox functions
% distance/deg2km. Cartesian mode has no Mapping Toolbox dependency.
%
% Station/source inputs:
%   Geographic: stations.lat, stations.lon, source.lat, source.lon
%   Cartesian:  stations.easting, stations.northing, source.easting, source.northing
%              or station offsets from source using stations.easting/northing
%              with source.easting/source.northing omitted or set to zero.
%
% Optional name-value pairs:
%   'CoordinateMode'  'auto'|'geographic'|'cartesian' (default 'auto')
%   'WindSpeed'       wind speed in m/s (default 0)
%   'WindDirection'   wind direction in degrees, same convention as original
%                     workflow (default 0)
%   'Waveforms'       GISMO waveform array to annotate using addfield
%   'ChannelNames'    cellstr/string channel names for reporting
%   'OutputFile'      optional text report path
%
% Output T is a table with channel, distance_m, backazimuth_deg,
% effective_speed_mps, travel_time_s.

p = inputParser;
p.FunctionName = 'falcon9.predictTravelTimes';
addRequired(p, 'stations', @isstruct);
addRequired(p, 'source', @isstruct);
addRequired(p, 'speedOfSound', @(x) isnumeric(x) && isscalar(x) && x > 0);
addParameter(p, 'CoordinateMode', 'auto', @(s) ischar(s) || isstring(s));
addParameter(p, 'WindSpeed', 0, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'WindDirection', 0, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'Waveforms', [], @(x) true);
addParameter(p, 'ChannelNames', {}, @(x) iscellstr(x) || isstring(x) || isempty(x)); %#ok<ISCLSTR>
addParameter(p, 'OutputFile', '', @(s) ischar(s) || isstring(s));
parse(p, stations, source, speedOfSound, varargin{:});

mode = lower(string(p.Results.CoordinateMode));
windSpeed = p.Results.WindSpeed;
windDirection = p.Results.WindDirection;
w = p.Results.Waveforms;
channelNames = cellstr(p.Results.ChannelNames);
outputFile = char(p.Results.OutputFile);

if mode == "auto"
    if hasFields(stations, {'lat', 'lon'}) && hasFields(source, {'lat', 'lon'})
        mode = "geographic";
    elseif hasFields(stations, {'easting', 'northing'})
        mode = "cartesian";
    else
        error('falcon9:predictTravelTimes:UnknownCoordinates', ...
            'Cannot infer coordinate mode from station/source fields.');
    end
end

switch mode
    case "geographic"
        requireFields(stations, {'lat', 'lon'}, 'stations');
        requireFields(source, {'lat', 'lon'}, 'source');
        lat = stations.lat(:);
        lon = stations.lon(:);
        n = numel(lat);
        distance_m = nan(n, 1);
        backazimuth_deg = nan(n, 1);
        for i = 1:n
            [arcDegrees, baz] = distance(lat(i), lon(i), source.lat, source.lon, 'degrees');
            distance_m(i) = deg2km(arcDegrees) * 1000;
            backazimuth_deg(i) = mod(baz, 360);
        end
    case "cartesian"
        requireFields(stations, {'easting', 'northing'}, 'stations');
        easting = stations.easting(:);
        northing = stations.northing(:);
        if isfield(source, 'easting'); sourceE = source.easting; else; sourceE = 0; end
        if isfield(source, 'northing'); sourceN = source.northing; else; sourceN = 0; end
        dE = easting - sourceE;
        dN = northing - sourceN;
        distance_m = hypot(dE, dN);
        % Back-azimuth from station toward source, clockwise from north.
        backazimuth_deg = mod(atan2d(sourceE - easting, sourceN - northing), 360);
    otherwise
        error('falcon9:predictTravelTimes:BadCoordinateMode', ...
            'CoordinateMode must be auto, geographic, or cartesian.');
end

n = numel(distance_m);
if isempty(channelNames)
    if isfield(stations, 'channel')
        channelNames = cellstr(string(stations.channel(:)));
    elseif ~isempty(w)
        channelNames = cell(n, 1);
        for i = 1:n
            try
                channelNames{i} = get(w(i), 'channel');
            catch
                channelNames{i} = sprintf('CH%02d', i);
            end
        end
    else
        channelNames = arrayfun(@(i) sprintf('CH%02d', i), 1:n, 'UniformOutput', false).';
    end
end
channelNames = channelNames(:);

effective_speed_mps = speedOfSound + windSpeed .* cosd((180 + backazimuth_deg) - windDirection);
travel_time_s = distance_m ./ effective_speed_mps;

travelTimes = table(channelNames, distance_m, backazimuth_deg, effective_speed_mps, travel_time_s, ...
    'VariableNames', {'channel', 'distance_m', 'backazimuth_deg', 'effective_speed_mps', 'travel_time_s'});

if ~isempty(w)
    for i = 1:min(numel(w), n)
        try
            w(i) = addfield(w(i), 'distance', distance_m(i));
            w(i) = addfield(w(i), 'backaz', backazimuth_deg(i));
            w(i) = addfield(w(i), 'predicted_traveltime_seconds', travel_time_s(i));
            if isfield(stations, 'lat'); w(i) = addfield(w(i), 'lat', stations.lat(i)); end
            if isfield(stations, 'lon'); w(i) = addfield(w(i), 'lon', stations.lon(i)); end
        catch ME
            warning('falcon9:predictTravelTimes:WaveformAnnotationFailed', ...
                'Could not annotate waveform %d: %s', i, ME.message);
        end
    end
end

if ~isempty(outputFile)
    writeTravelTimeReport(outputFile, travelTimes, speedOfSound, windSpeed, windDirection);
end
end

function tf = hasFields(s, fields)
tf = all(isfield(s, fields));
end

function requireFields(s, fields, name)
for j = 1:numel(fields)
    if ~isfield(s, fields{j})
        error('falcon9:predictTravelTimes:MissingField', ...
            '%s is missing required field "%s".', name, fields{j});
    end
end
end

function writeTravelTimeReport(filepath, T, speedOfSound, windSpeed, windDirection)
[fid, msg] = fopen(filepath, 'w');
if fid < 0
    error('falcon9:predictTravelTimes:FileOpenFailed', ...
        'Could not open %s: %s', filepath, msg);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '\n_______________________________________________\n');
fprintf(fid, 'PREDICTED TRAVEL TIME BASED ON:\n');
fprintf(fid, '  sound speed(c) %.1f m/s\n', speedOfSound);
fprintf(fid, '  wind speed     %.1f m/s\n', windSpeed);
fprintf(fid, '  wind direction %.1f degrees\n', windDirection);
fprintf(fid, '------\t--------\t-----------\t----------\t-----------\n');
fprintf(fid, 'Channel\tDistance\tBackAzimuth\tTravelTime\tc_effective\n');
fprintf(fid, '------\t--------\t-----------\t----------\t-----------\n');
for i = 1:height(T)
    fprintf(fid, '%s\t%.1f m\t\t%.1f deg\t%.3f s\t\t%.1f m/s\n', ...
        T.channel{i}, T.distance_m(i), T.backazimuth_deg(i), ...
        T.travel_time_s(i), T.effective_speed_mps(i));
end
fprintf(fid, '_______________________________________________\n');
fprintf(fid, 'Program name: %s\n', mfilename('fullpath'));
end
