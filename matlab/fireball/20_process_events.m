%% 20_PROCESS_EVENTS
% Process waveform/event data for the Falcon 9 explosion analysis.
%
% Algorithm:
%   1. Load the Level-1 cache created by 10_import_data.m.
%   2. Compute receiver-source distances and wind-corrected acoustic travel times.
%   3. Retrieve X1 arrivals from the Antelope database and group them into events.
%   4. High-pass filter the waveform data.
%   5. Segment event windows around each impulsive infrasound arrival.
%   6. Cross-correlate the first three infrasound channels for each event.
%   7. Build a master_event lag matrix from usable events.
%   8. Estimate apparent sound speed and source backazimuth by beamforming.
%   9. Time-shift waveforms, resegment events, and pick event amplitudes.
%  10. Compute pressure change, reduced pressure, and relative sensor calibrations.
%  11. Save all processed variables back to the cache MAT file.

clearvars
close all
clc

cfg = falcon9.config();
cache_file = cfg.CacheFile;

if ~exist(cache_file, 'file')
    error('20_process_events:MissingCache', ...
        'Cache file not found. Run 10_import_data.m first: %s', cache_file);
end

load(cache_file);

%% Predict acoustic travel times and attach receiver metadata

fprintf('\nPredicting travel times based on receiver coordinates and wind vector...\n');
fprintf('____________________________________________________________\n');
fprintf('Sound speed:    %.1f m/s\n', speed_of_sound_mps);
fprintf('Wind speed:     %.1f m/s\n', wind_speed_mps);
fprintf('Wind direction: %.1f degrees, toward\n', wind_direction_deg);
fprintf('------\t--------\t-----------\t----------\n');
fprintf('Chan\tDistance\tBackAzimuth\tTravelTime\n');
fprintf('------\t--------\t-----------\t----------\n');

nchan = numel(lat);
arclen_m = nan(1, nchan);
backaz_deg = nan(1, nchan);
predicted_traveltime_s = nan(1, nchan);

for c = 1:nchan
    [arclen_deg, backaz_deg(c)] = distance(lat(c), lon(c), source.lat, source.lon, 'degrees');
    arclen_m(c) = deg2km(arclen_deg) * 1000;

    propagation_direction_deg = mod(180 + backaz_deg(c), 360);
    effective_speed_mps = speed_of_sound_mps + ...
        wind_speed_mps * cosd(propagation_direction_deg - wind_direction_deg);

    predicted_traveltime_s(c) = arclen_m(c) / effective_speed_mps;

    fprintf('%s\t%.1f m\t\t%.1f deg\t%.3f s\n', ...
        get(w(c), 'channel'), arclen_m(c), backaz_deg(c), predicted_traveltime_s(c));

    w(c) = addfield(w(c), 'lat', lat(c));
    w(c) = addfield(w(c), 'lon', lon(c));
    w(c) = addfield(w(c), 'distance', arclen_m(c));
    w(c) = addfield(w(c), 'backaz', backaz_deg(c));
end

fprintf('____________________________________________________________\n');

%% Compute local easting/northing relative to SLC-40

deg2m = deg2km(1) * 1000;
easting_m = nan(1, nchan);
northing_m = nan(1, nchan);

for c = 1:nchan
    easting_m(c) = distance(lat(c), lon(c), lat(c), source.lon) * deg2m;
    northing_m(c) = distance(lat(c), lon(c), source.lat, lon(c)) * deg2m;
end

%% Load and group arrivals

fprintf('Loading arrivals...\n');

if exist('db_path', 'var')
    arrivals = Arrival.retrieve('antelope', db_path);
elseif exist(cfg.DbPathFallback, 'dir')
    arrivals = Arrival.retrieve('antelope', cfg.DbPathFallback);
else
    arrivals = Arrival.retrieve('antelope', cfg.DbPathPrimary);
end

fprintf('Subsetting X1 arrivals...\n');
arrivals = arrivals.subset('iphase', 'X1');

fprintf('Associating arrivals into events...\n');
max_time_diff_s = 1;
infrasound_event = struct('FirstArrivalTime', {}, 'LastArrivalTime', {});
event_on = false;
event_number = 0;

