%% falcon9fireball_wrapper.m
% Convenience runner for the refactored Falcon 9 explosion workflow.
%
% Core reproducible analysis stages:
%
%   10_import_data.m      Build or load the Level-1 waveform/cache MAT file.
%   20_process_events.m   Group events, correlate, beamform, pick amplitudes.
%   30_make_figures.m     Regenerate figures and figure-adjacent products.
%
% Optional visualization stage:
%
%   40_make_synchronized_video.m
%
% The 40_* stage is disabled by default because it depends on local video
% files and may take substantially longer than the science workflow.
%
% To include video synchronization, set this variable before running:
%
%   run_video_sync = true;
%   falcon9fireball_wrapper
%
% To skip one of the core stages during debugging, set one or more of:
%
%   run_import  = false;
%   run_process = false;
%   run_figures = false;

%% Default run controls
if ~exist('run_import', 'var') || isempty(run_import)
    run_import = true;
end

if ~exist('run_process', 'var') || isempty(run_process)
    run_process = true;
end

if ~exist('run_figures', 'var') || isempty(run_figures)
    run_figures = true;
end

if ~exist('run_video_sync', 'var') || isempty(run_video_sync)
    run_video_sync = false;
end

%% Run workflow
fprintf('\nFalcon 9 fireball MATLAB workflow\n');
fprintf('----------------------------------\n');

if run_import
    fprintf('\n[10] Import/cache waveform data\n');
    run('10_import_data.m');
else
    fprintf('\n[10] Skipped import/cache stage\n');
end

if run_process
    fprintf('\n[20] Process events and measurements\n');
    run('20_process_events.m');
else
    fprintf('\n[20] Skipped processing stage\n');
end

if run_figures
    fprintf('\n[30] Make figures\n');
    run('30_make_figures.m');
else
    fprintf('\n[30] Skipped figure stage\n');
end

if run_video_sync
    fprintf('\n[40] Make synchronized video\n');
    run('40_make_synchronized_video.m');
else
    fprintf('\n[40] Skipped synchronized-video stage (set run_video_sync = true to enable)\n');
end

fprintf('\nWorkflow complete.\n');
