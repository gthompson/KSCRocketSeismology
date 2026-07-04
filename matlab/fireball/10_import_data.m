%% 10_IMPORT_DATA
% Build the Level-1 MATLAB cache for the Falcon 9 explosion workflow.
%
% This script replaces the older exploratory scripts:
%
%   - load_explosion_miniseed.m
%   - spacexplosion2ascii.m
%
% Those scripts were useful prototypes for reading MiniSEED into GISMO, but
% they were not reproducible workflow stages: they used hard-coded paths,
% did not save named cache files, and mixed data import with plotting.
%
% This script now supports three import modes:
%
%   1. Reuse an existing MAT cache, if present.
%   2. Import from an Antelope/CSS database using GISMO.
%   3. Import from MiniSEED files using GISMO.
%
% Outputs saved to cfg.CacheFile:
%
%   - cfg                         workflow configuration
%   - w                           continuous GISMO waveform objects
%   - source                      SLC-40 source location
%   - lat, lon                    receiver coordinates
%   - weather/sound-speed metadata
%
% The downstream stages should use this cache rather than importing waveform
% data directly.

clearvars
close all
clc

cfg = falcon9.config();
cache_file = cfg.CacheFile;

% -------------------------------------------------------------------------
% 1. Load existing cache if available.
% -------------------------------------------------------------------------

if exist(cache_file, 'file')
    fprintf('Cache already exists: %s\n', cache_file);
    fprintf('Loading cache rather than re-importing waveforms. Delete the cache to rebuild it.\n');
    load(cache_file);
    fprintf('10_import_data complete.\n');
    return
end

fprintf('Building cache: %s\n', cache_file);

% -------------------------------------------------------------------------
% 2. Shared metadata.
% -------------------------------------------------------------------------

lat = cfg.ReceiverLat;
lon = cfg.ReceiverLon;

source.lat = cfg.SourceLat;
source.lon = cfg.SourceLon;

relative_humidity_percent = cfg.RelativeHumidityPercent;
temperature_f = cfg.TemperatureF;
wind_direction_from_deg = cfg.WindDirectionFromDeg;
wind_direction_deg = cfg.WindDirectionDeg;
wind_speed_knots = cfg.WindSpeedKnots;
wind_speed_mps = cfg.WindSpeedMps;

temperature_c = physics.fahrenheit2celsius(temperature_f);
speed_of_sound_mps = physics.computeSpeedOfSound(temperature_c, relative_humidity_percent);

fprintf('Sound speed at %.1f C and %.1f%% RH: %.1f m/s\n', ...
    temperature_c, relative_humidity_percent, speed_of_sound_mps);

% -------------------------------------------------------------------------
% 3. Determine import mode.
% -------------------------------------------------------------------------

% Recommended values in +falcon9/config.m:
%
%   cfg.ImportMode = 'antelope';
%   cfg.ImportMode = 'miniseed';
%
% For backward compatibility, if cfg.ImportMode is absent we infer the mode
% from cfg.UseAntelope.

if isfield(cfg, 'ImportMode')
    import_mode = lower(string(cfg.ImportMode));
elseif isfield(cfg, 'UseAntelope') && cfg.UseAntelope
    import_mode = "antelope";
else
    import_mode = "miniseed";
end

% -------------------------------------------------------------------------
% 4. Import waveforms.
% -------------------------------------------------------------------------

