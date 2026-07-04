# Rocket launch statistics overview

This refactor replaces the legacy auto-generated script:

```text
plot_rocket_launch_stats.m
```

with a small, reusable ensemble-overview module.

## Purpose

The launch statistics figure provides framing for an ensemble-analysis paper by showing:

- cumulative KSC/Cape launches,
- cumulative SpaceX launches,
- launches recorded by the seismic/infrasound network,
- other recorded rocket-related events.

## Main driver

```matlab
40_plot_launch_statistics
```

## Package functions

```text
+rocketensemble/launchStatsConfig.m
+rocketensemble/loadLaunchStatsSpreadsheet.m
+rocketensemble/computeLaunchStatsSummary.m
+rocketensemble/plotLaunchStats.m
```

## Configuration

Edit:

```matlab
+rocketensemble/launchStatsConfig.m
```

to set:

```matlab
cfg.WorkbookFile = '/path/to/KSC_rocket_launches_2016_onwards_v3.xlsx';
cfg.SheetName = 'Sheet1';
cfg.OutputDir = fullfile(pwd, 'launch_statistics_results');
```

## Outputs

The driver writes:

```text
launch_statistics_results/
  rocket_launch_cumulative_statistics.png
  launch_statistics_summary.mat
```

## Dependencies

Required:

- MATLAB
- Excel-reading support via `readtable`/`detectImportOptions`, or legacy `xlsread`

No GISMO or Antelope dependencies are needed for this overview plot.
