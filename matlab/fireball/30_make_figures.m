%% 30_MAKE_FIGURES
% Generate manuscript/diagnostic figures from the processed Falcon 9 cache.
%
% This stage should only render figures/tables from variables created by
% 10_import_data.m and 20_process_events.m.  It intentionally does not
% retrieve arrivals, recompute catalogs, cross-correlate, or beamform events.
%
% Material migrated from the older exploratory script
% spaceXplosion_make_figures.m is split as follows:
%   - Arrival/catalog/correlation/beamforming logic belongs in 20_process_events.m.
%   - Raw waveform panels, time-window panels, array maps, and event-level
%     diagnostic plots belong here.
%
% Required processed variables, when available:
%   w or wf, wfilt, wshift, wevent, weventshift, infrasound_event/master_event,
%   easting_m/northing_m, wind metadata, and event amplitude/beamforming fields.

clearvars
close all
clc

cfg = falcon9.config();
cache_file = cfg.CacheFile;

if ~exist(cache_file, 'file')
    error('30_make_figures:MissingCache', ...
        'Cache file not found. Run 10_import_data.m and 20_process_events.m first: %s', cache_file);
end

if ~exist(cfg.FigureOutDir, 'dir')
    mkdir(cfg.FigureOutDir);
end

load(cache_file);

% Support both the refactored name and the older camelCase name.
if exist('infrasound_event', 'var')
    events = infrasound_event;
elseif exist('infrasoundEvent', 'var')
    events = infrasoundEvent;
else
    events = struct([]);
end

% Support both the refactored waveform name and the older exploratory name.
if exist('w', 'var')
    wraw = w;
elseif exist('wf', 'var')
    wraw = wf;
else
    wraw = [];
end

%% Raw waveform overview

if ~isempty(wraw) && exist('plot_panels', 'file') == 2
    fh = figure('Name', 'Raw waveforms');
    plot_panels(wraw);
    save_current_figure(fh, cfg.FigureOutDir, 'waveforms_raw.png');
end

%% Raw helicorder-style plots from the older figure script

if ~isempty(wraw) && exist('plot_helicorder', 'file') == 2
    if numel(wraw) >= 2
        fh = figure('Name', 'Helicorder channel 2');
        plot_helicorder(wraw(2), 'mpl', 1, 'scale', 30);
        set(gca, 'FontSize', 18);
        save_current_figure(fh, cfg.FigureOutDir, 'helicorder_channel_2.png');
    end

    if numel(wraw) >= 6
        fh = figure('Name', 'Helicorder channel 6');
        plot_helicorder(wraw(6), 'mpl', 1, 'scale', 20);
        set(gca, 'FontSize', 18);
        save_current_figure(fh, cfg.FigureOutDir, 'helicorder_channel_6.png');
    end
end

%% Key waveform time windows from the older exploratory figure script

if ~isempty(wraw) && exist('plot_panels', 'file') == 2
    snum = get_start_time_from_config_or_data(cfg, wraw);

    plot_waveform_window(wraw, snum + 310/86400, snum + 319.4/86400, ...
        cfg.FigureOutDir, 'waveforms_second_stage.png', ...
        'Second-stage explosion window');

    plot_waveform_window(wraw, snum + 315.8/86400, snum + 316.3/86400, ...
        cfg.FigureOutDir, 'waveforms_second_stage_zoom.png', ...
        'Second-stage explosion zoom');

    plot_waveform_window(wraw, snum + 310/86400, snum + 315.8/86400, ...
        cfg.FigureOutDir, 'waveforms_pre_second_stage.png', ...
        'Pre-second-stage interval');
end

%% Travel-time-corrected main sequence

if exist('wshift', 'var') && exist('plot_panels', 'file') == 2
    fh = figure('Name', 'Travel-time corrected waveforms');
    plot_panels(wshift);
    save_current_figure(fh, cfg.FigureOutDir, 'waveforms_traveltime_corrected.png');

    snum = get_start_time_from_config_or_data(cfg, wshift);
    plot_waveform_window(wshift, datenum(2016,9,1,13,7,0), datenum(2016,9,1,13,8,0), ...
        cfg.FigureOutDir, 'waveforms_main_sequence_corrected.png', ...
        'Main sequence after acoustic travel-time correction');
end

%% Array map

if exist('easting_m', 'var') && exist('northing_m', 'var')
    wind_speed_for_plot = [];
    wind_direction_for_plot = [];

    if exist('wind_speed_mps', 'var')
        wind_speed_for_plot = wind_speed_mps;
    elseif exist('wind_speed', 'var')
        wind_speed_for_plot = wind_speed;
    end

    if exist('wind_direction_deg', 'var')
        wind_direction_for_plot = wind_direction_deg;
    elseif exist('wind_direction', 'var')
        wind_direction_for_plot = wind_direction;
    end

    
    %fh = falcon9.plotArrayMap(easting_m, northing_m, ...
    %    'Waveforms', wraw, ...
    %    'WindSpeed', wind_speed_for_plot, ...
    %    'WindDirection', wind_direction_for_plot, ...
    %    'SourceLabel', 'SLC-40');

    fh = rocketseis.plotArrayMap(easting_m, northing_m, ...
        'Waveforms', wraw, ...
        'SourceEastM', easting_m, ...
        'SourceNorthM', northing_m, ...
        'SourceLabels', {'SLC-40'}, ...
        'WindSpeed', wind_speed_for_plot, ...
        'WindDirection', wind_direction_for_plot);
    save_current_figure(fh, cfg.FigureOutDir, 'arraymap.png');
