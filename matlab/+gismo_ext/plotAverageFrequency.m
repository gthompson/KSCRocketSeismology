function metrics = plotAverageFrequency(w, varargin)
%PLOTAVERAGEFREQUENCY Plot spectrogram-derived frequency tracks for GISMO waveforms.
%
% metrics = gismo_ext.plotAverageFrequency(w, ...)
%
% This is a cleaned GISMO-extension utility based on the legacy
% plot_average_frequency.m rocket-analysis function.
%
% Inputs
% ------
% w
%   GISMO waveform object or waveform vector.
%
% Name-value options
% ------------------
% 'WindowLengthSeconds'   Spectrogram window length in seconds. Default: 2.0
% 'OverlapFraction'       Spectrogram overlap fraction, 0 <= x < 1. Default: 0.5
% 'Nfft'                  FFT length. Default: next power of 2 for each channel.
% 'FrequencyLimits'       [fmin fmax] Hz. Default: [0 Inf]
% 'Method'                'powerWeightedMean', 'peak', or 'both'. Default: 'both'
% 'PowerFloorDb'          Relative dB floor for excluding weak bins. Default: -Inf
% 'SmoothSeconds'         Moving median smoothing window in seconds. Default: 0
% 'MakeFigure'            true/false. Default: true
% 'OutputFile'            Optional figure filename. Default: ''
% 'Title'                 Figure title. Default: 'Average frequency'
%
% Outputs
% -------
% metrics is a struct array, one element per waveform, with fields:
%   station, channel, startTime, timeDatenum, timeSeconds,
%   frequencyHz, power, meanFrequencyHz, peakFrequencyHz
%
% Notes
% -----
% This function uses MATLAB's spectrogram function on GISMO waveform data.
% It does not require any rocket-specific metadata.

p = inputParser;
p.addRequired('w');
p.addParameter('WindowLengthSeconds', 2.0, @(x) isnumeric(x) && isscalar(x) && x > 0);
p.addParameter('OverlapFraction', 0.5, @(x) isnumeric(x) && isscalar(x) && x >= 0 && x < 1);
p.addParameter('Nfft', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x) && x > 0));
p.addParameter('FrequencyLimits', [0 Inf], @(x) isnumeric(x) && numel(x) == 2);
p.addParameter('Method', 'both', @(x) any(strcmpi(x, {'powerWeightedMean','peak','both'})));
p.addParameter('PowerFloorDb', -Inf, @(x) isnumeric(x) && isscalar(x));
p.addParameter('SmoothSeconds', 0, @(x) isnumeric(x) && isscalar(x) && x >= 0);
p.addParameter('MakeFigure', true, @(x) islogical(x) || isnumeric(x));
p.addParameter('OutputFile', '', @(x) ischar(x) || isstring(x));
p.addParameter('Title', 'Average frequency', @(x) ischar(x) || isstring(x));
p.parse(w, varargin{:});
opt = p.Results;

nwave = numel(w);
metrics = repmat(struct( ...
    'station', '', ...
    'channel', '', ...
    'startTime', NaN, ...
    'timeDatenum', [], ...
    'timeSeconds', [], ...
    'frequencyHz', [], ...
    'power', [], ...
    'meanFrequencyHz', [], ...
    'peakFrequencyHz', []), nwave, 1);

