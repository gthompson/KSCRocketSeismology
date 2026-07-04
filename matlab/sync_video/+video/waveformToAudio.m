function wAudio = waveformToAudio(w, outfile, opts)
%WAVEFORMTOAUDIO Convert waveform data to an audible WAV file.
%
% wAudio = falcon9.waveformToAudio(w, outfile)
%
% The original video-sync scripts used FM modulation so low-frequency
% infrasound/seismic signals could be heard. This implementation keeps that
% behavior, but makes the carrier/modulation explicit and optional.

arguments
    w
    outfile (1,:) char
    opts.InterpolationFactor (1,1) double {mustBePositive} = 16
    opts.Mode (1,:) char {mustBeMember(opts.Mode, {'fm','scaled'})} = 'fm'
    opts.CarrierFraction (1,1) double {mustBePositive} = 0.4
    opts.FrequencyDeviationFraction (1,1) double {mustBePositive} = 0.25
end

wAudio = falcon9.interpolateWaveform(w, opts.InterpolationFactor);
for c = 1:numel(wAudio)
    fs = get(wAudio(c), 'freq');
    x = get(wAudio(c), 'data');
    x = x(:);
    x = x - mean(x, 'omitnan');
    maxAbs = max(abs(x));
    if maxAbs > 0
        x = x ./ maxAbs;
    end
    switch lower(opts.Mode)
        case 'fm'
            if exist('fmmod', 'file') == 2
                fc = fs * opts.CarrierFraction;
                freqdev = fc * opts.FrequencyDeviationFraction;
                y = fmmod(x, fc, fs, freqdev);
            else
                warning('falcon9:MissingFmmod', 'fmmod not found; writing scaled audio instead.');
                y = x;
            end
        case 'scaled'
            y = x;
    end
    y = 0.95 * y ./ max(max(abs(y)), eps);
    outDir = fileparts(outfile);
    if ~isempty(outDir) && ~exist(outDir, 'dir')
        mkdir(outDir);
    end
    audiowrite(outfile, y, fs);
end
end
