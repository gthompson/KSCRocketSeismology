function w = loadMiniSeedWaveforms(dataDir, stationNames, filePattern)
%LOADMINISEEDWAVEFORMS Load station MiniSEED files as GISMO waveform objects.
%
% w = gismo_ext.loadMiniSeedWaveforms(dataDir, stationNames, filePattern)
%
% filePattern should contain one %s placeholder for station name, e.g.
% 'FL.%s..EHZ.D.2018.290'.

for k = 1:numel(stationNames)
    station_name = stationNames{k};
    filename = fullfile(dataDir, sprintf(filePattern, station_name));

    if ~exist(filename, 'file')
        error('MiniSEED file not found: %s', filename);
    end

    fprintf('  %s\n', filename);
    w(k) = waveform(filename, 'miniseed'); %#ok<AGROW>
end
end
