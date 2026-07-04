function launch_table = loadLaunchStatsSpreadsheet(workbook_file, varargin)
%LOADLAUNCHSTATSSPREADSHEET Load launch-statistics spreadsheet.
%
% launch_table = rocketensemble.loadLaunchStatsSpreadsheet(workbook_file)
%
% This replaces the auto-generated xlsread script
% plot_rocket_launch_stats.m.
%
% Expected spreadsheet columns, following the legacy script:
%   1  DATE        Excel serial date
%   2  TIME        fraction of day
%   3  COMPANY
%   4  ROCKETTYPE
%   5  PAYLOAD
%   6  MASSt
%   7  SLC
%   8  ORBIT
%   10 RECORDED    cumulative recorded launches
%   11 SPACEX      cumulative SpaceX launches
%   12 ALL         cumulative all launches
%   13 OTHER       cumulative other recorded events

p = inputParser;
p.addRequired('workbook_file', @(x) ischar(x) || isstring(x));
p.addParameter('Sheet', 'Sheet1', @(x) ischar(x) || isstring(x));
p.addParameter('ExcelDateOrigin', datenum(1899, 12, 31) - 1, @isnumeric);
p.parse(workbook_file, varargin{:});
opt = p.Results;

if ~exist(workbook_file, 'file')
    error('Workbook not found: %s', workbook_file);
end

% Prefer readtable when available; fall back to xlsread-style raw import.
try
    opts = detectImportOptions(workbook_file, 'Sheet', opt.Sheet);
    T = readtable(workbook_file, opts);
    launch_table = normalizeLaunchTable(T, opt.ExcelDateOrigin);
catch
    [~, ~, raw] = xlsread(workbook_file, opt.Sheet); %#ok<XLSRD>
    launch_table = loadFromRawCells(raw, opt.ExcelDateOrigin);
end
end


function launch_table = loadFromRawCells(raw, excel_date_origin)
raw = raw(2:end, :);
raw(cellfun(@(x) ~isempty(x) && isnumeric(x) && isnan(x), raw)) = {''};

string_vectors = string(raw(:, [3, 4, 5, 8, 13]));
string_vectors(ismissing(string_vectors)) = '';

numeric_raw = raw(:, [1, 2, 6, 7, 10, 11, 12, 13]);
R = cellfun(@(x) ~isnumeric(x) && ~islogical(x), numeric_raw);
numeric_raw(R) = {NaN};
data = reshape([numeric_raw{:}], size(numeric_raw));

launch_table = table();
launch_table.DATE = data(:, 1);
launch_table.TIME = data(:, 2);
launch_table.COMPANY = categorical(string_vectors(:, 1));
launch_table.ROCKETTYPE = categorical(string_vectors(:, 2));
launch_table.PAYLOAD = string_vectors(:, 3);
launch_table.MASSt = data(:, 3);
launch_table.SLC = data(:, 4);
launch_table.ORBIT = categorical(string_vectors(:, 4));
launch_table.RECORDED = data(:, 5);
launch_table.SPACEX = data(:, 6);
launch_table.ALL = data(:, 7);
launch_table.OTHER = data(:, 8);

launch_table.DateTimeDatenum = excel_date_origin + launch_table.DATE + launch_table.TIME;
launch_table.DateTime = datetime(launch_table.DateTimeDatenum, 'ConvertFrom', 'datenum');
end


function launch_table = normalizeLaunchTable(T, excel_date_origin)
% Normalize a readtable result to the expected legacy variable names.

names = upper(string(T.Properties.VariableNames));

launch_table = table();

launch_table.DATE = getColumn(T, names, ["DATE", "VAR1"]);
launch_table.TIME = getColumn(T, names, ["TIME", "VAR2"]);
launch_table.COMPANY = categorical(string(getColumn(T, names, ["COMPANY", "VAR3"])));
launch_table.ROCKETTYPE = categorical(string(getColumn(T, names, ["ROCKETTYPE", "ROCKET_TYPE", "VAR4"])));
launch_table.PAYLOAD = string(getColumn(T, names, ["PAYLOAD", "VAR5"]));
launch_table.MASSt = getColumn(T, names, ["MASST", "MASS_T", "MASS", "VAR6"]);
launch_table.SLC = getColumn(T, names, ["SLC", "VAR7"]);
launch_table.ORBIT = categorical(string(getColumn(T, names, ["ORBIT", "VAR8"])));
launch_table.RECORDED = getColumn(T, names, ["RECORDED", "VAR10"]);
launch_table.SPACEX = getColumn(T, names, ["SPACEX", "SPACE_X", "VAR11"]);
launch_table.ALL = getColumn(T, names, ["ALL", "VAR12"]);
launch_table.OTHER = getColumn(T, names, ["OTHER", "VAR13"]);

launch_table.DateTimeDatenum = excel_date_origin + launch_table.DATE + launch_table.TIME;
launch_table.DateTime = datetime(launch_table.DateTimeDatenum, 'ConvertFrom', 'datenum');
end


function col = getColumn(T, upper_names, candidates)
idx = find(ismember(upper_names, candidates), 1, 'first');
if isempty(idx)
    col = nan(height(T), 1);
else
    col = T{:, idx};
    if iscell(col)
        try
            col = cell2mat(col);
        catch
            col = string(col);
        end
    end
end
end
