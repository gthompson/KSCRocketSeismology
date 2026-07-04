function outfile = writeStationInventory(station, cfg)
%WRITESTATIONINVENTORY Write tab-delimited station inventory table.

outfile = fullfile(cfg.OutputDir, 'KSCnetwork.txt');

fid = fopen(outfile, 'w');
if fid < 0
    error('Could not open %s for writing.', outfile);
end
cleanup = onCleanup(@() fclose(fid));

fprintf(fid, 'net.sta.loc\tlatitude\tlongitude\tondate\toffdate\tdistance_km\tazimuth_deg\tnotes\n');

if cfg.IncludeLegacyInventoryRows
    writeLegacyRows(fid);
end

for k = 1:numel(station)
    ondate = datestr(floor(datenum(station(k).ondate)), 'yyyy-mm-dd');
    offdate = datestr(ceil(datenum(station(k).offdate)), 'yyyy-mm-dd');
    nsl = sprintf('%s.%s.%s', cfg.Network.Code, station(k).name, station(k).location);

    if isfield(station(k), 'distanceKm')
        distance_km = station(k).distanceKm;
    else
        distance_km = NaN;
    end

    if isfield(station(k), 'azimuthDeg')
        azimuth_deg = station(k).azimuthDeg;
    else
        azimuth_deg = NaN;
    end

    notes = '';
    if isfield(station(k), 'notes')
        notes = station(k).notes;
    end

    fprintf(fid, '%s\t%.6f\t%.6f\t%s\t%s\t%.3f\t%.2f\t%s\n', ...
        nsl, station(k).lat, station(k).lon, ondate, offdate, ...
        distance_km, azimuth_deg, notes);
end

delete(cleanup);
end


function writeLegacyRows(fid)
fprintf(fid, 'FL.BCHH.00\t28.574017\t-80.572376\t2016-02-24\t2016-10-06\tNaN\tNaN\tlegacy fixed row\n');
fprintf(fid, 'FL.FIRE.00\t28.549746\t-80.618641\t2016-02-24\t2016-05-01\tNaN\tNaN\tlegacy fixed row\n');
fprintf(fid, 'FL.TANK.00\t28.517301\t-80.636491\t2016-02-24\t2016-05-01\tNaN\tNaN\tlegacy fixed row\n');
fprintf(fid, 'FL.BCHH1.00\t28.573477\t-80.572377\t2017-05-??\t2019-02-03\tNaN\tNaN\tlegacy fixed row\n');
fprintf(fid, 'FL.BCHH1.10\t28.573494\t-80.572381\t2019-02-04\t2100-01-01\tNaN\tNaN\tlegacy fixed row\n');
fprintf(fid, 'FL.BCHH2.00\t28.57????\t-80.57????\t2017-05-??\t2100-01-01\tNaN\tNaN\tlegacy fixed row\n');
fprintf(fid, 'AM.RS3D.00\t28.573499\t-80.572353\t2018-??-??\t201?-??-??\tNaN\tNaN\tlegacy fixed row\n');
fprintf(fid, 'FL.DVEL4.00\t28.578731\t-80.607844\t2017-05-??\t2100-01-01\tNaN\tNaN\tlegacy fixed row\n');
end
