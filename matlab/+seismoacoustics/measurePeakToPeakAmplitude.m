function [eventOut, measurements] = measurePeakToPeakAmplitude(w, eventIn, relativeTravelTimes, varargin)
%MEASUREPEAKTOPEAKAMPLITUDE Measure peak-to-peak amplitudes in event windows.
%
%   [eventOut, measurements] = falcon9.measurePeakToPeakAmplitude(w, eventIn,
%   relativeTravelTimes) searches each waveform channel for the largest
%   peak-to-peak pressure excursion within a short moving sub-window around
%   the predicted arrival time. The function is a cleaned replacement for
%   the legacy auto_measure_minmax3.m / auto_measure_minmax.m code.
%
%   Inputs
%   ------
%   w : GISMO waveform array, or numeric matrix [samples x channels]
%       Waveform data. GISMO waveforms are preferred for the Falcon 9
%       workflow because start time and sampling rate are carried in the
%       object metadata.
%
%   eventIn : struct
%       Event structure. By default it must contain FirstArrivalTime as a
%       MATLAB datenum. This is the reference arrival time used to define
%       channel-specific search windows.
%
%   relativeTravelTimes : numeric vector [seconds]
%       Per-channel time correction relative to eventIn.FirstArrivalTime.
%
%   Name-value options
%   ------------------
%   'MaxPeakSeparation' : seconds, default 0.03
%       Maximum allowed time between min and max samples when computing
%       peak-to-peak amplitude.
%
%   'PreArrival' : seconds, default 0.05
%       Time before predicted arrival at which to begin search.
%
%   'PostArrival' : seconds, default 0.15
%       Time after the start of the search window to end search. This keeps
%       the legacy behavior: end = first arrival + relative delay - PreArrival
%       + PostArrival.
%
%   'SamplingFrequency' : Hz, default []
%       Required only when w is numeric.
%
%   'StartTime' : MATLAB datenum or seconds, default 0
%       Required for absolute timing when w is numeric. If eventIn uses
%       datenum FirstArrivalTime, StartTime should also be a datenum.
%
%   'Detrend' : logical, default true
%       Remove linear trend/offset before measuring.
%
%   'MakePlot' : logical, default false
%       Plot each channel and mark measured min/max samples. Plotting does
%       not require GISMO.
%
%   Outputs
%   -------
%   eventOut : struct
%       Copy of eventIn with fields maxAmp, minAmp, maxTime, minTime, p2p,
%       rms, and energy populated for each channel.
%
%   measurements : table
%       One row per channel with search-window and amplitude metrics.
%
%   Notes
%   -----
%   Energy here is the signal integral sum(y.^2)/fs within the search
%   window, not range-corrected acoustic energy. Use
%   falcon9.computeInfrasoundEnergy for range-corrected acoustic energy.
%
%   Glenn Thompson / Falcon 9 analysis cleanup.

p = inputParser;
p.FunctionName = 'falcon9.measurePeakToPeakAmplitude';
addParameter(p, 'MaxPeakSeparation', 0.03, @(x) validateattributes(x, {'numeric'}, {'scalar','positive'}));
addParameter(p, 'PreArrival', 0.05, @(x) validateattributes(x, {'numeric'}, {'scalar','nonnegative'}));
addParameter(p, 'PostArrival', 0.15, @(x) validateattributes(x, {'numeric'}, {'scalar','positive'}));
addParameter(p, 'SamplingFrequency', [], @(x) isempty(x) || (isscalar(x) && isnumeric(x) && x > 0));
addParameter(p, 'StartTime', 0, @(x) isnumeric(x) && (isscalar(x) || isvector(x)));
addParameter(p, 'Detrend', true, @(x) islogical(x) || isnumeric(x));
addParameter(p, 'MakePlot', false, @(x) islogical(x) || isnumeric(x));
parse(p, varargin{:});
opt = p.Results;

SECONDS_PER_DAY = 86400;

data = localGetDataMatrix(w);
[numSamples, numChannels] = size(data);

if opt.Detrend
    data = detrend(data);
end

fs = localGetSamplingRates(w, opt.SamplingFrequency, numChannels);
startTime = localGetStartTimes(w, opt.StartTime, numChannels);

if nargin < 3 || isempty(relativeTravelTimes)
    relativeTravelTimes = zeros(1, numChannels);
end
relativeTravelTimes = relativeTravelTimes(:).';
if numel(relativeTravelTimes) ~= numChannels
    error('relativeTravelTimes must have one value per channel (%d).', numChannels);
end

if ~isfield(eventIn, 'FirstArrivalTime')
    error('eventIn must contain FirstArrivalTime as the event reference time.');
end

eventOut = eventIn;
fields = {'maxAmp','minAmp','maxTime','minTime','p2p','rms','energy'};
for i = 1:numel(fields)
    eventOut.(fields{i}) = NaN(1, numChannels);
end

channel = (1:numChannels).';
searchStartTime = NaN(numChannels,1);
searchEndTime = NaN(numChannels,1);
maxTime = NaN(numChannels,1);
minTime = NaN(numChannels,1);
maxAmp = NaN(numChannels,1);
minAmp = NaN(numChannels,1);
p2p = NaN(numChannels,1);
rmsNoise = NaN(numChannels,1);
signalEnergy = NaN(numChannels,1);
startSample = NaN(numChannels,1);
endSample = NaN(numChannels,1);

if opt.MakePlot
    figure('Name', 'Peak-to-peak amplitude measurements');
end

