# Ensemble paper (2016–2022): plan

Working title (from the shared science plan): *Six Years of Rocket Seismology: Systematic
Seismo-Acoustic Observations of Space Launches at Cape Canaveral, 2016–2022.*

**Governing document:** `notes/rocket_seismology_science_plan.md` (Glenn, 2026-11-25), Sections 2
(shared metric definitions), 3 (this paper) and 10 (Priority 1). It makes this the top-priority
paper and scopes it to **2016–2022**. The 2026 era stays in `ensemble.yaml` and the code because the
same bridge serves cross-checks and the 2026 papers, but 2026 launches are not part of this paper.
The extended catalog (branch `claude/jovial-ptolemy-8effbc`) found no KSC waveform archive for 2023–2025.
See "Status against the science plan" below for what exists and what does not.

The Artemis II papers study one launch in depth with a dense 2026 network. This paper does the
opposite: many launches (191 `orbital_launch` rows in the reconciled sqlite for 2016–2022, plus
aborts, static fires, a booster landing and AMOS-6), each recorded by a few stations, and asks what
is systematic — how pressure and ground motion scale with vehicle, pad and distance, how
air-to-ground coupling repeats at each site — and how the answer depends on the instruments of the day.

## How the folder is built

| Piece | Where | Role |
|---|---|---|
| Launch catalog | `event_catalog_workflow_v5` (`kscrockets`), reconciled sqlite `data/processed/ksc_rockets.sqlite` | event ids, times (with provenance and precision), pads, names |
| Catalog → Event bridge | `ksclib.catalog_events` | era selection, pad coordinates, time-dependent stations and responses, correction, peaks |
| Ensemble config | `07_ensemble_paper/ensemble.yaml` | eras, archives, response locations, pads, windows, output, events not yet in the catalog |
| Shared science code | `ksclib` (geometry, moving-source model, responses), flovopy (Gem overflow, SDS) | same methods as Artemis II and New Glenn |
| Notebooks | `07_ensemble_paper/NN_*.ipynb` | thin: select events, call ksclib, tabulate, plot |

Existing notebooks: `00_station_map` (network maps per campaign; reads the station spreadsheet,
still from `~/Dropbox/KSC_paper`), `10_rocket_barcharts` (launch statistics; still reads
`merged_launches.csv` directly — should switch to `ce.load_catalog`), and the new
`20_ensemble_subset_amplitudes` (8 launches, 2016–2026, peaks against distance).

## Proposed analyses and figures

1. **Launch population and network evolution (2016–2026).**
   Fig. 1: map(s) of every station epoch, coloured by campaign, with the pads (from `KSC.xml`
   epochs + 2026 sheets; `station_map.py`). Fig. 2: timeline — launches per month by vehicle/pad
   above, station/channel availability below (from `kscrockets extract` manifests or SDS
   discovery). Table 1: campaigns (dates, stations, sensors, sample rates, dataloggers, gains).
   Table 2: launches by vehicle × pad × year (notebook 10, from the catalog).
2. **Event-time refinement.** Catalog times are often minute precision and some sources disagree
   (`time_conflict`, `time_spread_s`). Refine T0 from the airwave onset at the nearest station
   with a weather-based sound speed (as `10_NewGlenn_paper`, `ksclib.weather`/`physics` on the New
   Glenn branch), and check against LL2/GCAT. Required before anything uses arrival times.
3. **Amplitude field: peak pressure and PGV vs distance** (Artemis II notebook 40 §7, generalised).
   Peak |p| > 0.5 Hz, vertical PGV > 1 Hz, per channel per launch; power-law fits
   *p = A r^−n* by vehicle and pad; distance-reduced pressure *p·r* as a source-strength proxy.
   Fig. 3: p and PGV vs distance, all launches, coloured by vehicle (notebook 20 at full scale).
   Fig. 4: reduced pressure by vehicle (box plots), compared with thrust (Falcon 9 ≈ 7.6 MN,
   Falcon Heavy ≈ 22.8 MN, Atlas V ≈ 3.8–12 MN by solid-booster count, Delta IV Heavy ≈ 9.4 MN, SLS ≈ 39 MN,
   New Glenn ≈ 17 MN) — does reduced pressure scale with thrust or with thrust × exhaust velocity
   (acoustic efficiency)?
