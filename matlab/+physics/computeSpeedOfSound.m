function c = computeSpeedOfSound(temperatureC, relativeHumidity)
%COMPUTESPEEDOFSOUND Estimate speed of sound in humid air.
%
%   c = falcon9.computeSpeedOfSound(temperatureC, relativeHumidity)
%
%   Uses the simple empirical approximation:
%       c = 331.3 + 0.606*T_C + 1.26*RH/100
%
%   where T_C is temperature in degrees Celsius and RH is relative humidity
%   in percent. The result c is in m/s.

    if nargin < 2 || isempty(relativeHumidity)
        relativeHumidity = 0;
    end

    validateattributes(temperatureC, {'numeric'}, {}, mfilename, 'temperatureC', 1);
    validateattributes(relativeHumidity, {'numeric'}, {}, mfilename, 'relativeHumidity', 2);

    c = 331.3 + 0.606 .* temperatureC + 1.26 .* relativeHumidity ./ 100;
end
