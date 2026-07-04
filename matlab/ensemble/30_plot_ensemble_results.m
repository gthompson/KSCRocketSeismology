%% 30_plot_ensemble_results.m
% Produce diagnostic plots, spectrograms, sound files, and summary plots.

clearvars;

cfg = rocketensemble.config();

if ~exist(cfg.CacheFile, 'file')
    error('Cache not found: %s. Run 10_preprocess_rocketmaster.m first.', cfg.CacheFile);
end
if ~exist(cfg.MetricsFile, 'file')
    error('Metrics file not found: %s. Run 20_analyze_ensemble.m first.', cfg.MetricsFile);
end

if ~exist(cfg.FigureDir, 'dir')
    mkdir(cfg.FigureDir);
end
if ~exist(cfg.AudioDir, 'dir')
    mkdir(cfg.AudioDir);
end

load(cfg.CacheFile, 'catalogobj');
load(cfg.MetricsFile, 'cfg', 'event_metrics', 'winfra', 'wseismic');

fprintf('Making per-event diagnostics.\n');
rocketensemble.makeEventDiagnostics(catalogobj, cfg);

fprintf('Plotting ensemble summary.\n');
rocketensemble.plotEnsembleSummary(event_metrics, ...
    'OutputFile', fullfile(cfg.FigureDir, 'ensemble_summary.png'));

fprintf('Plotting representative waveform panels.\n');
try
    figure('Color', 'w');
    plot_panels(winfra, 'alignWaveforms', 1);
    title('Representative infrasound channel, one per launch/day');
    saveas(gcf, fullfile(cfg.FigureDir, 'representative_infrasound_waveforms.png'));
catch ME
    warning('Representative infrasound plot failed: %s', ME.message);
end

try
    figure('Color', 'w');
    plot_panels(wseismic, 'alignWaveforms', 1);
    title('Representative seismic channel, one per launch/day');
    saveas(gcf, fullfile(cfg.FigureDir, 'representative_seismic_waveforms.png'));
catch ME
    warning('Representative seismic plot failed: %s', ME.message);
end

fprintf('Plotting average-frequency tracks for representative seismic channel.\n');
try
    gismo_ext.plotAverageFrequency(wseismic, ...
        'FrequencyLimits', [0 150], ...
        'Title', 'Representative seismic average frequency', ...
        'OutputFile', fullfile(cfg.FigureDir, 'representative_seismic_average_frequency.png'));
catch ME
    warning('Average-frequency plot failed. Make sure +gismo_ext is on the path. %s', ME.message);
end

fprintf('Figures/audio written under %s\n', cfg.WorkDir);
