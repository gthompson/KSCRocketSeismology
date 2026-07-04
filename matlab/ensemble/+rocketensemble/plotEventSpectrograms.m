function plotEventSpectrograms(w, cfg, dstr, title_string)
%PLOTEVENTSPECTROGRAMS Plot infrasound and seismic spectrograms for one event.

if ~isempty(cfg.InfrasoundIndices)
    try
        figure('Color', 'w');
        spectrogram(w(cfg.InfrasoundIndices), ...
            'spectralobject', cfg.InfrasoundSpectralObject, ...
            'plot_metrics', 0);
        title(sprintf('Infrasound spectrogram\n%s', title_string), 'Interpreter', 'none');
        saveas(gcf, fullfile(cfg.FigureDir, sprintf('%s_infrasound_spectrogram.png', dstr)));
        close(gcf);
    catch ME
        warning('Infrasound spectrogram failed: %s', ME.message);
    end
end

if ~isempty(cfg.SeismicIndices)
    try
        figure('Color', 'w');
        spectrogram(w(cfg.SeismicIndices), ...
            'spectralobject', cfg.SeismicSpectralObject, ...
            'plot_metrics', 0);
        title(sprintf('Seismic spectrogram\n%s', title_string), 'Interpreter', 'none');
        saveas(gcf, fullfile(cfg.FigureDir, sprintf('%s_seismic_spectrogram.png', dstr)));
        close(gcf);
    catch ME
        warning('Seismic spectrogram failed: %s', ME.message);
    end
end
end
