function arrivalobj = addArrivalMetrics(arrivalobj, cfg)
%ADDARRIVALMETRICS Add waveform metrics to Arrival objects.

arrivalobj = arrivalobj.addmetrics(cfg.ArrivalMetricMaxTimeDiffSeconds);
end
