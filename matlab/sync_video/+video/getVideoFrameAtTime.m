function frame = getVideoFrameAtTime(video, utcDatenum)
%GETVIDEOFRAMEATTIME Return nearest video frame for an absolute UTC time.
%
% frame = falcon9.getVideoFrameAtTime(video, utcDatenum)

frame = [];
if isempty(video.Reader) || ~isvalidVideoReader(video.Reader)
    return
end

secondsFromStart = (utcDatenum - video.StartTime) * 86400;
if secondsFromStart < 0 || secondsFromStart > video.Duration
    return
end

try
    video.Reader.CurrentTime = min(max(secondsFromStart, 0), max(video.Duration - 1/video.Reader.FrameRate, 0));
    frame = readFrame(video.Reader);
catch
    frame = [];
end
end

function tf = isvalidVideoReader(vr)
tf = ~isempty(vr) && isobject(vr);
end
