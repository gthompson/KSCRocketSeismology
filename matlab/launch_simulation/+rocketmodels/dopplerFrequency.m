function f_obs = dopplerFrequency(source_frequency_hz, sound_speed_mps, radial_velocity_mps)
%DOPPLERFREQUENCY Observed frequency for a receding moving source.
%
% radial_velocity_mps is positive when the source moves away from observer.
%
% f_obs = f_source * c / (c + v_radial)

f_obs = source_frequency_hz .* sound_speed_mps ./ ...
    (sound_speed_mps + radial_velocity_mps);
end
