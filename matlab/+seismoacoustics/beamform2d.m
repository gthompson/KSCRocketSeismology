function [bestBackAz, bestSpeed, distanceDiff, speedMatrix, diagnostics] = beamform2d(easting, northing, meanSecsDiff, varargin)
%BEAMFORM2D Estimate source back azimuth and apparent speed from array lags.
%
%   [bestBackAz, bestSpeed, distanceDiff, speedMatrix] = falcon9.beamform2d(easting, northing, meanSecsDiff)
%   [...] = falcon9.beamform2d(..., 'FixedBackAz', backAz)
%   [...] = falcon9.beamform2d(..., 'FixedSpeed', speed)
%   [...] = falcon9.beamform2d(..., 'MakeFigure', true)
%
%   Plane-wave geometry is assumed. easting and northing are station
%   coordinates in meters. meanSecsDiff is an N-by-N lag matrix in seconds.

    parser = inputParser;
    parser.addParameter('FixedBackAz', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x)));
    parser.addParameter('FixedSpeed', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x) && x > 0));
    parser.addParameter('AzimuthStep', 0.1, @(x) isnumeric(x) && isscalar(x) && x > 0);
    parser.addParameter('MakeFigure', false, @(x) islogical(x) || isnumeric(x));
    parser.parse(varargin{:});
    opts = parser.Results;

    easting = easting(:);
    northing = northing(:);
    nStations = numel(easting);

    if numel(northing) ~= nStations
        error('falcon9:beamform2d:CoordinateLengthMismatch', ...
              'easting and northing must have the same number of elements.');
    end
    if ~isequal(size(meanSecsDiff), [nStations nStations])
        error('falcon9:beamform2d:LagSizeMismatch', ...
              'meanSecsDiff must be %d-by-%d.', nStations, nStations);
    end
    if ~isempty(opts.FixedBackAz) && ~isempty(opts.FixedSpeed)
        warning('falcon9:beamform2d:OverConstrained', ...
                'Both FixedBackAz and FixedSpeed were supplied. FixedSpeed will be used; FixedBackAz ignored.');
        opts.FixedBackAz = [];
    end

    if ~isempty(opts.FixedBackAz)
        backAz = opts.FixedBackAz - 1.0 : opts.AzimuthStep : opts.FixedBackAz + 1.0;
    else
        backAz = opts.AzimuthStep : opts.AzimuthStep : 360;
    end

    eastingDiff = easting - easting.';
    northingDiff = northing - northing.';
    offDiagonal = ~eye(nStations);

    meanSpeed = NaN(size(backAz));
    stdSpeed = NaN(size(backAz));

    for iAz = 1:numel(backAz)
        unitVector = [-sin(deg2rad(backAz(iAz))), -cos(deg2rad(backAz(iAz)))];
        thisDistanceDiff = eastingDiff .* unitVector(1) + northingDiff .* unitVector(2);
        thisSpeedMatrix = thisDistanceDiff ./ meanSecsDiff;
        speeds = thisSpeedMatrix(offDiagonal);
        speeds = speeds(isfinite(speeds));
        meanSpeed(iAz) = mean(speeds, 'omitnan');
        stdSpeed(iAz) = std(speeds, 'omitnan');
    end

    fractionalError = abs(stdSpeed ./ meanSpeed);
    fractionalError(meanSpeed <= 0) = Inf;

    if ~isempty(opts.FixedSpeed)
        score = abs(meanSpeed - opts.FixedSpeed);
        score(meanSpeed <= 0) = Inf;
    else
        score = fractionalError;
    end

    [~, bestIndex] = min(score);
    bestBackAz = backAz(bestIndex);
    bestSpeed = meanSpeed(bestIndex);

    bestUnitVector = [-sin(deg2rad(bestBackAz)), -cos(deg2rad(bestBackAz))];
    distanceDiff = eastingDiff .* bestUnitVector(1) + northingDiff .* bestUnitVector(2);
    speedMatrix = distanceDiff ./ meanSecsDiff;

    diagnostics = struct();
    diagnostics.backAz = backAz;
    diagnostics.meanSpeed = meanSpeed;
    diagnostics.stdSpeed = stdSpeed;
    diagnostics.fractionalError = fractionalError;
    diagnostics.score = score;

    fprintf('Source back azimuth %.1f degrees; apparent speed %.1f m/s.\n', bestBackAz, bestSpeed);

    if opts.MakeFigure
        figure;
        subplot(2,1,1);
        plot(backAz, meanSpeed);
        xlabel('Back azimuth (degrees)');
        ylabel('Apparent speed (m/s)');
        subplot(2,1,2);
        semilogy(backAz, fractionalError);
        xlabel('Back azimuth (degrees)');
        ylabel('Fractional speed scatter');
    end
end
