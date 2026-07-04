function writeEventAudio(w, cfg, dstr)
%WRITEEVENTAUDIO Write infrasound and seismic WAV files for one event.

try
    idx = cfg.SoundInfrasoundIndex;
    if idx <= numel(w)
        waveform2sound(w(idx), 30, fullfile(cfg.AudioDir, sprintf('%s_infrasound.wav', dstr)));
    end
catch ME
    warning('Infrasound sound file failed: %s', ME.message);
end

try
    idx = cfg.SoundSeismicIndex;
    if idx <= numel(w)
        waveform2sound(w(idx), 30, fullfile(cfg.AudioDir, sprintf('%s_seismic.wav', dstr)));
    end
catch ME
    warning('Seismic sound file failed: %s', ME.message);
end
end
