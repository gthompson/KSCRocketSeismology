function jdaystr = datenumToJdayString(dnum)
%DATENUMTOJDAYSTRING Convert MATLAB datenum to three-digit Julian day.

[y, ~, ~] = datevec(dnum);
day1 = datenum(y, 1, 1);
jday = 1 + floor(dnum) - day1;
jdaystr = sprintf('%03d', jday);
end
