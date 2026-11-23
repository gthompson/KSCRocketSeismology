# Ensemble paper (2016–2026): plan

Working title: *Ten years of seismo-acoustic recordings of rocket launches at Kennedy Space Center
and Cape Canaveral: amplitude scaling with vehicle, pad and distance.*

The Artemis II papers study one launch in depth with a dense 2026 network. This paper does the
opposite: many launches (≈200 in 2016–2022 alone, plus 2023–2026), each recorded by a few
stations, and asks what is systematic — how peak pressure and ground motion scale with vehicle,
pad, distance and atmosphere — and how the answer depends on the instruments of the day.

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
3. **Gains in `KSC.xml` are wrong for some epochs (most important; notebook 20 §Findings).**
   infraBSU channels carry either 18.4 or 736 counts/Pa (40 Vpp vs 1 Vpp Centaur input range, a
   factor of 40). Where an 18.4 and a 736 channel share a site they agree (BCHH1 vs BCHH2 for Falcon
   Heavy 2018 and AA-2 2019; BCHH4 vs BCHH2 for Artemis I 2022), but **DVEL1, DVEL2, RBLAB (Feb 2018)
   and DVEL3 (2019) read ≈ 35–40× too high** (AA-2: 340–400 Pa at 15 km vs ≈ 10 Pa at 13.5 km;
   Falcon Heavy: up to 6.9 kPa at 3.3 km) — as if those Centaurs ran at 1 Vpp. The **EH? geophones
   (BHP1–8, FIREP, TANKP, 2018–2021) also read ≈ 40–50× high** (AA-2: 2–4 mm/s at 12–13 km vs
   0.05 mm/s on the DVEL3 Trillium at 15 km; Atlas V AEHF-4: 4–8 cm/s at 1.5 km). **BCHH DD2 (2016)**
   reads ≈ 16× low against DD1/DD3 (SES-9, NROL-37; also in the 2016 relative-calibration outputs).
   Needs a per-epoch audit of Centaur gain settings (Centaur config files or response XMLs written
   at the time, as in 2026) and a corrected `KSC.xml` before absolute amplitudes are published.
   Meanwhile, co-located channel ratios (notebook 20 §7) give a cheap automatic check for every launch.
4. **`KSC.xml` has no datalogger or sensor descriptions.** Which 2016–2022 `HD?`/`DD?` channels are
   infraBSU on Centaur, Chaparral M25 (`DDF`), or Gem loggers is inferred from channel code and gain.
   `ensemble.yaml` assumes no Gems before 2026 (`gem_channel_prefix: null`) — please confirm (e.g. the
   2018 DVEL1 `HD1–HD6` and 2021 Riverbend `HD1–HD3` at 100 sps).
5. **Dead or unconnected channels and unmapped sensors.** SNR ≈ 1 with ≈ 0.1 Pa peaks: BCHH2 DD7
   (2018), DD8 (2019), HD5 (2022), DVEL1 DD4–6 (2018), FIRE DD1–3 (2016), 2026 B03 DD0–2, B05 DD1–2,
   B29 DD1–2. Riverbend infrasound (RB166/RB383 HD1–3, RB268 DDF) shows no Lucy signal at 9.6 km
   while RB383 HHZ does — check channel mapping. `1R.UNK..HD1` (2026) is an unmapped Gem. Proposal:
   a per-channel bad-epoch list in `ensemble.yaml` (or the catalog's `qc_intervals` table, which
   exists but is empty), applied in `peak_amplitudes`.
6. **Stations without responses.** `XA.MTEGL` (2022, CN? channels) is in the SDS but not in `KSC.xml`;
   Raspberry Shake/Boom (`AM`) responses are nominal. B14 (2026) has no Centaur response before
   2026-06-14 (New Glenn session; `ksclib.centaur` fallback on that branch).
7. **Station sets for 2026 campaigns.** The 2026 era uses the `artemis2` sheet for coordinates.
   Other 2026 launches (New Glenn, later service runs) need per-campaign sheets, or the bridge should
   read `SDS2026_metadata` (per-channel Start/End DOY) instead.
8. **Data gaps in 2016–2022.** 57 of 202 catalog events (28%) have no SDS files on the launch day (e.g.
   May–Aug 2016, Feb–Aug 2017 apart from R37BE, Apr–Aug 2018, late 2021–Mar 2022). Some may exist in
   `BUD_KSC` or `unmatched/` on `classdata`, or on older drives; worth one search before declaring them
   lost.
9. **SmartSolo polarity and units** (2026): geophone mV with reversed vertical polarity — handled for
   amplitudes (|v|), must be flipped for coupling polarity (Artemis II notebook 50 does this).
10. **Sample rates.** 250 sps (2016–2021 Centaur), 100 sps (2022 Centaur/Shake), 500 sps (2026
   Centaur) — compare peak amplitudes only after a common low-pass (e.g. 40 Hz) if high-frequency
   crackle dominates near-pad peaks.

## Next steps

1. Resolve decisions 1–5 above (catalog ids and coverage; KSC.xml gains; Gem presence pre-2026; bad-channel list).
2. Run notebook 20 over every catalog event with data (add a cache of per-event peak tables,
   keyed by `event_id`, written to `ensemble.yaml: output`), then fits by vehicle/pad (Fig. 3–4).
3. Event-time refinement notebook (airwave onset at the nearest station).
4. Port spectral-ratio and coupling estimators from Artemis II notebooks 42/50 into ksclib and run
   them over the ensemble.
5. Weather at launch time for every event (`ksclib.weather` once the New Glenn branch is merged).
