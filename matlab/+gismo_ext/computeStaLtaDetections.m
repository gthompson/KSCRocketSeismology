function [detobj, sta, lta, sta_to_lta] = computeStaLtaDetections(w, varargin)
%COMPUTESTALTADETECTIONS Generic GISMO STA/LTA wrapper.

p = inputParser;
p.addParameter('StaSeconds', 0.7, @isnumeric);
p.addParameter('LtaSeconds', 7.0, @isnumeric);
p.addParameter('TriggerOn', 3.0, @isnumeric);
p.addParameter('TriggerOff', 1.5, @isnumeric);
p.addParameter('MinimumEventDurationSeconds', 60.0, @isnumeric);
p.addParameter('NetworkCode', '', @(x) ischar(x) || isstring(x));
p.parse(varargin{:});
opt = p.Results;

event_detection_params = [ ...
    opt.StaSeconds, opt.LtaSeconds, opt.TriggerOn, opt.TriggerOff, ...
    opt.MinimumEventDurationSeconds];

[detobj, sta, lta, sta_to_lta] = Detection.sta_lta( ...
    w, 'edp', event_detection_params, 'lta_mode', 'frozen');

if strlength(string(opt.NetworkCode)) > 0
    try
        detobj = detobj.addnetwork(char(opt.NetworkCode));
    catch
    end
end
end
