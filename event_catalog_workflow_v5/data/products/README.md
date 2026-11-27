# Per-event products (`ksc-rockets process`)

    ksc-rockets process --events-file data/products/pilot_events.txt --run-id pilot-20261125

For each event, `ksclib.event_products.process_event` reads the waveforms of the network era
(`07_ensemble_paper/ensemble.yaml`: `SDS_KSC` for 2016–2022, the 2026 master SDS), removes the
instrument response, computes metrics, picks STA/LTA onsets, and writes the large files outside
Git to `[products] out_root` (`~/work/KSC_event_catalog/<YYYY>/<event_id>/`):

| file | content |
|---|---|
| `raw_counts.mseed` | raw counts, Steim2, catalog time −900 s to +900 s (reprocess after response fixes) |
| `corrected.mseed` | Pa and m/s, float32, noise + signal window |
| `plots/record_section_{pressure,seismic_Z}.png` | traces by distance, airwave moveout (343 m/s) and onsets |
| `plots/station_<STA>.png` | waveform and spectrogram per channel |
| `metrics.csv`, `onsets.csv`, `stations.csv`, `manifest.json` | as below; manifest has parameters, era, StationXML, warnings |

The run tables go to `~/work/KSC_event_catalog/tables/` (not Git) and are loaded into
`data/processed/ksc_rockets.sqlite` after each run and every `rebuild` (skipped, with a message, when
the drive is not mounted). Reprocessing an event replaces its rows. This folder keeps only the
pilot event list and this README.

| file / sqlite table | content |
|---|---|
| `processing_runs` | run id, code commit, products version, parameters, output root |
| `event_processing` | status per event (`ok`, `no_data`, `not_corrected`, `error`) |
| `measurements` | event × channel × metric (long table), with `data_source`, `qc_flag` |
| `onsets` | STA/LTA onset per channel; `origin_est_s` = onset − distance / 343 m/s |
| `event_products` | paths of the files above |
| `event_links` | `../curated/event_links.csv` (in Git): external links (webcasts, weather, regional data) — empty, for later |
| `event_tiers` (view) | usability tiers of the science plan §3.3 |

`../curated/detected_times.csv`: event origin from the best group of pressure onsets that agree
within 3 s (most stations, then strongest STA/LTA). Read by the catalog into
`events.detected_time_utc`, which becomes the event time only when the source time is coarser than
a second (rule in `04_event_catalog/SQLITE_CATALOG.md`). Only detections that are source times at
the pad are written (`ksclib.event_products.catalog_usable`); every detection, with the reason when
it is not used, is in `event_processing` (`detected_*` columns). Not used:

* booms (landings, reentries) and moving events (rollouts): onset − r/c is not their source time;
* launches whose nearest detecting station is > 5 km from the pad: the first clear arrival there
  comes from the rising vehicle, so the time is late (AA-2 2019: +23 s from 13.5 km);
* one-station detections with a competing arrival ≥ 0.8 × as strong (Falcon Heavy static fire
  2019-04-05: two bursts 65 s apart on every BCHH channel; Delta IV Heavy NROL-37 2016).

**Metrics** (science plan §2.1–2.2, band-limited: high-pass 0.5 Hz pressure / 1 Hz seismic up to
0.4 × sampling rate; signal window −30 s to +300 s, noise window the 300 s before):
peak, peak_positive, peak_negative, peak_to_peak, t_peak_s, noise_peak, snr_peak, rms_signal,
rms_noise, integrated_square, integrated_square_minus_noise, duration_5_95_s, skewness, kurtosis,
f_dominant_hz, f_centroid_hz, f_snr10_min/max_hz, band_<lo>_<hi>hz_mean_square / _snr_power;
pressure: spl_peak_db (unweighted, re 20 µPa), leq_db, sel_db, dpdt_skewness, dpdt_kurtosis;
seismic: pgv, pga, pgd; per station (`kind = seismic_vector`): pgv_horizontal_vector, pgv_3c_vector.

**Caveat:** `03_stationxml/KSC.xml` gains are known to be wrong for some epochs (DVEL1–3, RBLAB
infraBSU at 1 Vpp; geophones), so absolute amplitudes of the pilot are provisional. Rerun after
the StationXML is fixed; `processing_runs` records which version was used.

## Web pages

    ksc-rockets build-site            # -> ~/work/KSC_event_catalog/site/index.html

An index of every catalog event (filters by year, type, pad, data; sortable columns; strongest SPL,
Pa and PGV among channels with SNR >= 3) and one page per event: catalog details, every time field
and which one won, archive stations, the detected source time and why it is or is not used,
record sections, per-channel metric tables, STA/LTA onsets, per-station waveform and spectrogram
plots, the miniSEED files and external links. Pages link to the plots by relative path, so the
site opens from disk and can be copied with the event folders to a web server. Events with no
recordings get a page too. `--event-id` / `--events-file` limit which event pages are rewritten.

## Weather

    ksc-rockets fetch-weather --events-file data/products/pilot_events.txt

For each event, the files closest in time are downloaded once to `~/work/KSC_event_catalog/weather/`
(`kscrockets.weather`), and one summary row per event goes to `tables/event_weather.csv` (sqlite
`event_weather`), shown on the event page with its offset from the event time:

* **KSC weather towers** (Spaceport Weather Archive, kscweather.ksc.nasa.gov/wxarchive, not quality
  controlled): the 1-minute time step closest to the event (5-minute data if none within 15 min).
  Mean over towers of the lowest temperature/RH sensor (6 ft) and the vector mean of each tower's
  lowest wind sensor (12–54 ft), and the tower nearest the pad. Files before 2023 are fixed-width
  (`T1MMDDHHMM.dat`, several 1-minute blocks per file, no coordinates); tower coordinates come from
  `data/raw/ksc_weather_towers.csv` (the 2026 tower list).
* **Airports** (Iowa Environmental Mesonet ASOS): the METAR closest in time among XMR, TTS, TIX and
  COF (Melbourne only if none reported).
* **Wind profilers**, saved but not summarised yet: the 915 MHz profiler files (Q1–Q5) and the 48 MHz
  TDRWP file (M7) closest to the event.

The event pages also show a map (Leaflet, satellite or street tiles; needs internet to view) of the
pad, the stations that recorded the event coloured by best SNR, and the weather tower and airport.

## Publishing (GitHub Pages + Zenodo/Box)

    ksc-rockets package-waveforms        # -> ~/work/KSC_event_catalog/archive/ksc_event_waveforms_<YYYY>.zip
    ksc-rockets build-site --web         # -> ~/work/KSC_event_catalog/site_web/ (self-contained)

GitHub Pages limits a site to 1 GB, so the published copy (`site_web/`) holds the pages and the plots
as WebP (1100 px wide, ~4x smaller than the PNGs; ~1.2 MB per event), and no waveform files. The
waveforms go to Zenodo (DOI; 50 GB and 100 files per record) or Box as one zip per year
(`package-waveforms`, with `files_index.csv`: size and SHA-256 of every file). After uploading, list
each zip's download URL in `data/curated/waveform_urls.csv` (`key` = year, or an event_id for a single
event) and rebuild with `--web`: the Files section of each event page then links to the year's zip
and names the file inside it. Until then it says "not online yet". `site_web/` has a `.nojekyll` and
can be pushed as is to a `gh-pages` branch (one commit, force-pushed, so the repository does not grow
with every rebuild). `raw_counts.mseed` does not depend on the StationXML, so it can be archived now;
`corrected.mseed` and the metrics should be re-archived after the gain fix (a new Zenodo version).
