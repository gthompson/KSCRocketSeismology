function change_dates = getNetworkChangeDates(station)
%GETNETWORKCHANGEDATES Unique floor(ondate/offdate) days from station metadata.

dates = [];
for k = 1:numel(station)
    dates = [dates, floor(datenum(station(k).ondate)), floor(datenum(station(k).offdate))]; %#ok<AGROW>
end
change_dates = unique(sort(dates));
end
