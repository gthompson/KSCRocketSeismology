function results = syncVideoWithWaveforms(cfg, w)
%SYNCVIDEOWITHWAVEFORMS Render rocket video synchronized with waveforms.
%
% results = falcon9.syncVideoWithWaveforms(cfg, w)
%
% This generic renderer supports a single video or several simultaneous
% video sources. It overlays time cursors on full-window waveform panels and
% draws zoomed waveform panels that scroll with the video time.
%
% Required inputs:
%   cfg.Videos(:).VideoFile  Local video files readable by VideoReader.
%   cfg.Videos(:).StartTime  UTC MATLAB datenum of each first frame.
%   cfg.StartTime/cfg.EndTime Rendering window in UTC MATLAB datenums.
%   w                        GISMO waveform array or compatible object array.
%
% Notes:
%   - Video files are not distributed with the paper archive.
%   - GISMO waveform functions are used through get/extract when available.

arguments
    cfg struct
    w
end

ensureOutputDirectories(cfg);

renderFrames = getfielddefault(cfg, 'RenderFrames', true);
writeMovie = getfielddefault(cfg, 'WriteMovie', false);
writeAudio = getfielddefault(cfg, 'WriteAudio', false) && isfield(cfg, 'Audio') && cfg.Audio.Enabled;
frameStep = getfielddefault(cfg, 'FrameStep', 1);
maxFrames = getfielddefault(cfg, 'MaxFrames', Inf);
verbose = getfielddefault(cfg, 'Verbose', true);

videos = falcon9.openVideoSources(cfg.Videos);
layout = makeLayout(cfg, numel(videos));
[fig, ax] = createFigureAndAxes(cfg, layout);

% Draw static/full-window waveform panels.
mainHandles = drawMainWaveformPanels(ax, layout, cfg, w);

% Determine render times. For talks, it is usually best to render at a fixed
% output FPS rather than using frame timestamps from one video.
fps = cfg.FPS;
renderTimes = cfg.StartTime + (0:1/fps:(cfg.EndTime-cfg.StartTime)*86400) / 86400;
renderTimes = renderTimes(1:frameStep:end);
if isfinite(maxFrames)
    renderTimes = renderTimes(1:min(numel(renderTimes), maxFrames));
end

if ~renderFrames
    realtime = cfg.StartTime;
    drawOneFrame(fig, ax, layout, cfg, w, videos, realtime, mainHandles, 1, numel(renderTimes));
    results = struct('FrameCount', 0, 'FrameDir', cfg.FrameDir, 'MovieFile', cfg.MovieFile);
    return
end

for k = 1:numel(renderTimes)
    realtime = renderTimes(k);
    if verbose
        fprintf('Rendering frame %d of %d: %s\n', k, numel(renderTimes), datestr(realtime, 'yyyy-mm-dd HH:MM:SS.FFF'));
    end
    drawOneFrame(fig, ax, layout, cfg, w, videos, realtime, mainHandles, k, numel(renderTimes));
    frameFile = fullfile(cfg.FrameDir, sprintf('%06d.png', k));
    exportFrame(fig, frameFile);
end

if writeMovie
    falcon9.writeFrameMovie(cfg.FrameDir, cfg.MovieFile, 'FPS', fps, ...
        'Profile', cfg.MovieProfile, 'Quality', cfg.MovieQuality, 'Verbose', verbose);
end

if writeAudio
    for k = 1:numel(cfg.Audio.Tracks)
        tr = cfg.Audio.Tracks(k);
        falcon9.waveformToAudio(w(tr.WaveformIndex), tr.OutputFile, ...
            'InterpolationFactor', cfg.Audio.InterpolationFactor);
    end
end

results = struct();
results.FrameCount = numel(renderTimes);
results.FrameDir = cfg.FrameDir;
results.MovieFile = cfg.MovieFile;
results.AudioWritten = writeAudio;
end

function ensureOutputDirectories(cfg)
if ~exist(cfg.OutputDir, 'dir'), mkdir(cfg.OutputDir); end
if ~exist(cfg.FrameDir, 'dir'), mkdir(cfg.FrameDir); end
end

function layout = makeLayout(cfg, nVideos)
mode = lower(string(getfielddefault(cfg, 'VideoMode', 'single')));
if mode == "multi" || nVideos > 1
    layout.VideoRows = 2;
    layout.VideoCols = 2;
    layout.Mode = 'multi';
else
    layout.VideoRows = 1;
    layout.VideoCols = 1;
    layout.Mode = 'single';
end
layout.NVideos = nVideos;
end

function [fig, ax] = createFigureAndAxes(cfg, layout)
fig = figure('Units','pixels', 'Position',[10 10 cfg.Figure.Width cfg.Figure.Height], 'Color','w');
set(fig, 'Visible', 'on');
clf(fig);

