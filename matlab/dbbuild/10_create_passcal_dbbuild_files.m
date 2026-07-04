%% 10_create_passcal_dbbuild_files.m
% Create Antelope dbbuild network PF files and a station inventory table.
%
% This refactors the legacy passcal_create_dbbuild_batchfiles.m script.

clearvars;

cfg = passcal.kscNetworkConfig();

if ~exist(cfg.OutputDir, 'dir')
    mkdir(cfg.OutputDir);
end

station = passcal.kscPasscalStations(cfg);

fprintf('Writing network*.pf files to %s\n', cfg.OutputDir);
pf_files = passcal.writeNetworkPfFiles(station, cfg);

fprintf('Writing station inventory table.\n');
inventory_file = passcal.writeStationInventory(station, cfg);

fprintf('\nWrote %d PF files.\n', numel(pf_files));
fprintf('Inventory: %s\n', inventory_file);
