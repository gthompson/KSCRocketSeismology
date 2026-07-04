function g = gravityAtAltitude(altitude_m, cfg)
%GRAVITYATALTITUDE Gravity as a function of altitude above spherical Earth.

g = cfg.GravityMps2 .* cfg.EarthRadiusM.^2 ./ (cfg.EarthRadiusM + altitude_m).^2;
end
