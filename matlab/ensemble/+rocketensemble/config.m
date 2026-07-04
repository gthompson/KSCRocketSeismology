function cfg = config()
%CONFIG Configuration for rocket ensemble analysis.
%
% Edit paths and event/channel parameters here rather than inside workflow
% scripts.

cfg.ProjectName = 'Rocket launch ensemble analysis';

% Antelope/CSS master database.
if ismac
    cfg.DbPath = '/Volumes/data/rockets/rocketmaster2';
else
    cfg.DbPath = '/raid/data/rockets/rocketmaster2';
end

cfg.WorkDir = fullfile(pwd, 'ensemble1');
cfg.CacheFile = fullfile(cfg.WorkDir, 'rocketmaster.mat');
cfg.MetricsFile = fullfile(cfg.WorkDir, 'rocket_ensemble_metrics.mat');
cfg.FigureDir = fullfile(cfg.WorkDir, 'figures');
cfg.AudioDir = fullfile(cfg.WorkDir, 'audio');
cfg.ExportAntelopeDb = true;
cfg.ExportDbSuffix = '_ensemble';

% Arrival preprocessing.
cfg.ArrivalPretriggerSeconds = 5;
cfg.ArrivalPosttriggerSeconds = 90;
cfg.ArrivalMetricMaxTimeDiffSeconds = 1.0;

% Event association.
% Use short windows (20 s) for individual airwave pulses, or longer windows
% (e.g. 30*60 s) for grouping launches. The ensemble scripts historically
% used both. The default below groups into launch-scale events.
cfg.AssociationWindowSeconds = 30 * 60;

% Event waveform extraction.
cfg.EventPretriggerSeconds = 30;
cfg.EventPosttriggerSeconds = 120;
cfg.EventChannelTag = 'FL.BCHH.*.*';
cfg.EventMetricMaxTimeDiffSeconds = 2.0;

% Channel grouping. These assume BCHH infrasound first and seismic last,
% matching the original scripts. Override if channel order differs.
cfg.InfrasoundIndices = 1:3;
cfg.SeismicIndices = 4:6;
cfg.SoundInfrasoundIndex = 3;
cfg.SoundSeismicIndex = 6;

cfg.InfrasoundSpectralObject = spectralobject(1024, 1000, 100, [30 80]);
cfg.SeismicSpectralObject = spectralobject(1024, 1000, 100, [70 140]);

cfg.SoundSpeedMps = 340;

% Diagnostics.
cfg.MakeRawWaveformPlots = true;
cfg.MakeSpectrogramPlots = true;
cfg.MakeSoundFiles = true;
cfg.MakeTrajectoryPlots = true;
cfg.MakeEnvelopePlots = true;
cfg.PublishMode = false;

% Event loop controls.
cfg.FirstEventToPlot = 1;
cfg.MaxEventsToPlot = Inf;

% One representative infrasound/seismic channel per launch for summary plots.
cfg.RepresentativeInfrasoundChannel = 'HD1_00';
cfg.RepresentativeSeismicChannel = 'HHZ_00';
cfg.MinimumDaysBetweenRepresentativeEvents = 1;
end
