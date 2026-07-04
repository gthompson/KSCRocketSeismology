# PASSCAL dbbuild metadata utility

This refactors the legacy script:

```text
passcal_create_dbbuild_batchfiles.m
```

into a small, reusable package for writing Antelope `dbbuild` network parameter files and station inventory tables for the KSC RocketSeis PASSCAL deployment.

## Main driver

```matlab
10_create_passcal_dbbuild_files
```

This writes:

```text
dbbuild_files/
  networkYYYYJJJ.pf
  KSCnetwork.txt
```

## Package

```text
+passcal/
  kscNetworkConfig.m
  kscPasscalStations.m
  writeNetworkPfFiles.m
  writeStationInventory.m
  addSourceDistanceAzimuth.m
  printStationDistances.m
  getNetworkChangeDates.m
  stationActiveOnDate.m
  datenumToJdayString.m
```

## What the original script did

1. Defined SLC-41 source coordinates.
2. Defined RocketSeis/PASSCAL network metadata.
3. Defined BHP1–BHP8, FIREP, and TANKP station metadata, including:
   - station coordinates,
   - locations,
   - channel codes,
   - sensor serial numbers,
   - datalogger serial numbers,
   - on/off dates,
   - orientations,
   - sample rates.
4. Wrote one `networkYYYYJJJ.pf` file for each station on/off change date.
5. Wrote a tab-delimited `KSCnetwork.txt` station-location inventory.
6. Contained some later exploratory code for station distances and waveform loading.

## Refactor choices

- Station metadata now lives in `+passcal/kscPasscalStations.m`.
- Paths, network code, source coordinate, gain, and defaults live in `+passcal/kscNetworkConfig.m`.
- PF writing is handled by `+passcal/writeNetworkPfFiles.m`.
- Inventory writing is handled by `+passcal/writeStationInventory.m`.
- Distance/azimuth calculations are optional and avoid the Mapping Toolbox.
- The exploratory waveform-loading code at the end of the original script was not kept in the active workflow.

## Dependencies

Required:

- MATLAB

Optional:

- Antelope/dbbuild command-line tools to actually consume the generated PF files.

No GISMO, Antelope MATLAB toolbox, Mapping Toolbox, or Signal Processing Toolbox is required to generate the PF files.

## Notes

Some original comments indicate uncertain station orientation or datalogger assignments. These were preserved in the `notes` field of each station entry and exported to `KSCnetwork.txt`.
