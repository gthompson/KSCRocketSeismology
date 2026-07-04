function fh = plotArrayMap(easting_m, northing_m, varargin)
%PLOTARRAYMAP Plot infrasound array geometry relative to the source.
%
% fh = falcon9.plotArrayMap(easting_m, northing_m)
% fh = falcon9.plotArrayMap(..., 'Waveforms', w, 'WindSpeed', u, ...)
%
% Inputs
% ------
% easting_m, northing_m : numeric vectors
%     Station coordinates in metres relative to the source/launch pad.
%
% Name-value options
% ------------------
% Waveforms : GISMO waveform array, optional
%     Used only to extract channel labels with get(w(c),'channel').
% ChannelLabels : string/cellstr vector, optional
%     Explicit channel labels. Overrides Waveforms when supplied.
% WindSpeed : scalar, optional
%     Wind speed in m/s.
% WindDirection : scalar, optional
%     Wind direction in degrees, using the convention from the original
%     Falcon 9 scripts: east component = speed*sind(direction), north
%     component = speed*cosd(direction).
% WindOrigin : 1x2 numeric, optional
%     [east north] coordinate where the wind vector is drawn.
% MarkerColors : char/string/cell array, optional
%     Marker colors to cycle through. Default is the original 'rwbggg'.
% SourceLabel : char/string, optional
%     Label used in the title. Default: 'SLC-40'.
% MakeFigure : logical, optional
%     Create a new figure if true. Default true.
%
% Output
% ------
% fh : figure handle
%
% Notes
% -----
% This function replaces the old eventMap.m plotting snippet. It only plots
% geometry; it does not compute eastings/northings or modify analysis data.

    p = inputParser;
    p.addRequired('easting_m', @(x) isnumeric(x) && isvector(x));
    p.addRequired('northing_m', @(x) isnumeric(x) && isvector(x));
    p.addParameter('Waveforms', [], @(x) true);
    p.addParameter('ChannelLabels', {}, @(x) iscellstr(x) || isstring(x)); %#ok<ISCLSTR>
    p.addParameter('WindSpeed', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x)));
    p.addParameter('WindDirection', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x)));
    p.addParameter('WindOrigin', [440 1325], @(x) isnumeric(x) && numel(x) == 2);
    p.addParameter('MarkerColors', 'rwbggg', @(x) ischar(x) || isstring(x) || iscell(x));
    p.addParameter('SourceLabel', 'SLC-40', @(x) ischar(x) || isstring(x));
    p.addParameter('MakeFigure', true, @(x) islogical(x) && isscalar(x));
    p.parse(easting_m, northing_m, varargin{:});
    opts = p.Results;

    easting_m = easting_m(:);
    northing_m = northing_m(:);
    if numel(easting_m) ~= numel(northing_m)
        error('plotArrayMap:CoordinateSizeMismatch', ...
            'easting_m and northing_m must have the same number of elements.');
    end

    if opts.MakeFigure
        fh = figure('Name', 'Beach House array map');
    else
        fh = gcf;
    end

    labels = get_channel_labels(numel(easting_m), opts.Waveforms, opts.ChannelLabels);

    hold_state = ishold;
    hold on
    for c = 1:numel(easting_m)
        marker_col = get_marker_color(opts.MarkerColors, c);
        plot(easting_m(c), northing_m(c), 'o', ...
            'MarkerFaceColor', marker_col, ...
            'MarkerEdgeColor', 'k', ...
            'MarkerSize', 10);

        % Direction-to-source arrow. The /100 scale is retained from the
        % original eventMap.m to keep arrows readable on the array-scale map.
        quiver(easting_m(c), northing_m(c), -easting_m(c)/100, -northing_m(c)/100, 0);
        text(easting_m(c) + 1, northing_m(c), labels{c}, 'Interpreter', 'none');
    end

    if ~isempty(opts.WindSpeed) && ~isempty(opts.WindDirection)
        wind_origin = opts.WindOrigin(:).';
        u_east = opts.WindSpeed .* sind(opts.WindDirection);
        u_north = opts.WindSpeed .* cosd(opts.WindDirection);
        quiver(wind_origin(1), wind_origin(2), u_east, u_north, 0, 'k');
        text(wind_origin(1), wind_origin(2), 'wind');
    end

    grid on
    title(sprintf('Beach House array position relative to %s', string(opts.SourceLabel)));
    xlabel('Metres east');
    ylabel('Metres north');
    axis equal

    if ~hold_state
        hold off
    end
end

function labels = get_channel_labels(n, waveforms, channel_labels)
    if ~isempty(channel_labels)
        channel_labels = cellstr(channel_labels);
        labels = channel_labels(:).';
    else
        labels = cell(1, n);
        for c = 1:n
            labels{c} = sprintf('Ch%d', c);
        end
        if ~isempty(waveforms)
            for c = 1:min(n, numel(waveforms))
                try
                    chan = get(waveforms(c), 'channel');
                    labels{c} = char(chan);
                catch
                    % Keep default label.
                end
            end
        end
    end

    if numel(labels) < n
        for c = (numel(labels)+1):n
            labels{c} = sprintf('Ch%d', c);
        end
    end

    for c = 1:n
        label = char(labels{c});
        if numel(label) > 3
            label = label(1:3);
        end
        labels{c} = label;
    end
end

function marker_col = get_marker_color(marker_colors, idx)
    if iscell(marker_colors)
        marker_col = marker_colors{min(idx, numel(marker_colors))};
    else
        marker_colors = char(marker_colors);
        marker_col = marker_colors(min(idx, numel(marker_colors)));
    end
end