for c = 2:numel(arrivals.daynumber)
    is_same_event = arrivals.daynumber(c-1) + max_time_diff_s/86400 > arrivals.daynumber(c);

    if is_same_event
        if ~event_on
            event_on = true;
            event_number = event_number + 1;
            infrasound_event(event_number).FirstArrivalTime = arrivals.daynumber(c-1); %#ok<SAGROW>
        end
        infrasound_event(event_number).LastArrivalTime = arrivals.daynumber(c); %#ok<SAGROW>
    else
        event_on = false;
    end
end

num_events = numel(infrasound_event);
fprintf('Grouped %d infrasound events.\n', num_events);

%% Filter, segment, and correlate events

fprintf('Filtering waveform data...\n');
wfilt = detrend(w);
hp_filter = filterobject('h', [10], 3);
wfilt = filtfilt(hp_filter, wfilt);

pretrigger_s = 1;
posttrigger_s = 1;
wevent = falcon9.segmentEventWaveforms(wfilt, infrasound_event, pretrigger_s, posttrigger_s);

fprintf('Cross-correlating infrasound events...\n');
infrasound_event = falcon9.xcorr3C(wevent, infrasound_event, false, cfg.FigureOutDir, pretrigger_s);

%% Beamform each event using the canonical package beamformer
%
% This replaces the older exploratory beamform2dfull(...) branch from
% spaceXplosion_make_figures.m. Keeping these per-event results in the
% processing stage lets 30_make_figures.m reproduce the backazimuth/speed
% diagnostic plots without reprocessing.

fprintf('Beamforming individual events...\n');
for event_number = 1:num_events
    infrasound_event(event_number).bestbackaz = NaN;
    infrasound_event(event_number).bestspeed = NaN;
    infrasound_event(event_number).distanceDiff = NaN(3, 3);
    infrasound_event(event_number).speedMatrix = NaN(3, 3);

    try
        [event_backaz_deg, event_speed_mps, event_distance_diff, event_speed_matrix] = ...
            falcon9.beamform2d(easting_m(1:3), northing_m(1:3), ...
                infrasound_event(event_number).secsDiff, 'MakeFigure', false);

        infrasound_event(event_number).bestbackaz = event_backaz_deg;
        infrasound_event(event_number).bestspeed = event_speed_mps;
        infrasound_event(event_number).distanceDiff = event_distance_diff;
        infrasound_event(event_number).speedMatrix = event_speed_matrix;
    catch ME
        warning('20_process_events:EventBeamformFailed', ...
            'Event %d beamforming failed: %s', event_number, ME.message);
    end
end


%% Construct master event from usable event statistics

fprintf('Constructing master event from individual event statistics...\n');
master_event.FirstArrivalTime = infrasound_event(1).FirstArrivalTime;
master_event.LastArrivalTime = infrasound_event(1).LastArrivalTime;

usable_event_idx = find(abs([infrasound_event.meanSecsDiff]) < 0.01);
fprintf('Found %d events usable for master-event timing.\n', numel(usable_event_idx));
disp(usable_event_idx);

master_event.secsDiff = zeros(3, 3);
master_event.stdSecsDiff = zeros(3, 3);

for row = 1:3
    for col = 1:3
        values = [];
        for event_number = usable_event_idx
            values = [values, infrasound_event(event_number).secsDiff(row, col)]; %#ok<AGROW>
        end
        if numel(values) > 1 && std(values) > 0
            keep = abs((values - mean(values)) / std(values)) < 1.0;
        else
            keep = true(size(values));
        end
        master_event.secsDiff(row, col) = mean(values(keep));
        master_event.stdSecsDiff(row, col) = std(values(keep));
    end
end

fprintf('Mean differential times:\n');
disp(master_event.secsDiff);
fprintf('Standard deviations:\n');
disp(master_event.stdSecsDiff);

%% Estimate apparent sound speed from differential travel times

fprintf('Estimating apparent sound speed from receiver spacing and differential times...\n');
pair_speed_mps = nan(3, 3);

for row = 1:3
    for col = 1:3
        if row ~= col
            distance_difference_m = get(w(row), 'distance') - get(w(col), 'distance');
            time_difference_s = master_event.secsDiff(row, col);
            pair_speed_mps(row, col) = distance_difference_m / time_difference_s;
            fprintf('row %d col %d: dR %.1f m, dt %.4f s, speed %.1f m/s\n', ...
                row, col, distance_difference_m, time_difference_s, pair_speed_mps(row, col));
        end
    end
end

mean_speed_mps = nanmean(abs(pair_speed_mps(:)));
std_speed_mps = nanstd(abs(pair_speed_mps(:)));
fprintf('Mean apparent sound speed %.1f +/- %.1f m/s\n', mean_speed_mps, std_speed_mps);

