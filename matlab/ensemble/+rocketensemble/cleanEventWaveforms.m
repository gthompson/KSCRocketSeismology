function wclean = cleanEventWaveforms(w)
%CLEANEVENTWAVEFORMS Fill gaps and detrend waveforms for plotting/metrics.

try
    wclean = clean(w);
    return
catch
end

wclean = w;
try
    wclean = fillgaps(wclean, 'interp');
catch
end

try
    wclean = detrend(wclean);
catch
end
end
