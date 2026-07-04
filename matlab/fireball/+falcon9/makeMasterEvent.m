function masterEvent = makeMasterEvent(infrasoundEvent, varargin)
%MAKEMASTEREVENT Build a representative/master infrasound event.
%
% masterEvent = falcon9.makeMasterEvent(infrasoundEvent)
% masterEvent = falcon9.makeMasterEvent(..., 'MaxMeanSecsDiff', 0.01)
%
% The master event is formed by averaging pairwise time-delay matrices
% (secsDiff) over events whose meanSecsDiff is close to zero. In the original
% Falcon 9 workflow these events were interpreted as relatively clean,
% single-arrival windows suitable for defining array timing delays.
%
% Required event fields:
%   FirstArrivalTime, LastArrivalTime, meanSecsDiff, secsDiff
%
% Output fields:
%   FirstArrivalTime, LastArrivalTime, eventIndexes, nEvents,
%   secsDiff, stdSecsDiff, fractionalStdSecsDiff, maxMeanSecsDiff

p = inputParser;
p.FunctionName = 'falcon9.makeMasterEvent';
addRequired(p, 'infrasoundEvent', @(x) isstruct(x) && ~isempty(x));
addParameter(p, 'MaxMeanSecsDiff', 0.01, @(x) isnumeric(x) && isscalar(x) && x >= 0);
addParameter(p, 'Verbose', true, @(x) islogical(x) || isnumeric(x));
parse(p, infrasoundEvent, varargin{:});

maxMeanSecsDiff = p.Results.MaxMeanSecsDiff;
verbose = logical(p.Results.Verbose);

requiredFields = {'FirstArrivalTime', 'LastArrivalTime', 'meanSecsDiff', 'secsDiff'};
for k = 1:numel(requiredFields)
    if ~isfield(infrasoundEvent, requiredFields{k})
        error('falcon9:makeMasterEvent:MissingField', ...
            'infrasoundEvent is missing required field "%s".', requiredFields{k});
    end
end

meanSecsDiff = [infrasoundEvent.meanSecsDiff];
eventIndexes = find(abs(meanSecsDiff) < maxMeanSecsDiff);
if isempty(eventIndexes)
    error('falcon9:makeMasterEvent:NoUsableEvents', ...
        'No events satisfy abs(meanSecsDiff) < %.4g s.', maxMeanSecsDiff);
end

firstMatrix = infrasoundEvent(eventIndexes(1)).secsDiff;
[nRows, nCols] = size(firstMatrix);
allSecsDiff = nan(nRows, nCols, numel(eventIndexes));

for i = 1:numel(eventIndexes)
    eventNumber = eventIndexes(i);
    thisMatrix = infrasoundEvent(eventNumber).secsDiff;
    if ~isequal(size(thisMatrix), [nRows, nCols])
        error('falcon9:makeMasterEvent:SizeMismatch', ...
            'secsDiff matrix size differs for event %d.', eventNumber);
    end
    allSecsDiff(:, :, i) = thisMatrix;
end

masterEvent = struct();
masterEvent.FirstArrivalTime = infrasoundEvent(1).FirstArrivalTime;
masterEvent.LastArrivalTime = infrasoundEvent(1).LastArrivalTime;
masterEvent.eventIndexes = eventIndexes;
masterEvent.nEvents = numel(eventIndexes);
masterEvent.maxMeanSecsDiff = maxMeanSecsDiff;
masterEvent.secsDiff = mean(allSecsDiff, 3, 'omitnan');
masterEvent.stdSecsDiff = std(allSecsDiff, 0, 3, 'omitnan');
masterEvent.fractionalStdSecsDiff = masterEvent.stdSecsDiff ./ masterEvent.secsDiff;
masterEvent.fractionalStdSecsDiff(~isfinite(masterEvent.fractionalStdSecsDiff)) = NaN;

if verbose
    fprintf('Constructed master infrasound event from %d/%d events.\n', ...
        masterEvent.nEvents, numel(infrasoundEvent));
    fprintf('Selection criterion: abs(meanSecsDiff) < %.4g s.\n', maxMeanSecsDiff);
    disp('Event indexes used:');
    disp(eventIndexes);
    disp('Mean secsDiff:');
    disp(masterEvent.secsDiff);
    disp('Std secsDiff:');
    disp(masterEvent.stdSecsDiff);
end
end