%% Beamform to estimate source backazimuth

fprintf('Beamforming to estimate source backazimuth...\n');
[best_backaz_deg, best_sound_speed_mps, distance_diff, speed_matrix] = ...
    falcon9.beamform2d(easting_m(1:3), northing_m(1:3), master_event.secsDiff, ...
        'FixedBackAz', 199.0, 'FixedSpeed', 348.6, 'MakeFigure', false);

disp(distance_diff);
disp(speed_matrix);

source_dist_m = get(w(2), 'distance');
[beam_source_lat, beam_source_lon] = reckon( ...
    lat(2), lon(2), km2deg(source_dist_m/1000), best_backaz_deg);

dist_from_slc40_m = deg2km(distance(beam_source_lat, beam_source_lon, source.lat, source.lon)) * 1000;
fprintf('Beamforming source estimate: lat %.4f lon %.4f; %.1f m from SLC-40\n', ...
    beam_source_lat, beam_source_lon, dist_from_slc40_m);

%% Time-shift waveforms and resegment events

[min_predicted_traveltime_s, reference_idx] = min(predicted_traveltime_s);
traveltime_s = nan(1, numel(w));

for c = 1:3
    traveltime_s(c) = min_predicted_traveltime_s + ...
        mean([master_event.secsDiff(c, reference_idx), -master_event.secsDiff(reference_idx, c)]);
end

traveltime_s(4) = min_predicted_traveltime_s + ...
    (get(w(4), 'distance') - get(w(reference_idx), 'distance')) / best_sound_speed_mps;
traveltime_s(5:6) = traveltime_s(4);

wshift = wfilt;
for c = 1:numel(wshift)
    old_start = get(w(c), 'start');
    new_start = old_start - traveltime_s(c) / 86400;
    fprintf('Moving channel %d start from %s to %s\n', ...
        c, datestr(old_start, 'HH:MM:SS.FFF'), datestr(new_start, 'HH:MM:SS.FFF'));
    wshift(c) = set(wshift(c), 'start', new_start);
end

arrival_time_correction_s = min_predicted_traveltime_s;

% Approximate event origin times by subtracting the common acoustic travel
% time correction from the first array arrival. These are mainly used for
% tables/plots; event alignment still uses picked arrival times.
for event_number = 1:num_events
    infrasound_event(event_number).originTime = ...
        infrasound_event(event_number).FirstArrivalTime - arrival_time_correction_s/86400;
end

preplot_s = 0.15;
postplot_s = 0.15;
weventshift = falcon9.segmentEventWaveforms( ...
    wshift, infrasound_event, preplot_s, postplot_s, arrival_time_correction_s);

%% Pick event amplitudes

fprintf('Picking peak-to-trough event amplitudes...\n');
for event_number = 1:num_events
    w_event = weventshift{event_number};

    fh = figure('Name', sprintf('Picked event %03d', event_number), 'Visible', 'off');
    plot_panels(w_event);
    axes_handles = get(fh, 'Children');
    set(fh, 'Position', [0 0 1600 1000]);

    infrasound_event(event_number).maxAmp = zeros(1, 6);
    infrasound_event(event_number).minAmp = zeros(1, 6);
    infrasound_event(event_number).maxTime = zeros(1, 6);
    infrasound_event(event_number).minTime = zeros(1, 6);

    for chan_num = 1:6
        y = get(w_event(chan_num), 'data');
        fs = get(w_event(chan_num), 'freq');
        trace_start = get(w_event(chan_num), 'start');

        num_samples = length(y);
        window_size = round(fs / 25);
        best_peak_to_trough = -Inf;
        max_secs = NaN;
        min_secs = NaN;
        final_sample = round(num_samples * 0.7) - window_size;

        for start_samp = 1:window_size:final_sample
            sample_idx = start_samp:(start_samp + window_size - 1);
            [max_y, max_idx] = max(y(sample_idx));
            [min_y, min_idx] = min(y(sample_idx));
            peak_to_trough = max_y - min_y;

            if peak_to_trough > best_peak_to_trough
                max_secs = (max_idx + sample_idx(1) - 1) / fs;
                min_secs = (min_idx + sample_idx(1) - 1) / fs;
                best_peak_to_trough = peak_to_trough;
                infrasound_event(event_number).maxTime(chan_num) = trace_start + max_secs/86400;
                infrasound_event(event_number).minTime(chan_num) = trace_start + min_secs/86400;
                infrasound_event(event_number).maxAmp(chan_num) = max_y;
                infrasound_event(event_number).minAmp(chan_num) = min_y;
            end
        end

        axis_num = 8 - chan_num;
        if axis_num <= numel(axes_handles)
            axes(axes_handles(axis_num)); %#ok<LAXES>
            hold on
            plot(max_secs, infrasound_event(event_number).maxAmp(chan_num), 'g*');
            plot(min_secs, infrasound_event(event_number).minAmp(chan_num), 'r*');
        end
    end

    print(fh, '-dpng', fullfile(cfg.FigureOutDir, sprintf('picked_event_%03d.png', event_number)));
    close(fh);
