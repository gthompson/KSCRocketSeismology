function wfilt = butterworthFilter(w, filterType, corners, varargin)
%BUTTERWORTHFILTER Apply a Butterworth filter to GISMO waveform data.
%
%   wfilt = gismo_ext.butterworthFilter(w, filterType, corners) detrends and
%   zero-phase filters GISMO waveform object(s) using a GISMO filterobject.
%
%   This is a cleaned convenience wrapper around the legacy
%   butterworthFilter.m. It intentionally remains GISMO-dependent.
%
%   Inputs
%   ------
%   w : GISMO waveform object or waveform array
%   filterType : char/string
%       GISMO filter type, e.g. 'B', 'H', 'L', depending on local GISMO
%       conventions.
%   corners : numeric scalar/vector
%       Filter corner frequency/frequencies in Hz.
%
%   Name-value options
%   ------------------
%   'Poles' : default 2
%       Number of poles for filterobject.
%   'Detrend' : default true
%       Detrend before filtering.
%   'Verbose' : default false
%       Print a short status message.

p = inputParser;
p.FunctionName = 'gismo_ext.butterworthFilter';
addParameter(p, 'Poles', 2, @(x) validateattributes(x, {'numeric'}, {'scalar','integer','positive'}));
addParameter(p, 'Detrend', true, @(x) islogical(x) || isnumeric(x));
addParameter(p, 'Verbose', false, @(x) islogical(x) || isnumeric(x));
parse(p, varargin{:});
opt = p.Results;

if opt.Verbose
    fprintf('Filtering waveform data: type=%s, corners=%s Hz, poles=%d\n', ...
        char(filterType), mat2str(corners), opt.Poles);
end

if opt.Detrend
    wfilt = detrend(w);
else
    wfilt = w;
end

fobj = filterobject(char(filterType), corners, opt.Poles);
wfilt = filtfilt(fobj, wfilt);
end