sp = 0.025;
ax = struct();
if strcmp(layout.Mode, 'multi')
    videoW = 0.22; videoH = 0.25;
    x0 = [0.04 0.285 0.04 0.285];
    y0 = [0.70 0.70 0.42 0.42];
    for k = 1:4
        ax.Video(k) = axes('Parent', fig, 'Position', [x0(k) y0(k) videoW videoH]); %#ok<AGROW>
        axis(ax.Video(k), 'off');
    end
    ax.Main(1) = axes('Parent', fig, 'Position', [0.04 0.23 0.47 0.13]);
    ax.Main(2) = axes('Parent', fig, 'Position', [0.04 0.06 0.47 0.13]);
    zoomX = 0.56; zoomW = 0.40; zoomTop = 0.88; zoomH = 0.075; gap = 0.018;
else
    ax.Video(1) = axes('Parent', fig, 'Position', [0.04 0.54 0.48 0.40]);
    axis(ax.Video(1), 'off');
    ax.Main(1) = axes('Parent', fig, 'Position', [0.06 0.33 0.43 0.12]);
    ax.Main(2) = axes('Parent', fig, 'Position', [0.06 0.16 0.43 0.12]);
    zoomX = 0.56; zoomW = 0.40; zoomTop = 0.88; zoomH = 0.075; gap = 0.018;
end

nZoom = numel(getfielddefault(cfg, 'InfrasoundZoomIndices', [])) + 3 + 1;
for k = 1:nZoom
    y = zoomTop - (k-1)*(zoomH+gap);
    ax.Zoom(k) = axes('Parent', fig, 'Position', [zoomX y zoomW zoomH]); %#ok<AGROW>
end
ax.Time = axes('Parent', fig, 'Position', [0.04 0.94 0.25 0.04], 'Visible','off');
set(findall(fig, '-property', 'FontSize'), 'FontSize', cfg.FontSize);
end

function mainHandles = drawMainWaveformPanels(ax, ~, cfg, w)
mainHandles = struct();
for p = 1:numel(cfg.MainPanels)
    panel = cfg.MainPanels(p);
    axes(ax.Main(p)); %#ok<LAXES>
    [t, x] = waveformTimeData(w(panel.WaveformIndex));
    x = x .* panel.Scale;
    plot(ax.Main(p), t, x, 'LineWidth', 1.5);
    xlim(ax.Main(p), [cfg.StartTime cfg.EndTime]);
    if isfield(panel, 'YLim') && ~isempty(panel.YLim)
        ylim(ax.Main(p), panel.YLim);
    end
    datetick(ax.Main(p), 'x', 'HH:MM:SS', 'keeplimits');
    ylabel(ax.Main(p), panel.Units);
    title(ax.Main(p), panel.Name, 'Interpreter','none');
    grid(ax.Main(p), 'on');
    mainHandles(p).YLim = ylim(ax.Main(p)); %#ok<AGROW>
end
end

function drawOneFrame(fig, ax, layout, cfg, w, videos, realtime, mainHandles, k, kmax)
% Clear dynamic axes.
for p = 1:numel(ax.Video)
    cla(ax.Video(p)); axis(ax.Video(p), 'off');
end
for p = 1:numel(ax.Zoom)
    cla(ax.Zoom(p));
end
cla(ax.Time);

% Redraw main panels each frame to avoid handle cleanup complexity.
drawMainWaveformPanels(ax, layout, cfg, w);
for p = 1:numel(ax.Main)
    hold(ax.Main(p), 'on');
    line(ax.Main(p), [realtime realtime], mainHandles(p).YLim, 'Color','k', 'LineWidth', 2);
    for d = 1:numel(cfg.Overlay.DelaysSeconds)
        tdel = realtime + cfg.Overlay.DelaysSeconds(d)/86400;
        if tdel <= cfg.EndTime + cfg.ZoomWindowSeconds/86400
            line(ax.Main(p), [tdel tdel], mainHandles(p).YLim, 'Color', cfg.Overlay.LineStyles{d}, 'LineWidth', 2);
        end
    end
    hold(ax.Main(p), 'off');
end

% Video frames.
for v = 1:numel(videos)
    panel = min(max(videos(v).Panel,1), numel(ax.Video));
    frame = falcon9.getVideoFrameAtTime(videos(v), realtime);
    if ~isempty(frame)
        image(ax.Video(panel), frame);
        title(ax.Video(panel), videos(v).Name, 'Interpreter','none');
    else
        text(ax.Video(panel), 0.5, 0.5, 'No frame', 'HorizontalAlignment','center');
        title(ax.Video(panel), videos(v).Name, 'Interpreter','none');
    end
    axis(ax.Video(panel), 'off');
end

% Timestamp.
text(ax.Time, 0, 0.5, sprintf('%s UTC   frame %d/%d', datestr(realtime,'HH:MM:SS.FFF'), k, kmax), ...
    'FontSize', 24, 'FontWeight', 'bold');

