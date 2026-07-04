function cfg = kscNetworkConfig()
%KSCNETWORKCONFIG Configuration for KSC PASSCAL/Antelope dbbuild metadata.

cfg.Network.Code = '1R';
cfg.Network.Name = 'RocketSeis';
cfg.OutputDir = fullfile(pwd, 'dbbuild_files');

% Reference source used for optional distance/azimuth calculations.
cfg.Source.Name = 'SLC41';
cfg.Source.Latitude = dms2degrees_local([28, 35, 0.57]);
cfg.Source.Longitude = -dms2degrees_local([80, 34, 58.48]);

% Site-wide metadata.
cfg.MagneticDeclinationDeg = -6.81;
cfg.DefaultGain = 32;
cfg.DefaultSampleRate = 200;
cfg.DefaultElevationM = 0;
cfg.DefaultBurialDepthM = 0;

% Optional legacy fixed sites to include at the top of the inventory table.
cfg.IncludeLegacyInventoryRows = true;
end


function degrees = dms2degrees_local(dms)
degrees = abs(dms(1)) + dms(2)/60 + dms(3)/3600;
if dms(1) < 0
    degrees = -degrees;
end
end
