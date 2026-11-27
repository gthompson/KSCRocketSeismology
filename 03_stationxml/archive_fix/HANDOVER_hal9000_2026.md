# Handover for Claude on hal9000: rename the 2026 Centaur channels (D?? → C??/H??)

Written 2026-11-27 by the StationXML session on the Mac. Branch: `shared-ksclib`. Conda env: `flovopy_plus`.
Never `pip install`. Do not edit `09_artemis2_paper/`. Commit to `shared-ksclib` only; never push unless asked.

## Background (decided by Glenn, 2026-11-26)
The Centaur names its channels with band code **D** at 250/500 sps. D means a short-period sensor (corner < 10 s).
The KSC Centaurs record broadband sensors only: Trillium Compact (120 s), infraBSU (~28 s) and Chaparral M25.
So the SEED codes are **C** at 250–999 sps and **H** at 80–249 sps. B20 2026-04-04..06-14 and the B24 huddle on
2026-01-08 ran at 100 sps under D names, so those records become H. SmartSolo `DP?` (5 Hz geophone) is
correctly D and must not change. Gem (`HD?`/`HDF`), Certimus, Silicon Audio and the Shakes are not affected.

## Already done
* `03_stationxml/KSC.xml` (2016–2026) uses C/H codes. It has no validator errors; the only 3 warnings are B23 `CL?`.
  `KSC_sds_codes.xml` holds the same responses under the archives' D codes. `KSC_1R_2016-2022.xml` is the DMC subset.
* **SDS_KSC (2016–2022) on hal is finished.** `archive_fix/fix_sds_ksc.py --apply` ran, then
  `rename_band_codes.py --apply`: 10,921 files renamed, 0 conflicts, 0 errors.
  * The originals are in `/data/remastered/SDS_KSC/_renamed_D_originals_20261126/`.
  * Files removed by the fix are in `_removed_20261126/`. Each folder has a `manifest.csv`.
  * Checked from the Mac: no D folders are left; 250 random files differ from their originals only in the band letter; every renamed day has a KSC.xml epoch except 22 dead-input days that were excluded on purpose.
  * **Do not empty either quarantine yet.** Glenn will compare the old copy at `/ZPOOL_BACKUP/data/remastered/SDS_KSC` first:
    `python 03_stationxml/archive_fix/compare_backup_unmatched.py --backup /ZPOOL_BACKUP/data/remastered/SDS_KSC --current /data/remastered/SDS_KSC`
    (read-only; writes `./compare_backup_unmatched.csv`).
* ksclib reads either spelling. `ksclib.seedcodes` and the alias patterns in `get_group_stream` do this. An event or era with
  `seed_band_codes: true` gets C/H names back even from a D archive.
* flovopy (branch `feature/gem-overflow` and `main`, both local and not pushed) renames new Centaur downloads to C/H
  during `ingest_centaur`, by default (`sources.centaur.seed_band_codes: true`). New data merged into a D archive
  therefore arrive as C/H, and ingest warns while the master still has D folders.
* The Artemis II and AMOS-6 notebooks have been switched to C codes. The New Glenn ones have not (see below).

## To do on hal: the 2026 data
1. **Find every 2026 SDS tree on hal that holds Centaur D channels.** Known: the service-run folders under the KSC data
   directory (from the Mac they appear as `/Volumes/classdata/KSC/2026*_service/2026/1R/...`), and any 2026 master SDS.
   Find them with:
   `find <root> -type d -regex '.*/D[DH][0-9A-Z]\.D' -path '*2026*' | sed 's#/[^/]*/[^/]*$##' | sort -u`
   List what you find, with sizes and free space (`du -sh`, `df -h`), before changing anything.
2. **Dry run** on each tree (reads only; writes `./rename_band_codes_manifest.csv`):
   `python 03_stationxml/archive_fix/rename_band_codes.py --sds <tree>`
   * Expect 0 conflicts.
   * Expected errors: B29 `DHZ` 2026-082..093 are zero-filled files with no parsable records (a restored copy exists, and ksclib's `event_stream_raw` uses it). They are skipped and stay as `DHZ`. Report any other error.
   * Day files that switch from 500 to 100 sps (B20 around 2026-094) are split into C?? and H?? files. That is expected.
3. **Wait for Glenn's go-ahead before `--apply`.** The New Glenn notebooks (`10_NewGlenn_paper/*.ipynb`,
   `read_newglenn_improved_v3.ipynb`) still select `DHZ`/`DD0–2`/`DDF` by name and must switch to C codes first.
   That is being handled in the New Glenn session on the Mac.
4. `--apply` moves each original to `<tree>/_renamed_D_originals_20261126/` after its renamed copy has been written and
   read back, so it needs free space equal to the D files. Use `--delete-originals` only if Glenn approves it explicitly
   and there isn't room; it is irreversible.
5. After applying, check the run the way SDS_KSC was checked:
   * no `D[DH]?.D` folders remain (except the B29 zero-filled days);
   * the counts in `manifest.csv` match;
   * a byte-compare of a random sample against the quarantined originals differs only at byte 15 of each record (D→C/H);
   * every C/H channel-day has an epoch in `03_stationxml/KSC.xml`.
6. Afterwards, read the renamed trees with `KSC.xml`, not `KSC_sds_codes.xml`.

The Mac-mini copy (`/Volumes/KSCGTdownld/SDS`, 8,676 D files, 548 GB, 416 GB free) is handled from the Mac.
Because of the space it will need `--delete-originals`, or more free disk.

## Still open (not for this task)
* XX.9BC5 2019-100 differs from BHP7.10 2019-100 over ~47,500 samples: needs a manual look.
* MTEGL has a 25 h gap (2022-11-19 08:00 to 11-20 09:00). The level jumps across it, so it's a real break. Glenn may find the raw minute files.
* B23 `CL?` vs `CN?`; what changed at the 2026-09-22 service; whether the L-22s had damping shunts.