% Zoom panels.
zoomStart = realtime;
zoomEnd = realtime + cfg.ZoomWindowSeconds/86400;
zoomIdx = 1;
infra = getfielddefault(cfg, 'InfrasoundZoomIndices', []);
for c = 1:numel(infra)
    plotZoomWaveform(ax.Zoom(zoomIdx), w(infra(c)), cfg, zoomStart, zoomEnd, sprintf('Infrasound %d', c), 'Pa', 1.0);
    zoomIdx = zoomIdx + 1;
end

% Seismic Z/R/T if possible, otherwise plot original three components.
wseis = getSeismicDisplayWaveforms(cfg, w, zoomStart, zoomEnd);
labels = {'Seismic vertical', 'Seismic radial/N', 'Seismic transverse/E'};
for c = 1:min(3, numel(wseis))
    plotZoomWaveform(ax.Zoom(zoomIdx), wseis(c), cfg, zoomStart, zoomEnd, labels{c}, '\mum/s', 1/1000);
    zoomIdx = zoomIdx + 1;
end

% Rectilinearity/planarity panel if GISMO threecomp methods are available.
plotParticleMotionMetric(ax.Zoom(zoomIdx), cfg, w, zoomStart, zoomEnd);
end

function plotZoomWaveform(axh, wone, cfg, t0, t1, label, units, scale)
try
    wz = extract(wone, 'time', t0, t1);
catch
    wz = wone;
end
[t, x] = waveformTimeData(wz);
tsec = (t - cfg.StartTime) * 86400;
plot(axh, tsec, x .* scale, 'LineWidth', 1.2);
xlim(axh, ([t0 t1] - cfg.StartTime) * 86400);
ylabel(axh, units);
title(axh, label, 'Interpreter','none');
grid(axh, 'on');
hold(axh, 'on');
x0 = (t0 - cfg.StartTime)*86400;
line(axh, [x0 x0], ylim(axh), 'Color','k', 'LineWidth', 1.2);
for d = 1:numel(cfg.Overlay.DelaysSeconds)
    xd = x0 + cfg.Overlay.DelaysSeconds(d);
    line(axh, [xd xd], ylim(axh), 'Color', cfg.Overlay.LineStyles{d}, 'LineWidth', 1.2);
end
hold(axh, 'off');
end

function wseis = getSeismicDisplayWaveforms(cfg, w, t0, t1)
idx = getfielddefault(cfg, 'SeismicZNEIndices', []);
if isempty(idx)
    wseis = w(cfg.SeismicIndex);
    return
end
wraw = w(idx);
try
    wz = extract(wraw, 'time', t0, t1);
catch
    wz = wraw;
end
if exist('threecomp','file') == 2
    try
        tc = threecomp(wz', cfg.SeismicRotateBackAzimuth);
        tr = tc.rotate();
        wseis = get(tr, 'waveform');
        return
    catch
        % Fall back to unrotated components.
    end
end
wseis = wz;
end

function plotParticleMotionMetric(axh, cfg, w, t0, t1)
idx = getfielddefault(cfg, 'SeismicZNEIndices', []);
if isempty(idx) || exist('threecomp','file') ~= 2
    axis(axh, 'off');
    text(axh, 0.05, 0.5, 'Rectilinearity unavailable', 'Units','normalized');
    return
end
try
    wsz = extract(w(idx), 'time', t0, t1);
    tc = threecomp(wsz', cfg.SeismicRotateBackAzimuth);
    tc1 = tc.rotate();
    tc2 = tc1.particlemotion();
    rl = get(tc2, 'rectilinearity');
    pl = get(tc2, 'planarity');
    [tr, xr] = waveformTimeData(rl);
    [tp, xp] = waveformTimeData(pl);
    plot(axh, (tr-cfg.StartTime)*86400, xr, 'm-', 'LineWidth', 1.2); hold(axh, 'on');
    plot(axh, (tp-cfg.StartTime)*86400, xp, 'c-', 'LineWidth', 1.2); hold(axh, 'off');
    xlim(axh, ([t0 t1] - cfg.StartTime)*86400);
    ylim(axh, [0 1]);
    title(axh, 'Rectilinearity / planarity');
    xlabel(axh, 'Seconds from render start');
    grid(axh, 'on');
catch ME
    axis(axh, 'off');
    text(axh, 0.05, 0.5, sprintf('Particle-motion metric unavailable: %s', ME.message), ...
        'Units','normalized', 'Interpreter','none');
end
end

function [t, x] = waveformTimeData(wone)
t = get(wone, 'timevector');
x = get(wone, 'data');
t = t(:);
x = x(:);
end

function exportFrame(fig, frameFile)
try
    exportgraphics(fig, frameFile, 'Resolution', 120);
catch
    print(fig, '-dpng', frameFile);
end
end

function val = getfielddefault(s, field, defaultValue)
if isfield(s, field)
    val = s.(field);
else
    val = defaultValue;
end
end
