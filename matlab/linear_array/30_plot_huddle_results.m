%% 30_plot_huddle_results.m
% Regenerate huddle array figures.

clearvars;

cfg = huddle.config2018290();

if ~exist(cfg.CacheFile, 'file')
    error('Cache file not found: %s. Run 10_import_huddle_data.m and 20_analyze_huddle_xcorr.m first.', cfg.CacheFile);
end

load(cfg.CacheFile);

if ~exist(cfg.OutputDir, 'dir')
    mkdir(cfg.OutputDir);
end

fprintf('Plotting array geometry...\n');
station_labels = {station.name};
seismoacoustics.plotArrayMap( ...
    easting_m, northing_m, ...
    'StationLabels', station_labels, ...
    'SourceEastM', [0; easting_slc40_m], ...
    'SourceNorthM', [0; northing_slc40_m], ...
    'SourceLabels', {'SLC41', 'SLC40'}, ...
    'Title', 'Astronaut Beach House huddle-array geometry', ...
    'OutputFile', fullfile(cfg.OutputDir, 'huddle_array_map.png'));

fprintf('Plotting waveform panels, if GISMO plotting is available...\n');
try
    figure('Color', 'w');
    plot_panels(w_overview);
    title('Huddle array overview waveforms');
    saveas(gcf, fullfile(cfg.OutputDir, 'huddle_waveform_overview.png'));
catch ME
    warning('Waveform panel plot skipped: %s', ME.message);
end

try
    figure('Color', 'w');
    plot_panels(w_analysis);
    title('Huddle array analysis-window waveforms');
    saveas(gcf, fullfile(cfg.OutputDir, 'huddle_waveform_analysis_window.png'));
catch ME
    warning('Analysis waveform panel plot skipped: %s', ME.message);
end

fprintf('Plotting cross-correlation timing tracks...\n');
if exist('delay_tracks', 'var')
    seismoacoustics.plotXcorrTracks( ...
        delay_tracks.times, ...
        delay_tracks.relative_delay_seconds, ...
        'Correlations', delay_tracks.relative_correlation, ...
        'StationLabels', delay_tracks.station_names, ...
        'FlipSign', true, ...
        'Title', 'Huddle test rocket launch cross-correlation analysis', ...
        'OutputFile', fullfile(cfg.OutputDir, 'huddle_xcorr_tracks.png'));
else
    warning('delay_tracks not found. Run 20_analyze_huddle_xcorr.m first.');
end

fprintf('Plotting amplitude-ratio diagnostics...\n');
if exist('amplitude_result', 'var')
    huddle.plotAmplitudeRatios(amplitude_result, ...
        fullfile(cfg.OutputDir, 'huddle_amplitude_ratios.png'));
else
    warning('amplitude_result not found. Run 20_analyze_huddle_xcorr.m first.');
end

fprintf('Figures written to: %s\n', cfg.OutputDir);
