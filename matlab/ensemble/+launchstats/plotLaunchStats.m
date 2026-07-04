function ax = plotLaunchStats(summary, varargin)
%PLOTLAUNCHSTATS Plot cumulative launch statistics for ensemble context.
%
% ax = rocketensemble.plotLaunchStats(summary, ...)
%
% Name-value options:
%   OutputFile
%   Title
%   UseDatetimeAxis  true/false, default true

p = inputParser;
p.addRequired('summary', @istable);
p.addParameter('OutputFile', '', @(x) ischar(x) || isstring(x));
p.addParameter('Title', 'Rocket launch ensemble context', @(x) ischar(x) || isstring(x));
p.addParameter('UseDatetimeAxis', true, @(x) islogical(x) || isnumeric(x));
p.parse(summary, varargin{:});
opt = p.Results;

figure('Color', 'w');
ax = axes;
hold(ax, 'on');

if logical(opt.UseDatetimeAxis) && ismember('DateTime', summary.Properties.VariableNames)
    x = summary.DateTime;
    plot(ax, x, summary.AllLaunches, '^-', 'LineWidth', 1.2);
    plot(ax, x, summary.SpaceXLaunches, '^-', 'LineWidth', 1.2);
    plot(ax, x, summary.RecordedLaunches, '^-', 'LineWidth', 1.2);
    plot(ax, x, summary.OtherRecordedEvents, '*-', 'LineWidth', 1.2);
else
    x = summary.DateTimeDatenum;
    plot(ax, x, summary.AllLaunches, '^-', 'LineWidth', 1.2);
    plot(ax, x, summary.SpaceXLaunches, '^-', 'LineWidth', 1.2);
    plot(ax, x, summary.RecordedLaunches, '^-', 'LineWidth', 1.2);
    plot(ax, x, summary.OtherRecordedEvents, '*-', 'LineWidth', 1.2);
    datetick(ax, 'x', 'keeplimits');
end

ylabel(ax, 'Cumulative number');
xlabel(ax, 'Date');
title(ax, opt.Title);
legend(ax, ...
    'Launches - any', ...
    'Launches - SpaceX', ...
    'Launches recorded', ...
    'Other events recorded', ...
    'Location', 'northwest');

grid(ax, 'on');
box(ax, 'on');
hold(ax, 'off');

if strlength(string(opt.OutputFile)) > 0
    saveas(gcf, char(opt.OutputFile));
end
end
