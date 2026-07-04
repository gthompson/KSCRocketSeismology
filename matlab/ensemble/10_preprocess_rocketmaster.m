%% 10_preprocess_rocketmaster.m
% Build or update the rocketmaster ensemble Catalog cache from Antelope.

clearvars;

cfg = rocketensemble.config();

if ~exist(cfg.WorkDir, 'dir')
    mkdir(cfg.WorkDir);
end
if ~exist(cfg.FigureDir, 'dir')
    mkdir(cfg.FigureDir);
end
if ~exist(cfg.AudioDir, 'dir')
    mkdir(cfg.AudioDir);
end

fprintf('Rocket ensemble preprocessing\n');
fprintf('Database: %s\n', cfg.DbPath);
fprintf('Cache:    %s\n', cfg.CacheFile);

if exist(cfg.CacheFile, 'file')
    fprintf('Loading existing cache.\n');
    load(cfg.CacheFile, 'cfg', 'ds', 'arrivalobj', 'catalogobj');
else
    fprintf('Creating datasource.\n');
    ds = datasource('antelope', cfg.DbPath);

    fprintf('Retrieving arrivals.\n');
    arrivalobj = rocketensemble.loadArrivals(cfg.DbPath);

    fprintf('Adding short waveforms to arrivals.\n');
    arrivalobj = rocketensemble.addArrivalWaveforms(arrivalobj, ds, cfg);

    fprintf('Adding metrics to arrivals.\n');
    arrivalobj = rocketensemble.addArrivalMetrics(arrivalobj, cfg);

    fprintf('Associating arrivals into catalog events.\n');
    catalogobj = rocketensemble.associateArrivals(arrivalobj, cfg.AssociationWindowSeconds);

    fprintf('Adding event waveforms.\n');
    catalogobj = rocketensemble.addEventWaveforms(catalogobj, ds, cfg);

    fprintf('Adding waveform metrics to event waveforms.\n');
    catalogobj = rocketensemble.addEventWaveformMetrics(catalogobj, cfg);

    save(cfg.CacheFile, 'cfg', 'ds', 'arrivalobj', 'catalogobj', '-v7.3');
    fprintf('Saved cache: %s\n', cfg.CacheFile);
end

if cfg.ExportAntelopeDb
    try
        export_db = rocketensemble.writeCatalogToAntelope(catalogobj, cfg);
        fprintf('Wrote derived Antelope DB: %s\n', export_db);
    catch ME
        warning('Could not write derived Antelope DB: %s', ME.message);
    end
end

try
    catalogobj.list_waveform_metrics();
catch ME
    warning('Could not list waveform metrics: %s', ME.message);
end

fprintf('Preprocessing complete.\n');
