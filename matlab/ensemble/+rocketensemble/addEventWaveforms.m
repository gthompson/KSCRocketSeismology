function catalogobj = addEventWaveforms(catalogobj, ds, cfg)
%ADDEVENTWAVEFORMS Add event-scale waveform windows to each catalog event.

ctag = ChannelTag({cfg.EventChannelTag});
catalogobj = catalogobj.addwaveforms( ...
    ds, ctag, cfg.EventPretriggerSeconds, cfg.EventPosttriggerSeconds);
end
