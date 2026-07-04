function makeEventDiagnostics(catalogobj, cfg)
%MAKEEVENTDIAGNOSTICS Create per-event waveform, spectrogram, audio diagnostics.

nevents = catalogobj.numberOfEvents;
last_event = min(nevents, cfg.FirstEventToPlot + cfg.MaxEventsToPlot - 1);

for eventnum = cfg.FirstEventToPlot:last_event
    fprintf('  event %d/%d\n', eventnum, nevents);

    w = [catalogobj.waveforms{eventnum}];
    arrivals_this_event = catalogobj.arrivals{eventnum};
    [dstr, title_string] = rocketensemble.eventStartString(w, eventnum);

    if cfg.MakeRawWaveformPlots
        try
            figure('Color', 'w');
            plot_panels(w(:), 'alignWaveforms', 1, 'arrivals', arrivals_this_event);
            title(sprintf('Raw waveform plot\n%s', title_string), 'Interpreter', 'none');
            saveas(gcf, fullfile(cfg.FigureDir, sprintf('%s_raw_waveform.png', dstr)));
            close(gcf);
        catch ME
            warning('Raw waveform plot failed for event %d: %s', eventnum, ME.message);
        end
    end

    wclean = rocketensemble.cleanEventWaveforms(w);

    if cfg.MakeSpectrogramPlots
        rocketensemble.plotEventSpectrograms(wclean, cfg, dstr, title_string);
    end

    if cfg.MakeSoundFiles
        rocketensemble.writeEventAudio(wclean, cfg, dstr);
    end

    if cfg.MakeTrajectoryPlots || cfg.MakeEnvelopePlots
        try
            spectral_metrics = rocketensemble.computeEventSpectralMetrics(wclean, cfg);
            if cfg.MakeTrajectoryPlots
                rocketensemble.plotTrajectoryProxy(spectral_metrics, cfg, ...
                    fullfile(cfg.FigureDir, sprintf('%s_trajectory_proxy.png', dstr)), ...
                    title_string);
            end
        catch ME
            warning('Spectral trajectory proxy failed for event %d: %s', eventnum, ME.message);
        end

        if cfg.MakeEnvelopePlots
            try
                rocketensemble.plotEventEnvelope(wclean, cfg, ...
                    fullfile(cfg.FigureDir, sprintf('%s_envelope.png', dstr)), ...
                    title_string);
            catch ME
                warning('Envelope plot failed for event %d: %s', eventnum, ME.message);
            end
        end
    end
end
end