end

%% Event waveform panels

if exist('wevent', 'var')
    falcon9.plotEvents(wevent, 'waveforms_infrasoundEvent', cfg.FigureOutDir);
end

if exist('weventshift', 'var')
    falcon9.plotEvents(weventshift, 'waveforms_infrasoundEvent_shifted', cfg.FigureOutDir);
end

%% Beamforming diagnostic figure for the master event

if exist('easting_m', 'var') && exist('northing_m', 'var') && exist('master_event', 'var')
    [best_backaz_deg, best_sound_speed_mps, distance_diff, speed_matrix, diagnostics] = ... %#ok<ASGLU>
        falcon9.beamform2d(easting_m(1:3), northing_m(1:3), master_event.secsDiff, ...
            'FixedBackAz', 199.0, 'FixedSpeed', 348.6, 'MakeFigure', true);
    save_current_figure(gcf, cfg.FigureOutDir, 'beamforming_master_event.png');
end

%% Event quality-control diagnostics

if ~isempty(events)
    t = event_time_vector(events);

    if has_event_field(events, 'snr')
        snr_vector = nan(size(events));
        for event_number = 1:numel(events)
            snr_values = events(event_number).snr;
            snr_vector(event_number) = min(snr_values(1:min(3, numel(snr_values))));
        end
        good_idx = snr_vector > 4;

        fh = figure('Name', 'Event SNR quality control');
        plot(t, snr_vector, '*');
        hold on
        plot(t(good_idx), snr_vector(good_idx), '*');
        datetick('x');
        xlabel('Time');
        ylabel(sprintf('Signal to noise\n(worst of first 3 channels)'));
        save_current_figure(fh, cfg.FigureOutDir, 'event_snr_qc.png');
    else
        good_idx = true(size(t));
    end

    if has_event_field(events, 'bestbackaz')
        backaz = [events.bestbackaz];

        fh = figure('Name', 'Backazimuth histogram');
        histogram(backaz, 0:0.1:359.9);
        hold on
        histogram(backaz(good_idx), 0:0.1:359.9);
        xlim([195 205]);
        set(gca, 'XTick', 195:205);
        xlabel('Backazimuth (degrees)');
        ylabel('# events');
        save_current_figure(fh, cfg.FigureOutDir, 'backazimuth_histogram.png');

        fh = figure('Name', 'Backazimuth versus time');
        plot(t(good_idx), backaz(good_idx), '*');
        datetick('x');
        ylim([195 205]);
        ylabel('Backazimuth (degrees)');
        xlabel('Time on 1-Sep-2016 UTC');
        save_current_figure(fh, cfg.FigureOutDir, 'backazimuth_vs_time.png');
    end

    if has_event_field(events, 'speedMatrix')
        bestspeed = nan(1, numel(events));
        bestspeederror = nan(1, numel(events));
        for event_number = 1:numel(events)
            speed_matrix_this = events(event_number).speedMatrix;
            if numel(speed_matrix_this) >= 8
                speed_values = speed_matrix_this([2 3 4 6 7 8]);
                bestspeed(event_number) = mean(speed_values, 'omitnan');
                bestspeederror(event_number) = std(speed_values, 'omitnan');
            end
        end

        fh = figure('Name', 'Apparent speed versus time');
        plot(t, bestspeed, '*');
        hold on
        plot(t(good_idx), bestspeed(good_idx), '*');
        datetick('x');
        ylabel('Infrasound speed across array (m/s)');
        xlabel('Time on 1-Sep-2016 UTC');
        save_current_figure(fh, cfg.FigureOutDir, 'apparent_speed_vs_time.png');

        goodspeed = bestspeed(good_idx);
        goodspeed = goodspeed(goodspeed > 330 & goodspeed < 370);
        if ~isempty(goodspeed)
            fh = figure('Name', 'Apparent speed histogram');
            histogram(goodspeed);
            xlabel('Speed (m/s)');
            ylabel('# events');
            save_current_figure(fh, cfg.FigureOutDir, 'apparent_speed_histogram.png');
        end

        if has_event_field(events, 'bestbackaz')
            backaz = [events.bestbackaz];
            fh = figure('Name', 'Speed versus backazimuth');
            plot(backaz(good_idx), bestspeed(good_idx), '*');
            set(gca, 'XLim', [195 205], 'YLim', [330 370]);
            xlabel('Backazimuth (degrees)');
            ylabel('Speed (m/s)');
            save_current_figure(fh, cfg.FigureOutDir, 'speed_vs_backazimuth.png');
        end
    end

    if has_event_field(events, 'meanCorr') && has_event_field(events, 'stdCorr')
        fh = figure('Name', 'Mean correlation versus time');
        errorbar(t, [events.meanCorr], [events.stdCorr], '*');
        datetick('x');
        xlabel('Time on 1-Sep-2016 UTC');
        ylabel('Mean cross-correlation');
        save_current_figure(fh, cfg.FigureOutDir, 'mean_correlation_vs_time.png');
    end

    if has_event_field(events, 'seismicEnergy') && has_event_field(events, 'infrasoundEnergy')
        fh = figure('Name', 'Seismic versus infrasound energy');
        loglog([events.seismicEnergy], [events.infrasoundEnergy], '*');
        hold on
        se = logspace(2, 7);
        loglog(se, se);
        loglog(se, se*10);
        loglog(se, se*100);
        xlabel('Seismic energy (J)');
        ylabel('Infrasound energy (J)');
        save_current_figure(fh, cfg.FigureOutDir, 'seismic_vs_infrasound_energy.png');

        vasr = [events.infrasoundEnergy] ./ [events.seismicEnergy];
        fh = figure('Name', 'VASR versus time');
        semilogy(t, vasr, '*');
        datetick('x');
        xlabel('Time on 1-Sep-2016 UTC');
        ylabel('VASR');
        save_current_figure(fh, cfg.FigureOutDir, 'vasr_vs_time.png');
    end

    if has_event_field(events, 'preduced')
        redp = nan(1, numel(events));
        for event_number = 1:numel(events)
            redp(event_number) = mean(events(event_number).preduced, 'omitnan');
        end
        fh = figure('Name', 'Reduced pressure versus time');
        semilogy(t, redp, '*');
        hold on
        semilogy(t(good_idx), redp(good_idx), '*');
        datetick('x');
        ylabel('Reduced pressure (Pa km)');
        xlabel('Time on 1-Sep-2016 UTC');
        save_current_figure(fh, cfg.FigureOutDir, 'reduced_pressure_vs_time.png');
    elseif has_event_field(events, 'reducedPressure')
        redp = nan(1, numel(events));
        for event_number = 1:numel(events)
            redp(event_number) = mean(events(event_number).reducedPressure, 'omitnan');
        end
        fh = figure('Name', 'Reduced pressure versus time');
        semilogy(t, redp, '*');
        hold on
        semilogy(t(good_idx), redp(good_idx), '*');
        datetick('x');
        ylabel('Reduced pressure');
        xlabel('Time on 1-Sep-2016 UTC');
        save_current_figure(fh, cfg.FigureOutDir, 'reduced_pressure_vs_time.png');
    end
