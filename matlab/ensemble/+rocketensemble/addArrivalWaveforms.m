function arrivalobj = addArrivalWaveforms(arrivalobj, ds, cfg)
%ADDARRIVALWAVEFORMS Add short waveform snippets to Arrival objects.

arrivalobj = arrivalobj.addwaveforms( ...
    ds, cfg.ArrivalPretriggerSeconds, cfg.ArrivalPosttriggerSeconds);
end
