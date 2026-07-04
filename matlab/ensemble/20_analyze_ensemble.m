%% 20_analyze_ensemble.m
% Compute ensemble-level metrics from the preprocessed rocketmaster catalog.

clearvars;

cfg = rocketensemble.config();

if ~exist(cfg.CacheFile, 'file')
    error('Cache not found: %s. Run 10_preprocess_rocketmaster.m first.', cfg.CacheFile);
end

load(cfg.CacheFile, 'cfg', 'catalogobj');

fprintf('Computing ensemble metrics from %d catalog events.\n', catalogobj.numberOfEvents);

event_metrics = rocketensemble.computeEnsembleMetrics(catalogobj, cfg);
[winfra, wseismic] = rocketensemble.extractRepresentativeWaveforms(catalogobj, cfg);

save(cfg.MetricsFile, 'cfg', 'event_metrics', 'winfra', 'wseismic', '-v7.3');

fprintf('Saved metrics: %s\n', cfg.MetricsFile);
