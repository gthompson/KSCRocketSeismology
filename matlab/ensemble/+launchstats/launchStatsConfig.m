function cfg = launchStatsConfig()
%LAUNCHSTATSCONFIG Configuration for launch-statistics overview plots.

cfg.WorkbookFile = '/Users/gt/Dropbox/KSC_rocket_launches_2016_onwards_v3.xlsx';
cfg.SheetName = 'Sheet1';
cfg.OutputDir = fullfile(pwd, 'launch_statistics_results');

% Excel serial date system used by the legacy script:
% dnum = DATE - 1 + datenum(1899,12,31) + TIME
cfg.ExcelDateOrigin = datenum(1899, 12, 31) - 1;
end
