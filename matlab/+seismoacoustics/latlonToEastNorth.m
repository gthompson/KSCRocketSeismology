function [east_m, north_m] = latlonToEastNorth(originLat_deg, originLon_deg, lat_deg, lon_deg, varargin)
%LATLONTOEASTNORTH Convert latitude/longitude to local east/north offsets.
%
%   [EAST_M, NORTH_M] = falcon9.latlonToEastNorth(ORIGINLAT, ORIGINLON, LAT, LON)
%   converts LAT/LON coordinates in decimal degrees to local Cartesian offsets
%   in metres relative to ORIGINLAT/ORIGINLON.
%
%   Inputs
%   ------
%   ORIGINLAT, ORIGINLON : scalar decimal degrees
%       Origin of the local coordinate system.
%   LAT, LON : numeric arrays, decimal degrees
%       Coordinates to convert. LAT and LON must have the same size.
%
%   Outputs
%   -------
%   EAST_M, NORTH_M : numeric arrays, metres
%       Local east and north offsets from the origin. Output size matches LAT/LON.
%
%   Notes
%   -----
%   This implementation uses a local WGS84 tangent-plane approximation evaluated
%   at the origin latitude. It is appropriate for the small aperture of the
%   Falcon 9 / Astronaut Beach House station geometry and avoids requiring the
%   MATLAB Mapping Toolbox.
%
%   Example
%   -------
%   [east_m, north_m] = falcon9.latlonToEastNorth(28.5621, -80.5772, ...
%                                                 stationLat, stationLon);
%
%   See also latlon2eastingsNorthings

    %#ok<*NASGU> % varargin retained for future compatibility/name-value options.

    narginchk(4, inf);

    validateattributes(originLat_deg, {'numeric'}, {'scalar','real','finite','>=',-90,'<=',90}, mfilename, 'originLat_deg', 1);
    validateattributes(originLon_deg, {'numeric'}, {'scalar','real','finite','>=',-180,'<=',180}, mfilename, 'originLon_deg', 2);
    validateattributes(lat_deg, {'numeric'}, {'real','finite'}, mfilename, 'lat_deg', 3);
    validateattributes(lon_deg, {'numeric'}, {'real','finite'}, mfilename, 'lon_deg', 4);

    if ~isequal(size(lat_deg), size(lon_deg))
        error('falcon9:latlonToEastNorth:SizeMismatch', ...
              'LAT and LON must have the same size.');
    end
    if any(lat_deg(:) < -90 | lat_deg(:) > 90)
        error('falcon9:latlonToEastNorth:InvalidLatitude', ...
              'LAT values must be between -90 and 90 degrees.');
    end
    if any(lon_deg(:) < -180 | lon_deg(:) > 180)
        error('falcon9:latlonToEastNorth:InvalidLongitude', ...
              'LON values must be between -180 and 180 degrees.');
    end

    % WGS84 ellipsoid constants.
    a_m = 6378137.0;                 % semi-major axis, metres
    f = 1 / 298.257223563;           % flattening
    e2 = f * (2 - f);                % first eccentricity squared

    lat0_rad = deg2rad_local(originLat_deg);
    dlat_rad = deg2rad_local(lat_deg - originLat_deg);
    dlon_rad = deg2rad_local(wrapTo180_local(lon_deg - originLon_deg));

    sinLat0 = sin(lat0_rad);
    denom = sqrt(1 - e2 * sinLat0.^2);

    % Meridional and prime-vertical radii of curvature at the origin.
    M_m = a_m * (1 - e2) / denom.^3;
    N_m = a_m / denom;

    north_m = M_m .* dlat_rad;
    east_m  = N_m .* cos(lat0_rad) .* dlon_rad;
end

function rad = deg2rad_local(deg)
    rad = deg .* (pi / 180);
end

function lon_deg = wrapTo180_local(lon_deg)
%WRAPTO180_LOCAL Wrap degree offsets to [-180, 180].
    lon_deg = mod(lon_deg + 180, 360) - 180;
end
