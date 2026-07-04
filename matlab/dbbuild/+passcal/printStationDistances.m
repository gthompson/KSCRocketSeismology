function printStationDistances(station, varargin)
%PRINTSTATIONDISTANCES Print stations sorted by distance from source.

p = inputParser;
p.addParameter('SoundSpeedKmPerS', 0.340, @isnumeric);
p.parse(varargin{:});

[~, idx] = sort([station.distanceKm]);

for k = 1:numel(idx)
    i = idx(k);
    sound_time_s = station(i).distanceKm ./ p.Results.SoundSpeedKmPerS;
    fprintf('%s.%s, distance=%.3f km, azimuth=%.2f degrees, sound=%.2f s\n', ...
        station(i).name, station(i).location, station(i).distanceKm, ...
        station(i).azimuthDeg, sound_time_s);
end
end
