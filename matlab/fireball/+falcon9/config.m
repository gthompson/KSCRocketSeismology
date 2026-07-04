function cfg = config(varargin)
%CONFIG Return paths and run options for the Falcon 9 explosion workflow.
%
%   cfg = falcon9.config()
%   cfg = falcon9.config('ProjectRoot', path, 'MakeFigures', true)
%
% Edit this file, or pass name-value arguments, when running the workflow on
% a different computer.

    parser = inputParser;
    parser.addParameter('ProjectRoot', fullfile(getenv('HOME'), 'Dropbox', 'Rockets'), @(x) ischar(x) || isstring(x));
    parser.addParameter('AnalysisSubdir', fullfile('analysis', '20160901_SpaceXplosion'), @(x) ischar(x) || isstring(x));
    parser.addParameter('CacheFileName', 'explosion2.mat', @(x) ischar(x) || isstring(x));
    parser.addParameter('MakeFigures', true, @(x) islogical(x) || isnumeric(x));
    parser.addParameter('UseAntelope', true, @(x) islogical(x) || isnumeric(x));
    parser.parse(varargin{:});

    cfg = parser.Results;
    cfg.ProjectRoot = char(cfg.ProjectRoot);
    cfg.AnalysisDir = fullfile(cfg.ProjectRoot, cfg.AnalysisSubdir);
    cfg.FigureOutDir = fullfile(cfg.AnalysisDir, '20160901_results');
    cfg.CacheFile = fullfile(cfg.AnalysisDir, cfg.CacheFileName);
    cfg.DbPathPrimary = fullfile(cfg.ProjectRoot, 'db', '20160901_explosion');
    cfg.DbPathFallback = '/raid/data/rockets/dbspacexplosion';

    % Waveform import window.
    cfg.StartTime = datenum(2016, 9, 1, 13, 0, 0);
    cfg.EndTime = cfg.StartTime + 1/24;
    cfg.Network = 'FL';
    cfg.Station = 'BCHH';
    cfg.Channel = '*';

    % Receiver coordinates. Replace with database/metadata loading if available.
    cfg.ReceiverLat = [28.574182 28.573894 28.574004 28.574013 28.574013 28.574013];
    cfg.ReceiverLon = [-80.572410 -80.572352 -80.572561 -80.572360 -80.572360 -80.572360];

    % SLC-40 source coordinates.
    cfg.SourceLat = 28.562106;
    cfg.SourceLon = -80.57718;

    % Weather tower data from NASA / Lisa Huddleston email.
    cfg.RelativeHumidityPercent = 92;
    cfg.TemperatureF = 80;
    cfg.WindDirectionFromDeg = 150;
    cfg.WindDirectionDeg = mod(cfg.WindDirectionFromDeg + 180, 360);
    cfg.WindSpeedKnots = 10;
    cfg.WindSpeedMps = cfg.WindSpeedKnots * 0.514444;

    if ~exist(cfg.AnalysisDir, 'dir')
        mkdir(cfg.AnalysisDir);
    end
    if ~exist(cfg.FigureOutDir, 'dir')
        mkdir(cfg.FigureOutDir);
    end
end
