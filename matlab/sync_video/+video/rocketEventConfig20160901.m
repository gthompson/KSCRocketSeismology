function cfg = rocketEventConfig20160901()
%ROCKETEVENTCONFIG20160901 Configuration for the 2016-09-01 Falcon 9 event.
%
% cfg = falcon9.rocketEventConfig20160901()
%
% Returns a configuration structure used by 40_make_synchronized_video.m and
% falcon9.syncVideoWithWaveforms.  The paths below are examples based on the
% original scripts and should be edited on a new machine.
%
% Time convention:
%   All absolute times are MATLAB datenums in UTC.
%   Video.StartTime is the UTC time of the first video frame, plus any
%   frame-specific offset already applied.

SECONDS_PER_DAY = 86400;

cfg.EventName = 'Falcon9_StaticFire_Anomaly_20160901';
cfg.Description = 'SpaceX Falcon 9 static-fire explosion, LC-40, Kennedy Space Center';
cfg.TimeZone = 'UTC';

%% Output
cfg.OutputDir = fullfile(pwd, 'video_sync_output');
cfg.FrameDir = fullfile(cfg.OutputDir, 'frames');
cfg.MovieFile = fullfile(cfg.OutputDir, 'synchronized_video.avi');
cfg.MovieProfile = 'Motion JPEG AVI';   % portable and much smaller than Uncompressed AVI
cfg.MovieQuality = 95;

%% Render window
cfg.FPS = 30;
cfg.StartTime = datenum(2016,9,1,13,7,5);
cfg.EndTime   = datenum(2016,9,1,13,7,45);
cfg.ZoomWindowSeconds = 5;

%% Expected arrival-time overlays after a visual source time
cfg.Overlay.DelaysSeconds = [1.0, 4.0];
cfg.Overlay.Labels = {'seismic estimate', 'airwave estimate'};
cfg.Overlay.LineStyles = {'g', 'r'};  % MATLAB color/style strings

%% Video sources
% Mode can be:
%   'single'  - one video panel, e.g., public YouTube-derived clip
%   'multi'   - multiple simultaneous camera panels, e.g., proprietary clips
cfg.VideoMode = 'single';

% Public / YouTube-derived example. Edit VideoFile for local location.
cfg.Videos = struct([]);
cfg.Videos(1).Name = 'YouTube public clip';
cfg.Videos(1).VideoFile = fullfile(cfg.OutputDir, 'SpaceXStaticFireAnomalyAMOS_6_Youtube.mov');
cfg.Videos(1).StartTime = datenum(2016,9,1,13,6,0) + (1-1)/cfg.FPS/SECONDS_PER_DAY;
cfg.Videos(1).Panel = 1;
cfg.Videos(1).FrameStride = 1;

% Proprietary/multicam SpaceX example. Uncomment and edit paths to use.
% cfg.VideoMode = 'multi';
% videoDir = '/path/to/proprietary/spacex/videos';
% cfg.Videos(1) = localVideo('f9-29_nw_ptz',    fullfile(videoDir,'f9-29_nw_ptz.mov'),    datenum(2016,9,1,13,7,7)+(1-1)/cfg.FPS/SECONDS_PER_DAY, 1);
% cfg.Videos(2) = localVideo('f9-29_ne_twr',    fullfile(videoDir,'f9-29_ne_twr.mov'),    datenum(2016,9,1,13,7,6)+(6-1)/cfg.FPS/SECONDS_PER_DAY, 2);
% cfg.Videos(3) = localVideo('f9-29_ucs3',      fullfile(videoDir,'f9-29_ucs3.mov'),      datenum(2016,9,1,13,7,12)+(1-1)/cfg.FPS/SECONDS_PER_DAY, 3);
% cfg.Videos(4) = localVideo('f9-29_west_fixed',fullfile(videoDir,'f9-29_west_fixed.mov'),datenum(2016,9,1,13,7,6)+(7-1)/cfg.FPS/SECONDS_PER_DAY, 4);

%% Waveform source
% 'mat' expects cfg.WaveformMatFile containing variable w.
% 'antelope' uses GISMO datasource/waveform calls.
cfg.WaveformMode = 'antelope';
cfg.WaveformMatFile = fullfile(cfg.OutputDir, 'video_sync_waveforms.mat');
cfg.AntelopeDbPath = '/Volumes/data/rockets/rocketmaster2';
cfg.ChannelTag = 'FL.BCHH.*.*';

%% Waveform panels
% Indices refer to the GISMO waveform vector w after loading. For a MAT file,
% store w in the same order or edit these indices.
cfg.InfrasoundIndex = 1;
cfg.SeismicIndex = 6;
cfg.InfrasoundZoomIndices = [1 2 3];
cfg.SeismicZNEIndices = [6 5 4];
cfg.SeismicRotateBackAzimuth = 199.5; % degrees; used only if threecomp exists

cfg.MainPanels(1).Name = 'Infrasound';
cfg.MainPanels(1).WaveformIndex = cfg.InfrasoundIndex;
cfg.MainPanels(1).Scale = 1.0;
cfg.MainPanels(1).Units = 'Pa';
cfg.MainPanels(1).YLim = [-200 800];

cfg.MainPanels(2).Name = 'Vertical seismic';
cfg.MainPanels(2).WaveformIndex = cfg.SeismicIndex;
cfg.MainPanels(2).Scale = 1e-6;
cfg.MainPanels(2).Units = 'mm/s';
cfg.MainPanels(2).YLim = [-3 3];

%% Audio export
cfg.Audio.Enabled = true;
cfg.Audio.InterpolationFactor = 16;
cfg.Audio.Tracks(1).Name = 'infrasound';
cfg.Audio.Tracks(1).WaveformIndex = cfg.InfrasoundIndex;
cfg.Audio.Tracks(1).OutputFile = fullfile(cfg.OutputDir, 'infrasound_audio.wav');
cfg.Audio.Tracks(2).Name = 'seismic';
cfg.Audio.Tracks(2).WaveformIndex = cfg.SeismicIndex;
cfg.Audio.Tracks(2).OutputFile = fullfile(cfg.OutputDir, 'seismic_audio.wav');

%% Display
cfg.Figure.Width = 2667;
cfg.Figure.Height = 1500;
cfg.Figure.ReductionFactor = 0.5;
cfg.FontSize = 16;

end

function v = localVideo(name, file, startTime, panel)
v.Name = name;
v.VideoFile = file;
v.StartTime = startTime;
v.Panel = panel;
v.FrameStride = 1;
end