end

%% Seismic velocity model figure retained from exploratory script

fh = figure('Name', 'Seismic velocity model');
plot([400 400 1500 1500], [0 -3 -4 -32], 'LineWidth', 3);
hold on
plot([1500 2000 2000 4000], [-32 -33 -87 -90], ':', 'LineWidth', 3);
plot([120 170 220 280 340 450], [0 -4 -6 -11 -20 -21], 'LineWidth', 3);
xlabel('Velocity (m/s)');
ylabel('Depth (m)');
legend('P', 'P - uncertain', 'S', 'Location', 'best');
save_current_figure(fh, cfg.FigureOutDir, 'seismic_velocity_model.png');

fprintf('30_make_figures complete. Figures written to %s\n', cfg.FigureOutDir);

%% Local helper functions

function save_current_figure(fh, outdir, filename)
    if ~exist(outdir, 'dir')
        mkdir(outdir);
    end
    set(fh, 'Color', 'w');
    print(fh, '-dpng', fullfile(outdir, filename));
    close(fh);
end

function plot_waveform_window(waveforms, start_time, end_time, outdir, filename, figure_title)
    if exist('extract', 'file') ~= 2 || exist('plot_panels', 'file') ~= 2
        return
    end

    try
        wwin = extract(waveforms, 'time', start_time, end_time);
        fh = figure('Name', figure_title);
        plot_panels(wwin);
        title(figure_title);
        save_current_figure(fh, outdir, filename);
    catch ME
        warning('30_make_figures:WindowPlotFailed', ...
            'Could not create %s: %s', filename, ME.message);
    end
end

function tf = has_event_field(events, field_name)
    tf = isstruct(events) && ~isempty(events) && isfield(events, field_name);
end

function t = event_time_vector(events)
    if isfield(events, 'FirstArrivalTime')
        t = [events.FirstArrivalTime];
    elseif isfield(events, 'originTime')
        t = [events.originTime];
    else
        t = 1:numel(events);
    end
end

function start_time = get_start_time_from_config_or_data(cfg, waveforms)
    if isfield(cfg, 'StartTime')
        start_time = cfg.StartTime;
    else
        try
            start_time = get(waveforms(1), 'start');
        catch
            start_time = datenum(2016, 9, 1, 13, 0, 0);
        end
    end
end
