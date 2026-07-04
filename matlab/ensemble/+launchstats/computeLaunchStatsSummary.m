function summary = computeLaunchStatsSummary(launch_table)
%COMPUTELAUNCHSTATSSUMMARY Prepare cumulative launch-statistics summary.

valid_time = isfinite(launch_table.DateTimeDatenum);
launch_table = launch_table(valid_time, :);

[~, order] = sort(launch_table.DateTimeDatenum);
launch_table = launch_table(order, :);

summary = table();
summary.DateTimeDatenum = launch_table.DateTimeDatenum;
summary.DateTime = launch_table.DateTime;
summary.AllLaunches = launch_table.ALL;
summary.SpaceXLaunches = launch_table.SPACEX;
summary.RecordedLaunches = launch_table.RECORDED;
summary.OtherRecordedEvents = launch_table.OTHER;

% Include non-cumulative metadata for possible later labeling/filtering.
summary.Company = launch_table.COMPANY;
summary.RocketType = launch_table.ROCKETTYPE;
summary.Payload = launch_table.PAYLOAD;
summary.SLC = launch_table.SLC;
summary.Orbit = launch_table.ORBIT;

% Useful scalar values.
summary.Properties.UserData.FinalAllLaunches = lastFinite(summary.AllLaunches);
summary.Properties.UserData.FinalSpaceXLaunches = lastFinite(summary.SpaceXLaunches);
summary.Properties.UserData.FinalRecordedLaunches = lastFinite(summary.RecordedLaunches);
summary.Properties.UserData.FinalOtherRecordedEvents = lastFinite(summary.OtherRecordedEvents);
end


function value = lastFinite(x)
idx = find(isfinite(x), 1, 'last');
if isempty(idx)
    value = NaN;
else
    value = x(idx);
end
end
