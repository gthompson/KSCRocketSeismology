function [winfra, wseismic] = extractRepresentativeWaveforms(catalogobj, cfg)
%EXTRACTREPRESENTATIVEWAVEFORMS One infrasound and one seismic waveform per launch/day.

winfra = [];
wseismic = [];

for eventnum = 1:catalogobj.numberOfEvents
    try
        w = [catalogobj.waveforms{eventnum}];
        channels = get(w, 'channel');

        index_infra = find(ismember(channels, cfg.RepresentativeInfrasoundChannel), 1, 'first');
        index_seis = find(ismember(channels, cfg.RepresentativeSeismicChannel), 1, 'first');

        if isempty(index_infra) || isempty(index_seis)
            continue
        end

        if isempty(winfra)
            winfra = w(index_infra);
            wseismic = w(index_seis);
        else
            daysdiff = abs(get(winfra(end), 'start') - get(w(index_infra), 'start'));
            if daysdiff > cfg.MinimumDaysBetweenRepresentativeEvents
                winfra = [winfra w(index_infra)]; %#ok<AGROW>
                wseismic = [wseismic w(index_seis)]; %#ok<AGROW>
            end
        end
    catch ME
        warning('Could not extract representative waveform for event %d: %s', eventnum, ME.message);
    end
end
end