end

%% Compute relative sensor calibrations

fprintf('Computing relative calibrations of infrasound sensors...\n');
tolerance_s = 0.02;
component_pairs = [1 3; 1 2; 2 3];
rel_amp = nan(1, size(component_pairs, 1));

for pair_num = 1:size(component_pairs, 1)
    chan_num = component_pairs(pair_num, :);
    max_amp = nan(2, num_events);
    min_amp = nan(2, num_events);

    for event_number = 1:num_events
        ev = infrasound_event(event_number);
        if std(ev.maxTime) < tolerance_s/86400 && std(ev.minTime) < tolerance_s/86400
            for c = 1:2
                max_amp(c, event_number) = ev.maxAmp(chan_num(c));
                min_amp(c, event_number) = ev.minAmp(chan_num(c));
            end
        end
    end

    half_peak_to_trough = (max_amp - min_amp) / 2;
    ratio = half_peak_to_trough(1, :) ./ half_peak_to_trough(2, :);
    ratio_mean = nanmean(ratio);
    ratio_std = nanstd(ratio);
    keep = ratio > ratio_mean - ratio_std & ratio < ratio_mean + ratio_std;
    ratio_mean_clean = nanmean(ratio(keep));
    ratio_std_clean = nanstd(ratio(keep));
    distance_ratio = get(w(chan_num(2)), 'distance') / get(w(chan_num(1)), 'distance');
    rel_amp(pair_num) = ratio_mean_clean / distance_ratio;

    fprintf('Sensors %d/%d relative amplitude: %.4f +/- %.4f\n', ...
        chan_num(1), chan_num(2), ratio_mean_clean, ratio_std_clean);
    fprintf('Distance ratio: %.4f; distance-corrected relative amplitude: %.4f\n', ...
        distance_ratio, rel_amp(pair_num));
end

old_calib = get(w, 'calib');
new_calib = old_calib;
new_calib(1) = old_calib(1) / rel_amp(1);
new_calib(2) = old_calib(2) / rel_amp(3);
new_calib(3) = old_calib(3);

for chan_num = 1:3
    fprintf('Channel %d calib old = %.6g, new = %.6g\n', ...
        chan_num, old_calib(chan_num), new_calib(chan_num));
end

%% Compute pressure change and reduced pressure

fprintf('Computing pressure changes and reduced pressures...\n');
for event_number = 1:num_events
    for chan_num = 1:3
        ev = infrasound_event(event_number);
        pressure_change = ev.maxAmp(chan_num) - ev.minAmp(chan_num);
        distance_km = get(w(chan_num), 'distance') / 1000.0;
        infrasound_event(event_number).pchange(chan_num) = pressure_change;
        infrasound_event(event_number).preduced(chan_num) = (pressure_change / 2) * distance_km;
    end
end

%% Write event list

eventlist_file = fullfile(cfg.FigureOutDir, 'eventlist.csv');
fprintf('Writing event list: %s\n', eventlist_file);
fout = fopen(eventlist_file, 'w');
fprintf(fout, 'event_number,origin_time,pchange_mean,preduced_mean\n');

for event_number = 1:num_events
    ev = infrasound_event(event_number);
    if isfield(ev, 'originTime')
        origin_time_str = datestr(ev.originTime);
    else
        origin_time_str = '';
    end
    fprintf(fout, '%d,%s,%.3f,%.3f\n', ...
        event_number, origin_time_str, nanmean(ev.pchange), nanmean(ev.preduced));
end

fclose(fout);

% Compatibility alias for older plotting/result scripts that used camelCase.
infrasoundEvent = infrasound_event; %#ok<NASGU>

save(cache_file);
fprintf('20_process_events complete.\n');
