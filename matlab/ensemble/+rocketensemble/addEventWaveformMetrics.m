function catalogobj = addEventWaveformMetrics(catalogobj, cfg)
%ADDEVENTWAVEFORMMETRICS Add waveform metrics to each event waveform set.

for eventnum = 1:catalogobj.numberOfEvents
    w = [catalogobj.waveforms{eventnum}];
    try
        catalogobj.waveforms{eventnum} = addmetrics(w, cfg.EventMetricMaxTimeDiffSeconds);
    catch
        catalogobj.waveforms{eventnum} = addmetrics(w);
    end
end
end
