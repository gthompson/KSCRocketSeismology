%% 20_analyze_huddle_xcorr.m
% Sliding-window cross-correlation and amplitude-ratio analysis.

clearvars;

cfg = huddle.config2018290();

if ~exist(cfg.CacheFile, 'file')
    error('Cache file not found: %s. Run 10_import_huddle_data.m first.', cfg.CacheFile);
end

load(cfg.CacheFile, 'cfg', 'w_overview', 'w_analysis');

fprintf('Computing optional RSAM and STA/LTA diagnostics...\n');
rsam = [];
detobj = [];
sta = [];
lta = [];
sta_to_lta = [];

try
    rsam = waveform2rsam(w_overview, 'rms', cfg.RsamWindowSeconds);
catch ME
    warning('RSAM calculation skipped: %s', ME.message);
end

try
    [detobj, sta, lta, sta_to_lta] = gismo_ext.computeStaLtaDetections( ...
        w_overview, ...
        'StaSeconds', cfg.StaSeconds, ...
        'LtaSeconds', cfg.LtaSeconds, ...
        'TriggerOn', cfg.TriggerOn, ...
        'TriggerOff', cfg.TriggerOff, ...
        'MinimumEventDurationSeconds', cfg.MinimumEventDurationSeconds, ...
        'NetworkCode', cfg.NetworkCode);
catch ME
    warning('STA/LTA detection skipped: %s', ME.message);
end

fprintf('Computing sliding-window cross-correlations...\n');
xcorr_result = seismoacoustics.computeSlidingXcorr( ...
    w_analysis, ...
    'WindowSeconds', cfg.XcorrWindowSeconds, ...
    'StepSeconds', cfg.XcorrStepSeconds, ...
    'MinimumCorrelation', cfg.MinimumCorrelation);

fprintf('Collapsing adjacent-pair delays...\n');
delay_tracks = huddle.collapseAdjacentDelays(xcorr_result);

fprintf('Estimating amplitude ratios and calibration coefficients...\n');
amplitude_result = huddle.estimateAmplitudeRatios(xcorr_result, cfg);

save(cfg.CacheFile, ...
    'rsam', 'detobj', 'sta', 'lta', 'sta_to_lta', ...
    'xcorr_result', 'delay_tracks', 'amplitude_result', ...
    '-append');

fprintf('Updated cache: %s\n', cfg.CacheFile);
