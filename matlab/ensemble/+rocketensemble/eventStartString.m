function [dstr, title_string, start_time] = eventStartString(w, eventnum)
%EVENTSTARTSTRING Consistent event date strings for files and titles.

start_time = min(get(w, 'start'));
dstr = datestr(start_time, 'yyyymmdd.HHMMSS');
title_string = sprintf('Event %03d: %s', eventnum, datestr(start_time, 26));
end
