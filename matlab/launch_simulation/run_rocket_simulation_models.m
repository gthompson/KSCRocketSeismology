%% run_rocket_simulation_models.m
% Standalone runner for the rocket ascent/Doppler toy models.

clearvars;
close all;

outdir = fullfile(pwd, 'rocket_model_figures');
if ~exist(outdir, 'dir')
    mkdir(outdir);
end

cfg = rocketmodels.falcon9Defaults();

sim1d = rocketmodels.simulateAscent1D('Config', cfg);
rocketmodels.plotAscentSummary1D(sim1d, ...
    'OutputFile', fullfile(outdir, 'rocket_ascent_1d_summary.png'));

sim2d = rocketmodels.simulateAscent2D('Config', cfg);
rocketmodels.plotAscentSummary2D(sim2d, ...
    'OutputPrefix', fullfile(outdir, 'rocket_ascent_2d'));

save(fullfile(outdir, 'rocket_ascent_models.mat'), 'cfg', 'sim1d', 'sim2d');

fprintf('Wrote model figures and MAT file to %s\n', outdir);
