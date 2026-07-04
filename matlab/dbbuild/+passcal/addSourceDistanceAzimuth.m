function station = addSourceDistanceAzimuth(station, source_lat, source_lon)
%ADDSOURCEDISTANCEAZIMUTH Add source distance/azimuth using spherical formulas.
%
% Avoids requiring the Mapping Toolbox.

earth_radius_km = 6371.0;

lat1 = deg2rad(source_lat);
lon1 = deg2rad(source_lon);

for k = 1:numel(station)
    lat2 = deg2rad(station(k).lat);
    lon2 = deg2rad(station(k).lon);

    dlat = lat2 - lat1;
    dlon = lon2 - lon1;

    a = sin(dlat/2).^2 + cos(lat1).*cos(lat2).*sin(dlon/2).^2;
    c = 2 .* atan2(sqrt(a), sqrt(1-a));

    station(k).distanceKm = earth_radius_km .* c;

    y = sin(dlon) .* cos(lat2);
    x = cos(lat1).*sin(lat2) - sin(lat1).*cos(lat2).*cos(dlon);
    az = mod(rad2deg(atan2(y, x)), 360);
    station(k).azimuthDeg = az;
end
end
