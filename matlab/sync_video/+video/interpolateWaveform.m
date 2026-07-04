function w2 = interpolateWaveform(w, factor)
%INTERPOLATEWAVEFORM Upsample GISMO waveform objects by an integer factor.
%
% w2 = falcon9.interpolateWaveform(w, factor)

arguments
    w
    factor (1,1) double {mustBePositive} = 1
end

SECONDS_PER_DAY = 86400;
w2 = w;
for c = 1:numel(w)
    x = get(w(c), 'data');
    fs = get(w(c), 'freq');
    t = get(w(c), 'timevector');
    if factor == 1
        continue
    end
    t2 = t(1) + (1/SECONDS_PER_DAY) * (0:1/(fs*factor):(numel(x)-1)/fs);
    x2 = interp1(t, x, t2, 'linear', 'extrap');
    w2(c) = set(w2(c), 'data', x2(:));
    w2(c) = set(w2(c), 'freq', fs*factor);
end
end