4. **Pad and azimuth effects.** The same station sees LC39A, LC40 and LC41 launches at different
   distances and azimuths (e.g. BCHH ≈ 1.4 km from LC40, ≈ 4 km from LC39A). Use station × pad pairs
   with many launches of one vehicle (Falcon 9 from LC40 and LC39A at BCHH, S39A, DVEL) to separate
   pad geometry (flame trench orientation, deflector) from distance. Moving-source geometry
   (`ksclib.source_geometry`) needs launch azimuths: take them from the mission orbit (LL2) or set
   per family (Starlink ≈ 45–50°, GTO ≈ 90–100°, ISS ≈ 45°).
5. **Atmospheric effects.** For repeated launches recorded at the same station, relate the scatter
   of reduced pressure to wind along the ray, temperature and humidity at launch time (KSC weather
   towers; `ksclib.weather` from the New Glenn branch), and to time of day (inversion). Fig. 5:
   residual of the power-law fit vs along-ray wind.
6. **Spectra and usable bands** (Artemis II notebook 42). Launch-to-noise spectral ratios per
   channel; spectral peak frequency vs vehicle (larger exhaust → lower frequency?), and crackle
   statistics where sample rate allows (250 sps Centaur 2016–2021, 100 sps 2022 — limits crackle
   work, see Artemis II notebook 45).
7. **Air-to-ground coupling** (Artemis II notebooks 50/51). Every co-located infraBSU + Trillium
   (2016–2021 Centaur sites) or infrasound + geophone pair gives coupling coefficients (µm s⁻¹ Pa⁻¹),
   transfer functions and polarity; compare across sites, years and vehicles — this is where the
   ensemble is strongest, because the coupling is a site property and should repeat.
8. **Booster landings, static fires, aborts and the 2016 AMOS-6 explosion** as reference sources:
   landings (LZ1/LZ2 sonic booms) and static fires are short, near-stationary sources with known
   positions; AMOS-6 and New Glenn are static explosions (`kind: static`).

## Reuse of the Artemis II methods

| Artemis II notebook | Ensemble use | Changes needed |
|---|---|---|
| 40 amplitude field (§7) | peaks vs distance per launch → notebook 20 now | per-vehicle trajectories (`event.trajectory`), launch azimuth per launch, refined T0 |
| 40 retarded-time amplitudes, directivity | only for launches with ≥ 4 stations at different azimuths (2018–2019 BHP array, 2022, 2026) | same |
| 42 spectral ratios | every launch, every channel | move the PSD/usable-band code into ksclib (now inline in the notebook) |
| 50/51 coupling | every co-located pair | move `common_pair` and coupling estimators into ksclib |
| 20 infrasound clipping | 2016–2022 Centaur 40 Vpp vs 1 Vpp, clipping near pads | New Glenn `ksclib.clipping` (reference-sensor comparison) |

## Data gaps and calibration issues to resolve (decisions for the user)

1. **Catalog coverage stops at 2022-12-28.** 2023–2026 launches (≈ 400 from the Cape) are not in the
   reconciled catalog; only Artemis II is added by hand (`ensemble.yaml: extra_events`). Extend the
   catalog (LL2/GCAT caches already cover these years) and decide which 2023–2025 periods have any
   waveform data at all — the master SDS on `KSCGTdownld` starts in 2026, and the 2016–2022 SDS on
   `classdata` stops at 2022.
