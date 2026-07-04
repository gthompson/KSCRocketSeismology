%% 40_plot_launch_statistics.m
% Plot launch-count context for the rocket ensemble analysis paper.
%
% This stage reads the KSC/Cape launch spreadsheet and produces a framing
% figure showing cumulative launches, SpaceX launches, recorded launches,
% and other recorded events.

clearvars;

cfg = launchstats.launchStatsConfig();

if ~exist(cfg.OutputDir, 'dir')
    mkdir(cfg.OutputDir);
end

launch_table = launchstats.loadLaunchStatsSpreadsheet( ...
    cfg.WorkbookFile, ...
    'Sheet', cfg.SheetName);

summary = launchstats.computeLaunchStatsSummary(launch_table);

launchstats.plotLaunchStats(summary, ...
    'OutputFile', fullfile(cfg.OutputDir, 'rocket_launch_cumulative_statistics.png'), ...
    'Title', 'KSC/Cape rocket launches and recorded events');

save(fullfile(cfg.OutputDir, 'launch_statistics_summary.mat'), ...
    'cfg', 'launch_table', 'summary');

fprintf('Wrote launch statistics to %s\n', cfg.OutputDir);
