function tf = stationActiveOnDate(station, day_dnum)
%STATIONACTIVEONDATE True if station is active on a given whole-day datenum.

tf = floor(datenum(station.ondate)) <= day_dnum && datenum(station.offdate) >= day_dnum;
end
