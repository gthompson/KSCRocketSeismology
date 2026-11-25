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

The small tables here are in Git and loaded into `data/processed/ksc_rockets.sqlite` (also after
every `rebuild`). Reprocessing an event replaces its rows.

| file / sqlite table | content |
|---|---|
| `processing_runs` | run id, code commit, products version, parameters, output root |
| `event_processing` | status per event (`ok`, `no_data`, `not_corrected`, `error`) |
| `measurements` | event × channel × metric (long table), with `data_source`, `qc_flag` |
| `onsets` | STA/LTA onset per channel; `origin_est_s` = onset − distance / 343 m/s |
| `event_products` | paths of the files above |
| `event_links` | external links (webcasts, weather, regional data) — empty, for later |
| `event_tiers` (view) | usability tiers of the science plan §3.3 |

`../curated/detected_times.csv`: event origin from the largest group of pressure onsets that agree
within 3 s (read by the catalog into `events.detected_time_utc`). `nearest_km` matters: far from
the pad the first clear arrival of a launch comes from the rising vehicle, so the time is late.

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