for chan = 1:numChannels
    y = data(:, chan);
    thisFs = fs(chan);
    thisStart = startTime(chan);

    searchStart = eventIn.FirstArrivalTime + relativeTravelTimes(chan)/SECONDS_PER_DAY - opt.PreArrival/SECONDS_PER_DAY;
    searchEnd = searchStart + opt.PostArrival/SECONDS_PER_DAY;

    firstSample = max(1, round((searchStart - thisStart) * SECONDS_PER_DAY * thisFs));
    lastSample = min(numSamples, round((searchEnd - thisStart) * SECONDS_PER_DAY * thisFs));
    subWindowSamples = max(2, round(thisFs * opt.MaxPeakSeparation));

    searchStartTime(chan) = searchStart;
    searchEndTime(chan) = searchEnd;
    startSample(chan) = firstSample;
    endSample(chan) = lastSample;

    if lastSample <= firstSample || (lastSample - firstSample + 1) < subWindowSamples
        warning('Channel %d search window is too short or outside waveform range.', chan);
        continue
    end

    [bestP2P, bestMaxAmp, bestMinAmp, bestMaxSample, bestMinSample] = localMaxP2P(y, firstSample, lastSample, subWindowSamples);

    bestMaxTime = thisStart + ((bestMaxSample - 1) / thisFs) / SECONDS_PER_DAY;
    bestMinTime = thisStart + ((bestMinSample - 1) / thisFs) / SECONDS_PER_DAY;

    eventOut.maxAmp(chan) = bestMaxAmp;
    eventOut.minAmp(chan) = bestMinAmp;
    eventOut.maxTime(chan) = bestMaxTime;
    eventOut.minTime(chan) = bestMinTime;
    eventOut.p2p(chan) = bestP2P;
    eventOut.rms(chan) = std(y, 'omitnan');
    eventOut.energy(chan) = sum(y(firstSample:lastSample).^2, 'omitnan') / thisFs;

    maxTime(chan) = bestMaxTime;
    minTime(chan) = bestMinTime;
    maxAmp(chan) = bestMaxAmp;
    minAmp(chan) = bestMinAmp;
    p2p(chan) = bestP2P;
    rmsNoise(chan) = eventOut.rms(chan);
    signalEnergy(chan) = eventOut.energy(chan);

    if opt.MakePlot
        t = ((0:numSamples-1) ./ thisFs).';
        subplot(numChannels, 1, chan);
        plot(t, y, 'k-'); hold on
        xline((firstSample-1)/thisFs, '--');
        xline((lastSample-1)/thisFs, '--');
        plot((bestMaxSample-1)/thisFs, bestMaxAmp, 'g*');
        plot((bestMinSample-1)/thisFs, bestMinAmp, 'r*');
        ylabel(sprintf('Ch %d', chan));
        if chan == 1
            title('Peak-to-peak amplitude search');
        end
        if chan == numChannels
            xlabel('Time since waveform start (s)');
        end
    end
end

measurements = table(channel, startSample, endSample, searchStartTime, searchEndTime, ...
    maxAmp, minAmp, maxTime, minTime, p2p, rmsNoise, signalEnergy);
end

function data = localGetDataMatrix(w)
if isnumeric(w)
    data = w;
    if isvector(data)
        data = data(:);
    end
    return
end

try
    n = numel(w);
    dataCell = cell(1, n);
    maxLen = 0;
    for k = 1:n
        dataCell{k} = get(w(k), 'data'); %#ok<GTARG>
        dataCell{k} = dataCell{k}(:);
        maxLen = max(maxLen, numel(dataCell{k}));
    end
    data = NaN(maxLen, n);
    for k = 1:n
        data(1:numel(dataCell{k}), k) = dataCell{k};
    end
catch ME
    error('Could not extract data from input waveform array: %s', ME.message);
end
end

function fs = localGetSamplingRates(w, samplingFrequency, numChannels)
if isnumeric(w)
    if isempty(samplingFrequency)
        error('SamplingFrequency is required when w is numeric.');
    end
    fs = repmat(samplingFrequency, 1, numChannels);
    return
end

fs = NaN(1, numChannels);
for k = 1:numChannels
    fs(k) = get(w(k), 'freq'); %#ok<GTARG>
end
end

function startTime = localGetStartTimes(w, startTimeOption, numChannels)
if isnumeric(w)
    if isscalar(startTimeOption)
        startTime = repmat(startTimeOption, 1, numChannels);
    elseif numel(startTimeOption) == numChannels
        startTime = startTimeOption(:).';
    else
        error('StartTime must be scalar or one value per channel.');
    end
    return
end

startTime = NaN(1, numChannels);
for k = 1:numChannels
    startTime(k) = get(w(k), 'start'); %#ok<GTARG>
end
end

function [bestP2P, bestMaxAmp, bestMinAmp, bestMaxSample, bestMinSample] = localMaxP2P(y, firstSample, lastSample, subWindowSamples)
bestP2P = -Inf;
bestMaxAmp = NaN;
bestMinAmp = NaN;
bestMaxSample = NaN;
bestMinSample = NaN;

for startSample = firstSample:(lastSample - subWindowSamples + 1)
    samples = startSample:(startSample + subWindowSamples - 1);
    [thisMaxAmp, localMaxIndex] = max(y(samples));
    [thisMinAmp, localMinIndex] = min(y(samples));
    thisP2P = thisMaxAmp - thisMinAmp;
    if thisP2P > bestP2P
        bestP2P = thisP2P;
        bestMaxAmp = thisMaxAmp;
        bestMinAmp = thisMinAmp;
        bestMaxSample = samples(localMaxIndex);
        bestMinSample = samples(localMinIndex);
    end
end
end
