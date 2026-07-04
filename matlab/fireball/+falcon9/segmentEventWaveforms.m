function wevent = segmentEventWaveforms(w, infrasoundEvent, pretrigger, posttrigger, arrivalTimeCorrection)
%SEGMENTEVENTWAVEFORMS Extract event windows from continuous waveform data.
%
%   wevent = falcon9.segmentEventWaveforms(w, infrasoundEvent, pretrigger, posttrigger)
%   wevent = falcon9.segmentEventWaveforms(w, infrasoundEvent, pretrigger, posttrigger, arrivalTimeCorrection)
%
%   Inputs:
%       w                     Continuous waveform vector/array, typically GISMO waveform objects.
%       infrasoundEvent        Struct array with field FirstArrivalTime, in MATLAB datenum days.
%       pretrigger             Seconds before FirstArrivalTime to include.
%       posttrigger            Seconds after FirstArrivalTime to include.
%       arrivalTimeCorrection  Optional seconds to subtract from arrival time. Default: 0.
%
%   Output:
%       wevent                 Cell array of detrended waveform windows.

    if nargin < 5 || isempty(arrivalTimeCorrection)
        arrivalTimeCorrection = 0.0;
    end

    validateattributes(pretrigger, {'numeric'}, {'scalar','nonnegative'}, mfilename, 'pretrigger', 3);
    validateattributes(posttrigger, {'numeric'}, {'scalar','nonnegative'}, mfilename, 'posttrigger', 4);
    validateattributes(arrivalTimeCorrection, {'numeric'}, {'scalar'}, mfilename, 'arrivalTimeCorrection', 5);

    requiredField = 'FirstArrivalTime';
    if ~isstruct(infrasoundEvent) || ~isfield(infrasoundEvent, requiredField)
        error('falcon9:segmentEventWaveforms:MissingField', ...
              'infrasoundEvent must be a struct array with field %s.', requiredField);
    end

    numEvents = numel(infrasoundEvent);
    wevent = cell(numEvents, 1);

    fprintf('Segmenting %d event waveform(s)...\n', numEvents);
    for eventNumber = 1:numEvents
        fprintf('- segmenting infrasound event %d of %d\n', eventNumber, numEvents);

        centerTime = infrasoundEvent(eventNumber).FirstArrivalTime - arrivalTimeCorrection/86400;
        time1 = centerTime - pretrigger/86400;
        time2 = centerTime + posttrigger/86400;

        wevent{eventNumber} = detrend(extract(w, 'time', time1, time2));
    end
end
