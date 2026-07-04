function result = computeSlidingXcorr(w, varargin)
%COMPUTESLIDINGXCORR Generic sliding-window pairwise waveform cross-correlation.
%
% result = rocketseis.computeSlidingXcorr(w, 'WindowSeconds', 1.5, ...)
%
% Requires GISMO waveform objects and Signal Processing Toolbox xcorr.

p = inputParser;
p.addParameter('WindowSeconds', 1.5, @isnumeric);
p.addParameter('StepSeconds', 0.1, @isnumeric);
p.addParameter('MinimumCorrelation', 0.1, @isnumeric);
p.parse(varargin{:});
opt = p.Results;

SECS_PER_DAY = 86400;
window_days = opt.WindowSeconds / SECS_PER_DAY;
step_days = opt.StepSeconds / SECS_PER_DAY;

start_time = get(w(1), 'start');
end_time = get(w(1), 'end');

tv = start_time:step_days:(end_time - window_days);
nwin = numel(tv);
nchan = numel(w);

best_lag_seconds = zeros(nwin, nchan, nchan);
best_correlation = zeros(nwin, nchan, nchan);
amplitude_ratio = zeros(nwin, nchan, nchan);

for iwin = 1:nwin
    snum = tv(iwin);
    enum = snum + window_days;
    haystacks = detrend(extract(w, 'time', snum, enum));

    for needle_index = 1:nchan
        needle = haystacks(needle_index);
        needle_data = get(needle, 'data');
        fs = get(needle, 'freq');

        for haystack_index = 1:nchan
            this_haystack = haystacks(haystack_index);
            haystack_data = get(this_haystack, 'data');

            [acor, lag_samples] = xcorr(haystack_data, needle_data, 'coeff');

            denom = mean(abs(haystack_data));
            if denom == 0
                amplitude_ratio(iwin, needle_index, haystack_index) = NaN;
            else
                amplitude_ratio(iwin, needle_index, haystack_index) = ...
                    mean(abs(needle_data)) ./ denom;
            end

            [maxcor, best_index] = max(acor);
            best_lag = (best_index + lag_samples(1) - 1) / fs;

            if maxcor >= opt.MinimumCorrelation
                best_lag_seconds(iwin, needle_index, haystack_index) = best_lag;
                best_correlation(iwin, needle_index, haystack_index) = maxcor;
            else
                best_lag_seconds(iwin, needle_index, haystack_index) = NaN;
                best_correlation(iwin, needle_index, haystack_index) = maxcor;
            end
        end
    end
end

try
    station_names = get(w, 'station');
catch
    station_names = arrayfun(@(k) sprintf('S%d', k), 1:nchan, 'UniformOutput', false);
end

result.times = tv(:);
result.best_lag_seconds = best_lag_seconds;
result.best_correlation = best_correlation;
result.amplitude_ratio = amplitude_ratio;
result.station_names = station_names;
result.window_seconds = opt.WindowSeconds;
result.step_seconds = opt.StepSeconds;
result.minimum_correlation = opt.MinimumCorrelation;
end
