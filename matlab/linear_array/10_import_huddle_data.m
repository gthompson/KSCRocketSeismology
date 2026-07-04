%% 10_import_huddle_data.m
% Import/cache waveform data for the 2018 Astronaut Beach House huddle array.

clearvars;

cfg = huddle.config2018290();

if ~exist(cfg.OutputDir, 'dir')
    mkdir(cfg.OutputDir);
end

station = [];
network = [];
if ~isempty(cfg.NetworkMetadataScript) && exist(cfg.NetworkMetadataScript, 'file')
    run(cfg.NetworkMetadataScript);
elseif exist('network2batch_20181016', 'file')
    network2batch_20181016;
else
    warning('No network metadata script found. Using station positions from cfg.Stations.');
    station = cfg.Stations;
    network.code = cfg.NetworkCode;
end

if isempty(station)
    station = cfg.Stations;
end
if isempty(network) || ~isfield(network, 'code')
    network.code = cfg.NetworkCode;
end

station_lat = [station.lat];
station_lon = [station.lon];

[easting_m, northing_m] = seismoacoustics.latlonToEastNorth( ...
    cfg.Source.SLC41.Latitude, cfg.Source.SLC41.Longitude, ...
    station_lat, station_lon);

[easting_slc40_m, northing_slc40_m] = seismoacoustics.latlonToEastNorth( ...
    cfg.Source.SLC41.Latitude, cfg.Source.SLC41.Longitude, ...
    cfg.Source.SLC40.Latitude, cfg.Source.SLC40.Longitude);

fprintf('Loading huddle MiniSEED waveforms...\n');
w = rocketseis.loadMiniSeedWaveforms(cfg.DataDir, cfg.StationNames, cfg.FilePattern);

fprintf('Extracting analysis windows...\n');
w_overview = extract(w, 'time', cfg.OverviewStart, cfg.OverviewEnd);
w_analysis = extract(w, 'time', cfg.AnalysisStart, cfg.AnalysisEnd);

save(cfg.CacheFile, ...
    'cfg', 'network', 'station', 'easting_m', 'northing_m', ...
    'easting_slc40_m', 'northing_slc40_m', ...
    'w', 'w_overview', 'w_analysis');

fprintf('Saved cache: %s\n', cfg.CacheFile);
