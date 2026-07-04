function pf_files = writeNetworkPfFiles(station, cfg)
%WRITENETWORKPFFILES Write dbbuild networkYYYYJJJ.pf files.
%
% Each file contains stations active on a network-change date.

change_dates = passcal.getNetworkChangeDates(station);
pf_files = strings(numel(change_dates), 1);

for k = 1:numel(change_dates)
    this_day = change_dates(k);
    yyyyjjj = sprintf('%s%s', datestr(this_day, 'yyyy'), passcal.datenumToJdayString(this_day));
    outfile = fullfile(cfg.OutputDir, sprintf('network%s.pf', yyyyjjj));
    pf_files(k) = outfile;

    fid = fopen(outfile, 'w');
    if fid < 0
        error('Could not open %s for writing.', outfile);
    end

    cleanup = onCleanup(@() fclose(fid));

    fprintf(fid, 'net %s %s\n\n', cfg.Network.Code, cfg.Network.Name);

    for i = 1:numel(station)
        if passcal.stationActiveOnDate(station(i), this_day)
            writeStationBlock(fid, station(i), cfg.DefaultGain);
        end
    end

    delete(cleanup);
end
end


function writeStationBlock(fid, s, gain)
fprintf(fid, 'sta %s %.5f %.5f %.3f %s\n', ...
    s.name, s.lat, s.lon, s.elev, s.description);
fprintf(fid, 'time %s\n', datestr(datenum(s.ondate), 'mm/dd/yyyy HH:MM:SS'));
fprintf(fid, 'datalogger %s\n', s.datalogger);
fprintf(fid, 'sensor %s %d %s\n', s.sensor, s.burialdepth, s.sensorSN);

if strcmpi(s.sensor, 'l22')
    fprintf(fid, 'axis Z 0 180 - 1 %d\n', gain);
else
    fprintf(fid, 'axis Z 0 0 - 1 %d\n', gain);
end

orientation = round(s.orientationFromGeographicNorth);
fprintf(fid, 'axis N %d 90 - 2 %d\n', orientation, gain);
fprintf(fid, 'axis E %d 90 - 3 %d\n', 90 + orientation, gain);

fprintf(fid, 'samplerate %dsps\n', s.samplerate);
fprintf(fid, 'channel Z EHZ\n');
fprintf(fid, 'channel N EH1\n');
fprintf(fid, 'channel E EH2\n');
fprintf(fid, 'add\n\n');
fprintf(fid, 'close %s %s\n\n', s.name, datestr(datenum(s.offdate), 'mm/dd/yyyy'));
end
