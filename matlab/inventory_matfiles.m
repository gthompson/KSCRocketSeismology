%% inventory_matfiles.m
matfiledir = '/Users/thompsong/Library/CloudStorage/Box-Box/thompsong/3_Project_Documents/NASAprojects/201602_Rocket_Seismology/matlab/data'
files = {
    'eventmatfile.mat'
    'matlab.mat'
    'waveform_for_jake.mat'
    'spacex_results.mat'
    'currentstuff.mat'
    'rocketseismograms.mat'
    'rocketseismograms_raw_rotated_integrated.mat'
    'traveltimes.mat'
    'spacexplosion.mat'
    'filtered_waveforms.mat'
    'arrivals.mat'
    'arrivals_with_waveforms.mat'
    'arrivals_with_waveforms_and_amplitudes.mat'
    'catalog.mat'
};
chdir(matfiledir)
for i = 1:numel(files)

    fprintf('\n====================================================\n');
    fprintf('%s\n',files{i});

    if ~exist(files{i},'file')
        fprintf('Missing\n');
        continue
    end

    S = whos('-file',files{i});

    fprintf('Variables:\n');

    for j=1:numel(S)
        fprintf('%25s   %-12s %8.1f MB\n',...
            S(j).name,...
            S(j).class,...
            prod(S(j).size)*S(j).bytes/prod(S(j).size)/1e6);
    end

end