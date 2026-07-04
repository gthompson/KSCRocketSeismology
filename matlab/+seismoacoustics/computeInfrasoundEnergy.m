function energyJ = computeInfrasoundEnergy(dataInPascals, samplingFrequency, distanceMeters, varargin)
%COMPUTEINFRASOUNDENERGY Estimate range-corrected acoustic energy.
%
%   energyJ = falcon9.computeInfrasoundEnergy(dataInPascals,
%   samplingFrequency, distanceMeters) estimates acoustic energy from a
%   pressure waveform using hemispherical spreading:
%
%       E = 2*pi*r^2 / (rho*c) * integral(p(t)^2 dt)
%
%   where p is acoustic pressure in Pa, r is source-receiver distance in m,
%   rho is air density, and c is sound speed.
%
%   Name-value options
%   ------------------
%   'AirDensity' : kg/m^3, default 1.225
%   'SoundSpeed' : m/s, default 343
%   'GeometryFactor' : scalar, default 2*pi
%       Use 2*pi for hemispherical spreading near the ground, or 4*pi for
%       spherical spreading.
%   'RemoveMean' : logical, default true
%       Remove pressure offset before integration.
%
%   The input may be a vector or matrix. For matrices, samples are assumed
%   to run down rows and each column is treated as one channel.

p = inputParser;
p.FunctionName = 'falcon9.computeInfrasoundEnergy';
addParameter(p, 'AirDensity', 1.225, @(x) validateattributes(x, {'numeric'}, {'scalar','positive'}));
addParameter(p, 'SoundSpeed', 343, @(x) validateattributes(x, {'numeric'}, {'scalar','positive'}));
addParameter(p, 'GeometryFactor', 2*pi, @(x) validateattributes(x, {'numeric'}, {'scalar','positive'}));
addParameter(p, 'RemoveMean', true, @(x) islogical(x) || isnumeric(x));
parse(p, varargin{:});
opt = p.Results;

validateattributes(dataInPascals, {'numeric'}, {'nonempty','real'});
validateattributes(samplingFrequency, {'numeric'}, {'scalar','positive'});
validateattributes(distanceMeters, {'numeric'}, {'scalar','positive'});

pressure = dataInPascals;
if isvector(pressure)
    pressure = pressure(:);
end

if opt.RemoveMean
    pressure = pressure - mean(pressure, 1, 'omitnan');
end

pressureIntegral = sum(pressure.^2, 1, 'omitnan') ./ samplingFrequency; % Pa^2 s
energyJ = opt.GeometryFactor .* distanceMeters.^2 .* pressureIntegral ./ (opt.AirDensity .* opt.SoundSpeed);
end