switch import_mode

    case "antelope"
        % Import from Antelope/CSS database through GISMO.
        %
        % This is the preferred path when the original database is available.
        % It replaces the old ad-hoc datasource/waveform calls from prototype
        % scripts.

        if isfield(cfg, 'DbPathPrimary') && exist(cfg.DbPathPrimary, 'dir')
            db_path = cfg.DbPathPrimary;
        elseif isfield(cfg, 'DbPathFallback')
            db_path = cfg.DbPathFallback;
        else
            error('10_import_data:MissingDbPath', ...
                'cfg.ImportMode is antelope, but no database path is configured.');
        end

        if ~exist(db_path, 'dir')
            error('10_import_data:MissingDatabase', ...
                'Antelope/CSS database path does not exist: %s', db_path);
        end

        ds = datasource('antelope', db_path);
        scnl = scnlobject(cfg.Station, cfg.Channel, cfg.Network);

        fprintf('Loading waveform data from Antelope/CSS database:\n  %s\n', db_path);
        w = waveform(ds, scnl, cfg.StartTime, cfg.EndTime);

    case "miniseed"
        % Import from MiniSEED files through GISMO.
        %
        % This replaces load_explosion_miniseed.m and spacexplosion2ascii.m.
        % Configure one of the following in +falcon9/config.m:
        %
        %   cfg.MiniSeedFiles = {'/path/file1.mseed', '/path/file2.mseed'};
        %
        % or
        %
        %   cfg.MiniSeedDir = '/path/to/mseed';
        %   cfg.MiniSeedPattern = '*.mseed';      % optional
        %
        % The older prototype scripts used datasource('miniseed', file).
        % Here we apply that consistently and concatenate each file's
        % waveform object into one array.

        mseed_files = {};

        if isfield(cfg, 'MiniSeedFiles') && ~isempty(cfg.MiniSeedFiles)
            mseed_files = cfg.MiniSeedFiles;
            if ischar(mseed_files) || isstring(mseed_files)
                mseed_files = cellstr(mseed_files);
            end
        elseif isfield(cfg, 'MiniSeedDir') && ~isempty(cfg.MiniSeedDir)
            if isfield(cfg, 'MiniSeedPattern') && ~isempty(cfg.MiniSeedPattern)
                pattern = cfg.MiniSeedPattern;
            else
                pattern = '*.mseed';
            end

            listing = dir(fullfile(cfg.MiniSeedDir, pattern));
            mseed_files = fullfile({listing.folder}, {listing.name});
        end

        if isempty(mseed_files)
            error('10_import_data:MissingMiniSeedFiles', ...
                ['cfg.ImportMode is miniseed, but no MiniSEED files are configured. ' ...
                 'Set cfg.MiniSeedFiles or cfg.MiniSeedDir in +falcon9/config.m.']);
        end

        fprintf('Loading %d MiniSEED file(s)...\n', numel(mseed_files));

        w = [];
        for n = 1:numel(mseed_files)
            this_file = mseed_files{n};

            if ~exist(this_file, 'file')
                error('10_import_data:MissingMiniSeedFile', ...
                    'MiniSEED file does not exist: %s', this_file);
            end

            fprintf('  %s\n', this_file);
            ds = datasource('miniseed', this_file);

            if isfield(cfg, 'Station') && isfield(cfg, 'Channel') && isfield(cfg, 'Network')
                scnl = scnlobject(cfg.Station, cfg.Channel, cfg.Network);
                this_w = waveform(ds, scnl, cfg.StartTime, cfg.EndTime);
            else
                % Some GISMO versions can read all channels from a MiniSEED
                % datasource without an explicit SCNL object.
                this_w = waveform(ds, cfg.StartTime, cfg.EndTime);
            end

            w = [w this_w]; %#ok<AGROW>
        end

    otherwise
        error('10_import_data:UnknownImportMode', ...
            'Unknown cfg.ImportMode: %s. Use ''antelope'' or ''miniseed''.', import_mode);
end

% -------------------------------------------------------------------------
% 5. Save reproducible Level-1 cache.
% -------------------------------------------------------------------------

fprintf('Saving Level-1 cache:\n  %s\n', cache_file);
save(cache_file, ...
    'cfg', ...
    'w', ...
    'source', ...
    'lat', ...
    'lon', ...
    'relative_humidity_percent', ...
    'temperature_f', ...
    'temperature_c', ...
    'speed_of_sound_mps', ...
    'wind_direction_from_deg', ...
    'wind_direction_deg', ...
    'wind_speed_knots', ...
    'wind_speed_mps');

fprintf('10_import_data complete.\n');
