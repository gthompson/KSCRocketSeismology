# KSC weather towers, 2026-05-29 00:00-01:30 UTC

1-minute files `WT_1MIN_YYYYMMDDHHMM.dat` (times UTC, as in each file's header "0100Z") from the
KSC Spaceport Weather Archive, https://kscweather.ksc.nasa.gov/wxarchive (product midds/WINDS_TOWER).
Downloaded 2026-11-27, one file per request through the archive's Explorer (select, then Download).

Each row: tower ID (NW/SE/NE/SW suffix = sensor side; use the side named in PREVAILING), lat, lon,
sensor height (ft), 1-min average wind direction (deg) and speed (kt), peaks, temperature and dew
point (F), RH (%), and other channels. 999 = missing. The archive states the data are not quality controlled.
