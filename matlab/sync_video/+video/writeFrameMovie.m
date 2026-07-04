function writeFrameMovie(frameDir, movieFile, opts)
%WRITEFRAMEMOVIE Assemble rendered PNG/JPG frames into a movie file.
%
% falcon9.writeFrameMovie(frameDir, movieFile, 'FPS', 30)

arguments
    frameDir (1,:) char
    movieFile (1,:) char
    opts.FPS (1,1) double = 30
    opts.Profile (1,:) char = 'Motion JPEG AVI'
    opts.Quality (1,1) double = 95
    opts.Verbose (1,1) logical = true
end

files = dir(fullfile(frameDir, '*.png'));
if isempty(files)
    files = dir(fullfile(frameDir, '*.jpg'));
end
if isempty(files)
    error('falcon9:NoFrames', 'No PNG/JPG frames found in %s', frameDir);
end
[~, order] = sort({files.name});
files = files(order);

outDir = fileparts(movieFile);
if ~isempty(outDir) && ~exist(outDir, 'dir')
    mkdir(outDir);
end

vw = VideoWriter(movieFile, opts.Profile);
vw.FrameRate = opts.FPS;
if isprop(vw, 'Quality')
    vw.Quality = opts.Quality;
end
open(vw);
cleanupObj = onCleanup(@() close(vw));

for k = 1:numel(files)
    if opts.Verbose
        fprintf('Writing movie frame %d of %d\n', k, numel(files));
    end
    img = imread(fullfile(files(k).folder, files(k).name));
    writeVideo(vw, img);
end
end
