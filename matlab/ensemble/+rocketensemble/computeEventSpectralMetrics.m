function metrics = computeEventSpectralMetrics(w, cfg)
%COMPUTEEVENTSPECTRALMETRICS Compute spectrogram peak/mean frequency tracks.

metrics = struct();

if ~isempty(cfg.InfrasoundIndices)
    [Ti, Fi, Yi, meanfi, peakfi] = spectrogram( ...
        w(cfg.InfrasoundIndices), ...
        'spectralobject', cfg.InfrasoundSpectralObject, ...
        'plot_metrics', 0);
    metrics.infrasound.T = Ti;
    metrics.infrasound.F = Fi;
    metrics.infrasound.Y = Yi;
    metrics.infrasound.meanFrequency = meanfi;
    metrics.infrasound.peakFrequency = peakfi;
end

if ~isempty(cfg.SeismicIndices)
    [Ts, Fs, Ys, meanfs, peakfs] = spectrogram( ...
        w(cfg.SeismicIndices), ...
        'spectralobject', cfg.SeismicSpectralObject, ...
        'plot_metrics', 0);
    metrics.seismic.T = Ts;
    metrics.seismic.F = Fs;
    metrics.seismic.Y = Ys;
    metrics.seismic.meanFrequency = meanfs;
    metrics.seismic.peakFrequency = peakfs;
end
end
