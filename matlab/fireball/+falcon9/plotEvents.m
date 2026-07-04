function plotEvents(wevent, filepattern, figureOutDirectory)
%PLOTEVENTS Plot segmented waveform events to PNG files.
%
%   falcon9.plotEvents(wevent, filepattern, figureOutDirectory)
%
%   Requires plot_panels.m on the MATLAB path. This helper is part of the
%   original GISMO-style workflow and is not included in this package.

    if nargin < 2 || isempty(filepattern)
        filepattern = 'event_';
    end
    if nargin < 3 || isempty(figureOutDirectory)
        figureOutDirectory = pwd;
    end

    if ~exist(figureOutDirectory, 'dir')
        mkdir(figureOutDirectory);
    end
    if exist('plot_panels', 'file') ~= 2
        error('falcon9:plotEvents:MissingDependency', ...
              'plot_panels.m is required but was not found on the MATLAB path.');
    end

    numEvents = numel(wevent);
    for eventNumber = 1:numEvents
        fprintf('- plotting event %d of %d\n', eventNumber, numEvents);
        fig = figure('Visible', 'off'); %#ok<NASGU>
        plot_panels(wevent{eventNumber});

        axesHandles = findall(gcf, 'Type', 'axes');
        if ~isempty(axesHandles)
            title(axesHandles(end), sprintf('Event %d', eventNumber));
        end

        outfile = fullfile(figureOutDirectory, sprintf('%s%03d.png', filepattern, eventNumber));
        print(gcf, '-dpng', outfile);
        close(gcf);
    end
end
