function videos = openVideoSources(videoCfg)
%OPENVIDEOSOURCES Open VideoReader objects and attach timing metadata.

arguments
    videoCfg struct
end

videos = repmat(struct('Name','','VideoFile','','StartTime',NaN,'Panel',1, ...
    'Reader',[],'FrameRate',NaN,'Duration',NaN), size(videoCfg));

for k = 1:numel(videoCfg)
    if ~isfile(videoCfg(k).VideoFile)
        warning('falcon9:MissingVideoFile', 'Video file not found: %s', videoCfg(k).VideoFile);
        videos(k).Name = videoCfg(k).Name;
        videos(k).VideoFile = videoCfg(k).VideoFile;
        videos(k).StartTime = videoCfg(k).StartTime;
        videos(k).Panel = videoCfg(k).Panel;
        continue
    end
    vr = VideoReader(videoCfg(k).VideoFile);
    videos(k).Name = videoCfg(k).Name;
    videos(k).VideoFile = videoCfg(k).VideoFile;
    videos(k).StartTime = videoCfg(k).StartTime;
    videos(k).Panel = videoCfg(k).Panel;
    videos(k).Reader = vr;
    videos(k).FrameRate = vr.FrameRate;
    videos(k).Duration = vr.Duration;
end
end
