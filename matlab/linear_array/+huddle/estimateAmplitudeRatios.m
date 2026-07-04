function amp = estimateAmplitudeRatios(xcorr_result, cfg)
%ESTIMATEAMPLITUDERATIOS Estimate mean amplitude ratios and calibration factors.

aratio = xcorr_result.amplitude_ratio;
nchan = size(aratio, 2);

idx = cfg.AmplitudeRatioIndexRange;
idx = idx(idx >= 1 & idx <= size(aratio, 1));

if isempty(idx)
    warning('AmplitudeRatioIndexRange did not overlap available windows. Using all windows.');
    idx = 1:size(aratio, 1);
end

mean_ratio = zeros(nchan, nchan);
for i = 1:nchan
    for j = 1:nchan
        mean_ratio(i, j) = mean(aratio(idx, i, j), 'omitnan');
    end
end

cal_coeff = nan(nchan, nchan);
for ref = 1:nchan
    for c = 1:nchan
        cal_coeff(ref, c) = mean([mean_ratio(c, ref), 1 ./ mean_ratio(ref, c)], 'omitnan');
    end
end

ref_index = cfg.ReferenceStationIndex;
final_cal_coeff = cal_coeff(ref_index, :);

amp.amplitude_ratio = aratio;
amp.mean_ratio = mean_ratio;
amp.calibration_coefficients = cal_coeff;
amp.final_calibration_coefficients = final_cal_coeff;
amp.reference_station_index = ref_index;
amp.station_names = xcorr_result.station_names;
amp.average_indices = idx;
end