2. **Two catalogs disagree on event ids.** The untracked `data/processed/launch_catalog.csv` (in the
   main checkout's `KSCRocketSeismology_event_catalog_workflow_v5/`) uses registry ids
   (e.g. `ksc-0a37d378c793` for 2016-02-05), while the sqlite database in git and the 2016
   calibration outputs use reconciled ids (`ksc-14e6273111f1`). This paper uses the sqlite ids.
   Decide which is canonical before ids are written into products, and whether the untracked CSVs
   move into git.
3. **Gains in `KSC.xml` are wrong for some epochs (most important).** infraBSU sensors were only
   ever recorded at two Centaur settings: 40 Vpp (18.4 counts/Pa) or 1 Vpp (×40 preamp, 736 counts/Pa).
   *Cause:* `vpp` is blank in the master sheet (`ksc_stations_master*.csv/xlsx`) for every DVEL, DVEL1–3,
   RBLAB and RB166/268/383 row, and flovopy's builder (`flovopy/stationmetadata/build.py:330`) turns
   anything other than 1 or 40 into 40.
   *Audit done for DVEL/RBLAB* (notebook 15, proposed values in `03_stationxml/vpp_audit_DVEL_RBLAB.csv`):
   **DVEL1, DVEL2, RBLAB (Feb 2018) and DVEL3 (Feb 2019–Jan 2020) ran at 1 Vpp.** Evidence: Centaur 166's
   own dataless files for DVEL3 (×40 preamp on the infrasound inputs; BCHH1 control ×1); launch p·r against
   the beach-house references is ≈ 1.0–1.1 under 1 Vpp and ≈ 43 under 40 Vpp for DVEL3 over 8 launches, and
   ≈ 1–2 for the live DVEL1/DVEL2/RBLAB channels on the Falcon Heavy demo; night-time 0.15–0.35 Hz levels are
   only plausible under 1 Vpp. The references agree with each other (BCHH1 40 Vpp / BCHH2 1 Vpp: median 0.93
   over 17 launches). Still to do: put `vpp=1` in the master sheet for these rows, audit every other blank-`vpp`
   row (RB166/268/383 in 2021; the 2017 `DVEL` epoch, which has no SDS data and an end date of 2018-12-31
   that overlaps DVEL1–3), and rebuild `KSC.xml`.
   *Geophones:* the EH? channels (BHP1–8, FIREP, TANKP, 2018–2021; RT130 + L-22 in the master sheet) also
   read ≈ 40–50× high against Trilliums. `KSC.xml` gives 3.96×10⁷ counts/(m/s), which matches an RT130 at
   gain 1; L-22s on RT130s are often run at gain 32, which would explain a factor of ≈ 32. Not yet audited.
   *Known and stable:* BCHH DD2 (2016) reads ≈ 16× low against DD1/DD3 (also seen for AMOS-6); apply a
   fixed correction in the metadata.
4. **`KSC.xml` has no datalogger or sensor descriptions.** Gems were deployed only in 2026, so every
   2016–2022 `HD?`/`HH?` channel is a Centaur at 100 sps (`ensemble.yaml: gem_channel_prefix: null`).
   The rebuilt StationXML should carry datalogger, sensor and input range per channel epoch, so the
   setting is visible rather than implied by a number.
5. **Dead or unconnected channels and unmapped sensors.** SNR ≈ 1 with ≈ 0.1 Pa peaks: BCHH2 DD7
   (2018), DD8 (2019), HD5 (2022), DVEL1 DD3–DD6 (2018; DD4–6 sit at the digitizer floor, ≈ 1.5 counts),
   RBLAB DD1 (2018), FIRE DD1–3 (2016), 2026 B03 DD0–2, B05 DD1–2, B29 DD1–2. DVEL3 DD3 was cut by a
   lawnmower on 2019-07-01 (field notes). At RBLAB in 2021 (RB166/RB383 HD1–3, RB268 DDF) the infrasound
   shows no signal from Atlas V Lucy at 9.6 km while RB383 HHZ does — check channel mapping and `vpp`.
   `1R.UNK..HD1` (2026) is Gem 363, which the ingest mapping (`gem_mapping_artemis2_example.csv`) has not
   yet assigned to a station. Proposal: a per-channel bad-epoch list in `ensemble.yaml` (or the
   catalog's `qc_intervals` table, which exists but is empty), applied in `peak_amplitudes`.
6. **Stations without responses.** `XA.MTEGL` (2022, CN? channels) is in the SDS but not in `KSC.xml`;
   Raspberry Shake/Boom (`AM`) responses are nominal. B14 (2026) has no Centaur response before
   2026-06-14 (New Glenn session; `ksclib.centaur` fallback on that branch).
7. **Station coordinates for 2026.** The 2026 era currently takes coordinates from one sheet
   (`artemis2`) of the Box spreadsheet, i.e. the Artemis II layout. Gems and SmartSolos were only out
   for part of 2026 and Centaur sites changed between service runs, so a launch in, say, September
   would be given stations that were not there. Better: build a 2026 StationXML with epochs
   (`03_stationxml/1R_2026_2030/1R_stations.xml` has the Centaur sites but no dates, Gems or SmartSolos)
   and treat 2026 like 2016–2022, or read the `SDS2026_metadata` sheet's per-channel day ranges.
8. **Data gaps in 2016–2022.** 57 of 202 catalog events (28%) have no SDS files on the launch day (e.g.
   May–Aug 2016, Feb–Aug 2017 apart from R37BE, Apr–Aug 2018, late 2021–Mar 2022). Some may exist in
   `BUD_KSC` or `unmatched/` on `classdata`, or on older drives; worth one search before declaring them
   lost.
9. **SmartSolo polarity and units** (2026): geophone mV with reversed vertical polarity — handled for
   amplitudes (|v|), must be flipped for coupling polarity (Artemis II notebook 50 does this).
10. **Sample rates.** 250 sps (2016–2021 Centaur), 100 sps (2022 Centaur/Shake), 500 sps (2026
   Centaur) — compare peak amplitudes only after a common low-pass (e.g. 40 Hz) if high-frequency
   crackle dominates near-pad peaks.

## Status against the science plan (checked 2026-11-25)

What exists in this branch, what exists elsewhere, and what is missing. Nothing below is a result;
the only numbers are counts of catalog rows and the measurement settings in the code.

| Science plan item | Exists | Missing |
|---|---|---|
| 3.2 Network history and metadata | `00_station_map` (reads the sheet from `~/Dropbox/KSC_paper`); rebuilt `KSC.xml` 2016–2026 with audit trail on branch `claude/wizardly-faraday-01d6b3` (not merged here) | operation timeline, data-availability figure, station inventory table (sensor, datalogger, input range, sample rate per epoch), 1R network DOI |
| 3.3 Launch catalogue | sqlite: 202 events to 2022-12-28, with `mission` and landing columns (landing columns empty); extended to the present with a waveform-availability table on branch `claude/jovial-ptolemy-8effbc` (not merged here) | the six tiers (catalogued / waveforms / usable seismic / usable infrasound / quantitative quality / > 1 station), data-quality and processing-status columns, landing info, DOI |
| 3.4 Anatomy of launch signals | — | representative waveforms and spectrograms (near, intermediate, far; seismic ahead of airwave; ignition overpressure; ascent; sonic booms; landings) |
| 3.5 Acoustic amplitudes | `catalog_events.peak_amplitudes`: peak \|p\| after a 0.5 Hz high-pass, signal window −30…300 s, noise window, SNR, Gem-overflow lower bounds; run on the 8-launch subset only (notebook 20). `ksclib.pressure` (AMOS-6 port: baseline-corrected positive/negative extrema, reduced pressure) exists on newer branches, not here | peak SPL, peak positive/negative, peak-to-peak, RMS and Leq, SEL / ∫p² dt, duration, band energies; full-ensemble run; attenuation fits with uncertainties; grouped regression by vehicle/pad |
| 3.6 Seismic amplitudes | vertical PGV after a 1 Hz high-pass (`kind = seismic_Z`) | horizontal and vector PGV (and a stated definition), PGA, PGD, RMS velocity, ∫v² dt, band amplitudes |
| 3.7 Air-to-ground coupling (major section) | estimators only in Artemis II notebooks 50/51 | port to ksclib; per-station distributions across launches; frequency-dependent coupling |
| 3.8 Spectra and Doppler | estimators only in Artemis II notebook 42 | median spectra by vehicle, spectral evolution, first-order Doppler |
| 3.9 Historical archive | — | inventory of presentations, posters, abstracts, old catalogues and software |
| 2.4 Calibration and QC table | proposals in `03_stationxml/vpp_audit_DVEL_RBLAB.csv`; full audit on the StationXML branch; catalog schema already has empty `channel_epochs`, `qc_intervals` and `measurements` tables (the last with `metric_name`, `units`, `processing_version`, `qc_flag`) | one versioned table, populated and applied in `peak_amplitudes` |

**Metric definitions (science plan Sec. 2) — decision for implementation.** Put every metric in one
ksclib module shared by all five papers (Sec. 9), rather than in `catalog_events` or notebooks, and
have `peak_amplitudes` call it. Every value carries its band (high-pass and low-pass corner, sample
rate), window and processing version, so "band-limited, unweighted peak SPL" is stated with its
bandwidth. Peak SPL = 20 log10(peak |p| / 20 µPa). PGV must say which: the current column is the
vertical component only. Write results to the catalog's `measurements` table (or a parquet with the
same columns), keyed by `event_id` and channel epoch.

**Items in this plan that the science plan does not ask for.** T0 refinement (analysis 2) stays,
because arrival times and windows depend on it. Pad/azimuth (4) and atmosphere (5) are secondary:
the science plan says to keep the paper manageable, so do them only if the amplitude residuals
need explaining. Thrust comparisons (3) need sourced thrust values before any number goes into text.

## Next steps (science plan Priority 1 order)

1. **Merge in the rebuilt StationXML and the extended catalog** (branches above; the user decides).
   Then re-run notebooks 15 and 20 against the new `KSC.xml`.
2. **Shared metric module** (Sec. 2.1–2.3): peak ±, \|p\|, p-p, SPL, RMS/Leq, SEL/∫p², duration;
   PGV (Z, H, 3-C vector), PGA, PGD, RMS v, ∫v²; band versions. Reuse `ksclib.pressure` once merged.
   Tests with synthetic signals of known SPL/SEL. **In progress (2026-11-25), not committed:** the
   catalog session is writing `ksclib.event_products` (`PRODUCTS_VERSION = "0.2"`: per-channel SPL/SEL/
   Leq, vector metrics, STA/LTA onsets, built on `catalog_events`) in its worktree on branch
   `claude/jovial-ptolemy-8effbc`. Build on that; do not write a second metric module here.
3. **Catalogue tiers and QC** (Sec. 3.3, 2.4): populate `channel_epochs`/`qc_intervals` from the
   StationXML audit and the dead-channel list (item 5 above); add the tier columns.
4. **Full-ensemble run** of the metrics over every 2016–2022 event with data, cached per `event_id`.
5. **Network-history figures and tables** (Sec. 3.2, Figs 1–3).
6. **Anatomy examples** (Sec. 3.4, Fig. 4), then amplitude-distance fits (Figs 5–8).
7. **Coupling and spectra**: port the Artemis II notebook 42/50/51 estimators into ksclib (Figs 9–12).
8. Event-time refinement where arrival times are needed; weather (`ksclib.weather` on the New Glenn
   branch) only if residuals call for it.
9. Historical archive inventory (Sec. 3.9) — needs the user's list of past presentations.
