function c = speedOfSoundProfile(altitude_m, cfg)
%SPEEDOFSOUNDPROFILE Simple altitude-dependent speed of sound model.
%
% This retains the legacy approximation:
% c = max(c0 - lapse * altitude, cmin)

c = max(cfg.SeaLevelSoundSpeedMps ...
    - cfg.SoundSpeedLapseMpsPerM .* altitude_m, ...
    cfg.MinimumSoundSpeedMps);
end
