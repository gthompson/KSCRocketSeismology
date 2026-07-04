function w = loadVideoSyncWaveforms(cfg)
%LOADVIDEOSYNCWAVEFORMS Load waveforms for synchronized video rendering.
%
% w = falcon9.loadVideoSyncWaveforms(cfg)
%
% Supported cfg.WaveformMode values:
%   'mat'      Load variable w from cfg.WaveformMatFile.
%   'antelope' Load waveforms via GISMO/Antelope datasource.

arguments
    cfg struct
end

mode = lower(string(getfieldwithdefault(cfg, 'WaveformMode', 'mat')));

switch mode
    case "mat"
        if ~isfield(cfg, 'WaveformMatFile') || ~isfile(cfg.WaveformMatFile)
            error('falcon9:MissingWaveformMatFile', ...
                'cfg.WaveformMatFile does not exist: %s', cfg.WaveformMatFile);
        end
        S = load(cfg.WaveformMatFile);
        if ~isfield(S, 'w')
            error('falcon9:MissingWaveformVariable', ...
                'MAT file must contain a waveform variable named w.');
        end
        w = S.w;

    case "antelope"
        requireFunction('datasource');
        requireFunction('waveform');
        requireFunction('ChannelTag');
        ds = datasource('antelope', cfg.AntelopeDbPath);
        chantag = ChannelTag(cfg.ChannelTag);
        t0 = cfg.StartTime;
        t1 = cfg.EndTime + cfg.ZoomWindowSeconds/86400;
        w = waveform(ds, chantag, t0, t1);
        if isempty(w)
            error('falcon9:NoWaveforms', 'No waveforms returned for requested window.');
        end
        if exist('clean', 'file') == 2
            w = clean(w);
        end

    otherwise
        error('falcon9:BadWaveformMode', 'Unsupported cfg.WaveformMode: %s', mode);
end
end

function requireFunction(fname)
if exist(fname, 'file') ~= 2 && exist(fname, 'class') ~= 8
    error('falcon9:MissingDependency', ...
        'Required function/class not found on MATLAB path: %s', fname);
end
end

function value = getfieldwithdefault(s, name, defaultValue)
if isfield(s, name)
    value = s.(name);
else
    value = defaultValue;
end
end
