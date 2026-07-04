function plotEventEnvelope(w, cfg, output_file, title_string)
%PLOTEVENTENVELOPE Plot smoothed Hilbert envelopes for one event.

figure('Color', 'w');

ax1 = subplot(2,1,1);
try
    plot(smooth(hilbert(rocketensemble.cleanEventWaveforms(w(cfg.InfrasoundIndices))), 1000), ...
        'axeshandle', ax1);
catch
    data = collectEnvelopeData(w(cfg.InfrasoundIndices));
    plot(ax1, data);
end
title(ax1, 'Infrasound envelope');

ax2 = subplot(2,1,2);
try
    plot(smooth(hilbert(rocketensemble.cleanEventWaveforms(w(cfg.SeismicIndices))), 1000), ...
        'axeshandle', ax2);
catch
    data = collectEnvelopeData(w(cfg.SeismicIndices));
    plot(ax2, data);
end
title(ax2, 'Seismic envelope');

sgtitle(sprintf('Envelope\n%s', title_string), 'Interpreter', 'none');

saveas(gcf, output_file);
close(gcf);
end


function data = collectEnvelopeData(w)
data = [];
for k = 1:numel(w)
    x = double(get(w(k), 'data'));
    x = x(:) - mean(x(:), 'omitnan');
    env = abs(hilbert(x));
    env = movmean(env, min(1000, numel(env)));
    data(:, k) = env; %#ok<AGROW>
end
end
