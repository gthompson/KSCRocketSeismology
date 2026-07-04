function T = writeEventsTable(filepath, events, varargin)
%WRITEEVENTSTABLE Write Falcon 9 event metrics to CSV and return a table.
%
% T = falcon9.writeEventsTable(filepath, events)
% T = falcon9.writeEventsTable(filepath, events, 'ArrayDistanceKm', d)
%
% This is a safer replacement for writeEvents.m. Missing event fields are
% written as NaN/NaT rather than causing the whole export to fail.

p = inputParser;
p.FunctionName = 'falcon9.writeEventsTable';
addRequired(p, 'filepath', @(s) ischar(s) || isstring(s));
addRequired(p, 'events', @(x) isstruct(x) || isempty(x));
addParameter(p, 'ArrayDistanceKm', [], @(x) isempty(x) || isnumeric(x));
addParameter(p, 'SpeedOfSound', NaN, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'CorrelationThreshold', 0.7, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'TimeErrorThreshold', 0.001, @(x) isnumeric(x) && isscalar(x));
parse(p, filepath, events, varargin{:});

filepath = char(p.Results.filepath);
arrayDistanceKm = p.Results.ArrayDistanceKm;
corrThreshold = p.Results.CorrelationThreshold;
timeThreshold = p.Results.TimeErrorThreshold;

n = numel(events);
arrivalTime = NaT(n, 1);
pressurePa = nan(n, 1);
reducedPressurePaKm = nan(n, 1);
infrasoundEnergyJ = nan(n, 1);
pSnr = nan(n, 1);
verticalSeismicAmplitudeUmPerS = nan(n, 1);
seismicEnergyJ = nan(n, 1);
sSnr = nan(n, 1);
energyRatio = nan(n, 1);
meanCorrelation = nan(n, 1);
timeErrorS = nan(n, 1);
goodEvent = false(n, 1);
backAzimuthDeg = nan(n, 1);
soundSpeedMps = nan(n, 1);
predictedOriginTime = NaT(n, 1);
apparentSpeedMps = nan(n, 1);
apparentSpeedErrorMps = nan(n, 1);
apparentOriginTime = NaT(n, 1);

for i = 1:n
    ev = events(i);
    arrivalTime(i) = eventTime(ev, 'FirstArrivalTime');
    pressurePa(i) = medianField(ev, 'p2p', 1:3);
    reducedPressurePaKm(i) = medianField(ev, 'reducedPressure', []);
    infrasoundEnergyJ(i) = scalarField(ev, 'infrasoundEnergy');
    pSnr(i) = medianField(ev, 'snr', 1:3);
    verticalSeismicAmplitudeUmPerS(i) = scalarArrayField(ev, 'p2p', 6) / 1000;
    seismicEnergyJ(i) = scalarField(ev, 'seismicEnergy');
    sSnr(i) = scalarArrayField(ev, 'snr', 6);
    if isfinite(infrasoundEnergyJ(i)) && isfinite(seismicEnergyJ(i)) && seismicEnergyJ(i) ~= 0
        energyRatio(i) = infrasoundEnergyJ(i) / seismicEnergyJ(i);
    end
    meanCorrelation(i) = scalarField(ev, 'meanCorr');
    timeErrorS(i) = scalarField(ev, 'meanSecsDiff');
    goodEvent(i) = isfinite(timeErrorS(i)) && abs(timeErrorS(i)) < timeThreshold && ...
        isfinite(meanCorrelation(i)) && meanCorrelation(i) >= corrThreshold;
    if goodEvent(i)
        backAzimuthDeg(i) = scalarField(ev, 'bestbackaz');
        soundSpeedMps(i) = scalarField(ev, 'bestsoundspeed');
        apparentSpeedMps(i) = scalarField(ev, 'apparentSpeed');
        apparentSpeedErrorMps(i) = scalarField(ev, 'apparentSpeedError');
        if ~isempty(arrayDistanceKm) && ~isnat(arrivalTime(i))
            minDistanceM = min(arrayDistanceKm(:)) * 1000;
            if isfinite(soundSpeedMps(i)) && soundSpeedMps(i) > 0
                predictedOriginTime(i) = arrivalTime(i) - seconds(minDistanceM / soundSpeedMps(i));
            end
            if isfinite(apparentSpeedMps(i)) && apparentSpeedMps(i) > 0
                apparentOriginTime(i) = arrivalTime(i) - seconds(minDistanceM / apparentSpeedMps(i));
            end
        end
    end
end

T = table(arrivalTime, pressurePa, reducedPressurePaKm, infrasoundEnergyJ, pSnr, ...
    verticalSeismicAmplitudeUmPerS, seismicEnergyJ, sSnr, energyRatio, ...
    meanCorrelation, timeErrorS, goodEvent, backAzimuthDeg, soundSpeedMps, ...
    predictedOriginTime, apparentSpeedMps, apparentSpeedErrorMps, apparentOriginTime);

writetable(T, filepath);
end

function value = scalarField(s, fieldName)
if isfield(s, fieldName) && ~isempty(s.(fieldName)) && isnumeric(s.(fieldName))
    value = s.(fieldName)(1);
else
    value = NaN;
end
end

function value = scalarArrayField(s, fieldName, idx)
if isfield(s, fieldName) && isnumeric(s.(fieldName)) && numel(s.(fieldName)) >= idx
    value = s.(fieldName)(idx);
else
    value = NaN;
end
end

function value = medianField(s, fieldName, idx)
if ~isfield(s, fieldName) || isempty(s.(fieldName)) || ~isnumeric(s.(fieldName))
    value = NaN;
    return;
end
x = s.(fieldName);
if ~isempty(idx)
    idx = idx(idx <= numel(x));
    x = x(idx);
end
value = median(x, 'omitnan');
end

function t = eventTime(s, fieldName)
t = NaT;
if ~isfield(s, fieldName) || isempty(s.(fieldName))
    return;
end
x = s.(fieldName);
try
    if isa(x, 'datetime')
        t = x(1);
    elseif isnumeric(x)
        t = datetime(x(1), 'ConvertFrom', 'datenum');
    elseif ischar(x) || isstring(x)
        t = datetime(x(1));
    end
catch
    t = NaT;
end
end