for iw = 1:nwave
    this_waveform = w(iw);

    data = double(get(this_waveform, 'data'));
    fs = double(get(this_waveform, 'freq'));
    start_time = get(this_waveform, 'start');

    if isempty(data) || all(~isfinite(data))
        warning('Waveform %d contains no usable data.', iw);
        continue
    end

    data = data(:);
    data = data - mean(data, 'omitnan');
    data(~isfinite(data)) = 0;

    window_samples = max(2, round(opt.WindowLengthSeconds * fs));
    overlap_samples = round(opt.OverlapFraction * window_samples);

    if isempty(opt.Nfft)
        nfft = 2 ^ nextpow2(window_samples);
    else
        nfft = round(opt.Nfft);
    end

    [s, f, t] = spectrogram(data, window_samples, overlap_samples, nfft, fs);
    power = abs(s).^2;

    freq_mask = f >= opt.FrequencyLimits(1) & f <= opt.FrequencyLimits(2);
    f_used = f(freq_mask);
    p_used = power(freq_mask, :);

    if isempty(f_used)
        error('FrequencyLimits exclude all spectrogram frequencies.');
    end

    if isfinite(opt.PowerFloorDb)
        max_power = max(p_used, [], 1);
        threshold = max_power .* 10.^(opt.PowerFloorDb ./ 10);
        p_used(p_used < threshold) = NaN;
    end

    denom = sum(p_used, 1, 'omitnan');
    mean_frequency = sum(p_used .* f_used, 1, 'omitnan') ./ denom;
    mean_frequency(denom <= 0) = NaN;

    [~, peak_idx] = max(p_used, [], 1, 'omitnan');
    peak_frequency = f_used(peak_idx);
    peak_frequency(all(~isfinite(p_used), 1)) = NaN;

    if opt.SmoothSeconds > 0 && numel(t) > 2
        dt = median(diff(t));
        n_smooth = max(1, round(opt.SmoothSeconds ./ dt));
        mean_frequency = movmedian(mean_frequency, n_smooth, 'omitnan');
        peak_frequency = movmedian(peak_frequency, n_smooth, 'omitnan');
    end

    metrics(iw).station = safeGet(this_waveform, 'station');
    metrics(iw).channel = safeGet(this_waveform, 'channel');
    metrics(iw).startTime = start_time;
    metrics(iw).timeSeconds = t(:);
    metrics(iw).timeDatenum = start_time + t(:) ./ 86400;
    metrics(iw).frequencyHz = f_used(:);
    metrics(iw).power = p_used;
    metrics(iw).meanFrequencyHz = mean_frequency(:);
    metrics(iw).peakFrequencyHz = peak_frequency(:);
end

if logical(opt.MakeFigure)
    makeFrequencyFigure(metrics, opt);
end
end


function value = safeGet(w, fieldname)
try
    value = get(w, fieldname);
    if iscell(value)
        value = value{1};
    end
catch
    value = '';
end
end


function makeFrequencyFigure(metrics, opt)
nwave = numel(metrics);
figure('Color', 'w');
hold on;

show_mean = any(strcmpi(opt.Method, {'powerWeightedMean', 'both'}));
show_peak = any(strcmpi(opt.Method, {'peak', 'both'}));

legend_entries = {};

for iw = 1:nwave
    if isempty(metrics(iw).timeDatenum)
        continue
    end

    label_base = strtrim(sprintf('%s %s', metrics(iw).station, metrics(iw).channel));
    if isempty(label_base)
        label_base = sprintf('waveform %d', iw);
    end

    if show_mean
        plot(metrics(iw).timeDatenum, metrics(iw).meanFrequencyHz, '-', 'LineWidth', 1.2);
        legend_entries{end+1} = sprintf('%s mean', label_base); %#ok<AGROW>
    end

    if show_peak
        plot(metrics(iw).timeDatenum, metrics(iw).peakFrequencyHz, '--', 'LineWidth', 1.0);
        legend_entries{end+1} = sprintf('%s peak', label_base); %#ok<AGROW>
    end
end

datetick('x', 'HH:MM:SS', 'keeplimits');
xlabel('Time (UTC)');
ylabel('Frequency (Hz)');
title(char(opt.Title));
grid on;

if ~isempty(legend_entries)
    legend(legend_entries, 'Interpreter', 'none', 'Location', 'best');
end

hold off;

if strlength(string(opt.OutputFile)) > 0
    saveas(gcf, char(opt.OutputFile));
end
end
