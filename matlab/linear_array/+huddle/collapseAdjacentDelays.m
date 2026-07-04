function tracks = collapseAdjacentDelays(xcorr_result)
%COLLAPSEADJACENTDELAYS Convert adjacent-pair lags into cumulative tracks.

best_lag = xcorr_result.best_lag_seconds;
best_cor = xcorr_result.best_correlation;

nwin = size(best_lag, 1);
nchan = size(best_lag, 2);

relative_delay_seconds = zeros(nwin, nchan);
relative_correlation = ones(nwin, nchan);

for iwin = 1:nwin
    for ichan = 2:nchan
        relative_delay_seconds(iwin, ichan) = ...
            relative_delay_seconds(iwin, ichan-1) + best_lag(iwin, ichan, ichan-1);
        relative_correlation(iwin, ichan) = best_cor(iwin, ichan, ichan-1);
    end
end

tracks.times = xcorr_result.times;
tracks.relative_delay_seconds = relative_delay_seconds;
tracks.relative_correlation = relative_correlation;
tracks.station_names = xcorr_result.station_names;
end
