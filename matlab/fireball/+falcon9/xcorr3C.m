function infrasoundEvent = xcorr3C(wevent, infrasoundEvent, makeFigures, figureOutDirectory, pretrigger)
%XCORR3C Cross-correlate a 3-channel infrasound event waveform set.
%
%   infrasoundEvent = falcon9.xcorr3C(wevent, infrasoundEvent, makeFigures, figureOutDirectory, pretrigger)
%
%   Inputs:
%       wevent              Cell array; each cell contains a 3-element waveform vector.
%       infrasoundEvent     Struct array with field FirstArrivalTime.
%       makeFigures         Logical flag. Default: false.
%       figureOutDirectory  Output directory for diagnostic PNGs. Default: pwd.
%       pretrigger          Seconds included before FirstArrivalTime in each wevent window.
%
%   Output fields added to infrasoundEvent:
%       maxCorr, secsDiff, meanCorr, stdCorr, meanSecsDiff, stdSecsDiff

    if nargin < 3 || isempty(makeFigures)
        makeFigures = false;
    end
    if nargin < 4 || isempty(figureOutDirectory)
        figureOutDirectory = pwd;
    end
    if nargin < 5 || isempty(pretrigger)
        pretrigger = 0;
    end

    if makeFigures && ~exist(figureOutDirectory, 'dir')
        mkdir(figureOutDirectory);
    end

    if ~isstruct(infrasoundEvent) || ~isfield(infrasoundEvent, 'FirstArrivalTime')
        error('falcon9:xcorr3C:MissingField', ...
              'infrasoundEvent must be a struct array with field FirstArrivalTime.');
    end

    precorrtime = 0.1;   % seconds before picked arrival for template
    postcorrtime = 0.2;  % seconds after picked arrival for template
    offDiagonal = ~eye(3);

    numEvents = numel(infrasoundEvent);
    fprintf('Cross-correlating %d event(s)...\n', numEvents);

    for eventNumber = 1:numEvents
        fprintf('- processing event %d of %d\n', eventNumber, numEvents);
        haystacks = wevent{eventNumber};

        if numel(haystacks) ~= 3
            error('falcon9:xcorr3C:ExpectedThreeChannels', ...
                  'Event %d contains %d waveform(s); expected 3.', eventNumber, numel(haystacks));
        end

        infrasoundEvent(eventNumber).maxCorr = eye(3);
        infrasoundEvent(eventNumber).secsDiff = zeros(3);

        for chanNumber = 1:3
            t1 = infrasoundEvent(eventNumber).FirstArrivalTime - precorrtime/86400;
            t2 = infrasoundEvent(eventNumber).FirstArrivalTime + postcorrtime/86400;
            needle = extract(haystacks(chanNumber), 'time', t1, t2);
            needleData = detrend(get(needle, 'data'));

            for haystackNum = 1:3
                fprintf('  - looking for channel %d template in channel %d\n', chanNumber, haystackNum);
                haystack = haystacks(haystackNum);
                haystackData = detrend(get(haystack, 'data'));

                [acor, lag] = xcorr(needleData, haystackData);
                scale = sqrt(sum(abs(needleData).^2) * sum(abs(haystackData).^2));
                if scale > 0
                    acor = acor ./ scale;
                else
                    acor(:) = NaN;
                end

                [maxCorrelation, idx] = max(abs(acor));
                infrasoundEvent(eventNumber).maxCorr(chanNumber, haystackNum) = maxCorrelation;
                infrasoundEvent(eventNumber).secsDiff(chanNumber, haystackNum) = ...
                    lag(idx) / get(haystack, 'freq') + pretrigger - precorrtime;

                if makeFigures
                    fig = figure('Visible', 'off');
                    subplot(3,1,1); plot(haystack, 'axeshandle', gca); title('Haystack');
                    subplot(3,1,2); plot(needle, 'axeshandle', gca); title('Template');
                    subplot(3,1,3); plot(lag, acor); title('Normalized cross-correlation');
                    xlabel('Lag samples'); ylabel('Correlation');

                    outfile = fullfile(figureOutDirectory, ...
                        sprintf('xcorr_infrasoundEvent%03d_%d_%d.png', eventNumber, chanNumber, haystackNum));
                    print(fig, '-dpng', outfile);
                    close(fig);
                end
            end
        end

        corrValues = infrasoundEvent(eventNumber).maxCorr(offDiagonal);
        lagValues = infrasoundEvent(eventNumber).secsDiff(offDiagonal);
        infrasoundEvent(eventNumber).meanCorr = mean(corrValues, 'omitnan');
        infrasoundEvent(eventNumber).stdCorr = std(corrValues, 'omitnan');
        infrasoundEvent(eventNumber).meanSecsDiff = mean(lagValues, 'omitnan');
        infrasoundEvent(eventNumber).stdSecsDiff = std(lagValues, 'omitnan');
    end
end
