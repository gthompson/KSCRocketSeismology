function tempC = fahrenheit2celsius(tempF)
%FAHRENHEIT2CELSIUS Convert temperature from degrees Fahrenheit to Celsius.
%
%   tempC = falcon9.fahrenheit2celsius(tempF)
%
%   Input may be a scalar, vector, or array. NaNs are preserved.

    validateattributes(tempF, {'numeric'}, {}, mfilename, 'tempF', 1);
    tempC = (tempF - 32) .* (5/9);
end
