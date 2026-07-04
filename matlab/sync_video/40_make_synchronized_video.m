%% 40_make_synchronized_video.m
% Optional visualization module for synchronizing rocket-event video with
% seismic and infrasound waveform data.
%
% This script is intentionally separate from the reproducible science
% workflow (10/20/30). It is for presentations, outreach, timing checks,
% and qualitative comparison of visible events with waveform arrivals.
%
% To adapt to another rocket event:
%   1. Copy +falcon9/rocketEventConfig20160901.m to a new config function.
%   2. Edit event time, video files/start times, waveform source, and channels.
%   3. Set cfg.EventConfigFunction below to your new function name.
%   4. Run this script.

clearvars;
close all;
clc;

%% Select event configuration
cfg = falcon9.rocketEventConfig20160901();

% Example for a future event:
% cfg = launchname.rocketEventConfigYYYYMMDD();

%% User-adjustable run options
cfg.RenderFrames = true;       % false = make a layout preview only
cfg.WriteMovie   = true;       % true = assemble rendered frames into movie
cfg.WriteAudio   = true;       % true = export audio tracks from selected waveforms
cfg.FrameStep    = 1;          % render every Nth video frame; use >1 for testing
cfg.MaxFrames    = Inf;        % set small number, e.g. 60, for a quick test
cfg.Verbose      = true;

%% Load waveform data
% If cfg.WaveformMode = 'mat', cfg.WaveformMatFile must contain variable w.
% If cfg.WaveformMode = 'antelope', GISMO/Antelope are required.
w = video.loadVideoSyncWaveforms(cfg);

%% Render synchronized visualization
results = video.syncVideoWithWaveforms(cfg, w);

disp(results);
