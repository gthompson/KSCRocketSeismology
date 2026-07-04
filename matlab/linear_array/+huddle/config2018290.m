function cfg = config2018290()
%CONFIG2018290 Configuration for the 2018-290 huddle array analysis.

cfg.ProjectName = 'Huddle linear-array rocket-launch analysis';
cfg.EventDate = datenum(2018, 10, 17);
cfg.NetworkCode = 'FL';
cfg.Channel = 'EHZ';

cfg.NetworkMetadataScript = 'network2batch_20181016.m';

cfg.Source.SLC41.Latitude = 28.5835;
cfg.Source.SLC41.Longitude = -80.5828;
cfg.Source.SLC41.ElevationM = 0;

cfg.Source.SLC40.Latitude = 28.5620;
cfg.Source.SLC40.Longitude = -80.5772;
cfg.Source.SLC40.ElevationM = 0;

cfg.DataDir = '/Users/gt/shared/RocketSeis/EVENTDB/290';
cfg.FilePattern = 'FL.%s..EHZ.D.2018.290';
cfg.StationNames = {'BHP2','BHP3','BHP4','BHP5','BHP6','BHP7','BHP8'};

for k = 1:numel(cfg.StationNames)
    cfg.Stations(k).name = cfg.StationNames{k}; %#ok<AGROW>
    cfg.Stations(k).lat = NaN; %#ok<AGROW>
    cfg.Stations(k).lon = NaN; %#ok<AGROW>
    cfg.Stations(k).elev = NaN; %#ok<AGROW>
end

cfg.OverviewStart = datenum(2018, 10, 17, 4, 14, 0);
cfg.OverviewEnd   = datenum(2018, 10, 17, 4, 20, 0);
cfg.AnalysisStart = datenum(2018, 10, 17, 4, 15, 0);
cfg.AnalysisEnd   = datenum(2018, 10, 17, 4, 16, 0);

cfg.StaSeconds = 0.7;
cfg.LtaSeconds = 7.0;
cfg.TriggerOn = 3.0;
cfg.TriggerOff = 1.5;
cfg.MinimumEventDurationSeconds = 60.0;
cfg.RsamWindowSeconds = 0.2;

cfg.XcorrWindowSeconds = 1.5;
cfg.XcorrStepSeconds = 0.1;
cfg.MinimumCorrelation = 0.1;

cfg.AmplitudeRatioIndexRange = 410:430;
cfg.ReferenceStationIndex = 1;

cfg.OutputDir = fullfile(pwd, 'huddle_results');
cfg.CacheFile = fullfile(cfg.OutputDir, 'huddle_2018290_cache.mat');
end
