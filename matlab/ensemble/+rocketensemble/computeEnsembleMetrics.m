function event_metrics = computeEnsembleMetrics(catalogobj, cfg)
%COMPUTEENSEMBLEMETRICS Extract scalar event-level metrics from catalog.

nevents = catalogobj.numberOfEvents;

event_metrics = table();
event_metrics.EventNumber = (1:nevents).';
event_metrics.StartTimeDatenum = nan(nevents, 1);
event_metrics.StartTime = NaT(nevents, 1);
event_metrics.NumWaveforms = nan(nevents, 1);
event_metrics.NumArrivals = nan(nevents, 1);
event_metrics.MaxInfrasoundAbsAmplitude = nan(nevents, 1);
event_metrics.MaxSeismicAbsAmplitude = nan(nevents, 1);
event_metrics.MeanInfrasoundPeakFrequencyHz = nan(nevents, 1);
event_metrics.MeanSeismicPeakFrequencyHz = nan(nevents, 1);

for eventnum = 1:nevents
    try
        w = [catalogobj.waveforms{eventnum}];
        arrivals_this_event = catalogobj.arrivals{eventnum};

        event_metrics.StartTimeDatenum(eventnum) = min(get(w, 'start'));
        event_metrics.StartTime(eventnum) = datetime(event_metrics.StartTimeDatenum(eventnum), 'ConvertFrom', 'datenum');
        event_metrics.NumWaveforms(eventnum) = numel(w);
        try
            event_metrics.NumArrivals(eventnum) = numel(arrivals_this_event);
        catch
            event_metrics.NumArrivals(eventnum) = NaN;
        end

        wclean = rocketensemble.cleanEventWaveforms(w);

        event_metrics.MaxInfrasoundAbsAmplitude(eventnum) = maxAbsAmplitude(wclean, cfg.InfrasoundIndices);
        event_metrics.MaxSeismicAbsAmplitude(eventnum) = maxAbsAmplitude(wclean, cfg.SeismicIndices);

        try
            spectral_metrics = rocketensemble.computeEventSpectralMetrics(wclean, cfg);
            event_metrics.MeanInfrasoundPeakFrequencyHz(eventnum) = meanPeakFreq(spectral_metrics, 'infrasound');
            event_metrics.MeanSeismicPeakFrequencyHz(eventnum) = meanPeakFreq(spectral_metrics, 'seismic');
        catch
        end

    catch ME
        warning('Metrics failed for event %d: %s', eventnum, ME.message);
    end
end
end


function value = maxAbsAmplitude(w, indices)
value = NaN;
if isempty(indices)
    return
end
vals = [];
for k = indices
    if k <= numel(w)
        x = double(get(w(k), 'data'));
        vals(end+1) = max(abs(x)); %#ok<AGROW>
    end
end
if ~isempty(vals)
    value = max(vals);
end
end


function value = meanPeakFreq(metrics, fieldname)
value = NaN;
if ~isfield(metrics, fieldname) || ~isfield(metrics.(fieldname), 'peakFrequency')
    return
end

pf = metrics.(fieldname).peakFrequency;
vals = [];

if iscell(pf)
    for k = 1:numel(pf)
        vals = [vals; pf{k}(:)]; %#ok<AGROW>
    end
else
    vals = pf(:);
end

value = mean(vals, 'omitnan');
end
