# Scientific review of the Falcon 9 manuscript and supplement

## Assessment

The dataset supports a worthwhile close-range seismo-acoustic case study. The strongest contributions are the calibrated local pressure record, the separation of catalogue transients from physical explosions, and the comparison of pressure with ground motion. The restraint in the regional non-detection and single-station phase interpretation is appropriate.

**I would resolve the confirmed catalogue and measurement-definition inconsistencies before submission.** They do not demonstrate that the central observations are wrong, but they affect reproducibility and several claims of robustness. This is a scientific and source-level review of `main37.pdf` and `supplement37.pdf`, checked against their LaTeX sources and selected saved workflow products. The complete waveform processing and 48-hour visual screen were not rerun. Recalculations below use the saved catalogue and measurement CSVs; they are audit results, not replacement publication products.

The accompanying version 38 sources implement the requested display-item change and associated reference repairs. They deliberately retain the scientific results pending resolution of this review. Page numbers below refer to the supplied version 37 PDFs.

## Confirmed inconsistencies requiring correction

### 1. Phase counts do not match the stated phase windows

**Location:** main §4.1, pp. 7–8 and Figure 2; supplement S3, p. 6, and the complete event table, pp. 19–22.

Both documents specify Phase I as 13:07:11.91–13:08:21.91, Phase II as 13:14:05–13:15:55, Phase III as 13:19:02–13:25:00, and Phase IV as 13:29:39–13:34:54 UTC. The main paper assigns 48, 4, 96, and 5 transients to those phases.

I selected catalogue entries using those exact bounds, converting the final catalogue’s DD2-referenced arrivals to source time with 1408.3384567/351 seconds. The results are:

| Interval | Published count | Count within the stated source-time bounds | Catalogue event numbers |
|---|---:|---:|---|
| Phase I | 48 | 39 | 1–39 |
| Phase II | 4 | 4 | 54–57 |
| Phase III | 96 | 90 | 58–147 |
| Phase IV | 5 | 6 | 148–153 |
| Outside these intervals | Not accounted for in the partition | 14 | 40–53 |

This is visible directly in the supplement: event 48 occurs about 144 seconds after the first catalogue arrival, whereas the stated Phase I duration is 70 seconds. It cannot be fixed by the approximately four-second acoustic reduction or rounding.

The public 2017 abstract contains the historical 48/4/96/5 cluster counts.[1] The current configuration explicitly calls its phase intervals “broad overview annotations” rather than catalogue assignments. This suggests two different definitions have been combined, although their exact history still needs confirmation.

**Required action:** choose whether phases are exhaustive catalogue groups or descriptive plotting intervals. Generate membership and counts from the authoritative catalogue using that definition. If the current windows remain, report the 14 intervening transients explicitly. Update the overview caption, abstract/summary wording about four phases if necessary, and relevant figure annotations. Do not simply extend the 70-second Phase I transfer-analysis interval: that interval is separately used to construct seven 10-second H1 segments.

### 2. The “principal explosion excluded” regression retains another measurement of that explosion

**Location:** main §4.3, p. 13 and Figure 8; supplement S5, p. 14.

Notebook 100 sets `PRINCIPAL_EXPLOSION_EVENT_NUMBER = 13` and removes only that row in the exclusion test. Event 14 remains. Events 13 and 14 are 0.073 seconds apart, have overlapping measurement windows, and have effectively identical stack pressure amplitudes of 1465.7909 Pa. Their vector PGVs are 3.5745×10⁻³ and 3.4049×10⁻³ m/s. Both are included in the 46-entry regression.

Recomputing ordinary least squares from the saved CSV gives:

| Audit fit | Entries | Slope | R² |
|---|---:|---:|---:|
| Published selection | 46 | 0.962230 | 0.952557 |
| Remove event 13 only | 45 | 0.958416 | 0.937069 |
| Remove events 13 and 14 | 44 | 0.943381 | 0.904944 |

The last result remains broadly compatible with a near-proportional descriptive relationship, but it is **not** a substitute for a new confidence interval or a complete complex-level sensitivity analysis. The published calculation does not establish the claim that the physical principal explosion has been excluded.

**Required action:** define physical/overlapping complexes consistently, exclude the whole principal complex, and bootstrap at complex level. Audit other overlapping entries as well. Retain the present fit as an entry-level descriptive result if desired, with an accurate label. Avoid reporting 46 independent physical events.

### 3. The pressure statistic in S5 does not describe the regression implementation

**Location:** supplement S5 opening, p. 11; main §3.3 and Figure 8; generated complete-event table.

S5 says peak-to-peak pressure is the median of individual sensor measurements, “not the amplitude of a median-stacked waveform.” That is correct for the named-event pressure summary, but it contradicts Notebook 100’s catalogue/regression calculation. The code aligns the three pressure traces, computes a sample-wise median stack, and takes its maximum minus minimum inside the event window. The regression uses `acoustic_stack_peak_to_peak_pa`. The complete-event table correctly calls its pressure an aligned-stack amplitude.

These quantities are not interchangeable: `median(max(p_i)−min(p_i))` generally differs from `max(median(p_i))−min(median(p_i))`.

**Required action:** distinguish the catalogue/regression stack statistic from the named-event sensor-median statistic in both Methods and captions. A suitable formulation is: “Catalogue and regression pressures are peak-to-peak amplitudes of the differentially aligned median stack; named-event pressures are medians of the independently measured channel amplitudes.” Confirm the same distinction for any pressure-to-PGV ratio presented in prose.

### 4. The regression selection is less stringent than “complete amplitude capture” implies

**Location:** main §3.3; supplement quality table and S5.

The code requires pressure-stack SNR ≥5, vector-PGV SNR ≥5, and capture fraction ≥0.70. The fraction is the event-window PGV divided by the PGV in the full short segment, not a proof that the complete physical event was captured. The minimum fraction among the selected saved rows is approximately 0.763.

**Required action:** publish the three numerical criteria and the exact capture definition. Replace “complete amplitude capture” with the actual criterion. A sensitivity at a stricter capture threshold would show whether under-captured seismic peaks affect the slope. Explain that the full comparison segment is itself only about 1.1 seconds long, so this check does not establish capture of a long seismic coda.

### 5. Claims of independent transfer estimates contradict the Methods

**Location:** main §3.3, p. 7 versus §4.3 and Figure 9, pp. 13–15; supplement S5.

The Methods correctly say that event and continuous Phase I estimates overlap and are complementary rather than independent. The Results and Figure 9 caption then call them independent. Both analyses reuse the same instruments and some of the same signal energy; the continuous estimate has only seven nonoverlapping 10-second segments. An input-energy-weighted event estimator can also be strongly influenced by the principal complex.

**Required action:** use “complementary event-window and continuous estimates” consistently. Preserve the existing dominant-event exclusion and weighting sensitivities: those tests are more informative than an independence claim. State that frequency-wise permutation thresholds are pointwise unless a simultaneous-band test has actually been performed. Treat significant narrow bins and robust broad response bands separately.

### 6. Named-event identifiers and PGV provenance need an explicit mapping

**Location:** main Table 2 (Table 1 in version 38), supplement complete-event table, and saved named-event match product.

The nearest-arrival matching product maps the upper-stage event to catalogue event 1 and the principal explosion to event 14. Notebook 100’s special principal-event constant instead identifies event 13. The main table’s upper-stage PGV, 7.85×10⁻⁵ m/s, matches catalogue event 2, whereas event 1 has 1.3347×10⁻⁴ m/s. This does not prove that the named-event PGV is incorrect: a separately chosen named-event window could explain it. The provenance is insufficiently explicit to tell.

**Required action:** provide a small machine-readable mapping of physical label, source-time convention, associated catalogue rows, and pressure/PGV integration windows. Trace every named-event table value to that mapping. Distinguish a representative catalogue peak from the physical event complex; automatic nearest-time association should not silently determine the scientific label.

## Methodological qualifications to strengthen

### 7. Make the energetics uncertainty explicit at the result

**Location:** main §4.4 and Conclusions; supplement S1 and S5.

The distinction between radiated acoustic energy and explosive yield is sound and should remain. I verified that 1390 Pa corresponds to about 156.84 dB re 20 µPa, and 2.2×10⁹ J corresponds to about 526 kg TNT as an energy-unit conversion.

The DD1–DD3 range is sensor dispersion, not the full uncertainty of the hemispherical estimate. A common ±20% pressure scaling alone multiplies energy by 0.64–1.44; applied to 2.2×10⁹ J, that is approximately 1.41–3.17×10⁹ J. This illustrative range is not a confidence interval and excludes geometric, propagation, window, and frequency-response uncertainty. Common calibration errors do not disappear by taking a median across three sensors.

A second issue is the conversion from local pressure to total radiated energy. The formula assumes a progressive-wave relationship between pressure and intensity and an adopted angular radiation pattern. Near-ground reflections, source directivity and obstacles may affect the pressure sampled at one azimuth. Explicitly call this a **hemispherical-equivalent acoustic-energy estimate under the stated model**, and say whether ground reflection is accounted for or remains unresolved. The existing 2π/4π sensitivity does not by itself capture all receiver reflection effects.

The 1-second moving-median subtraction is nonlinear and signal dependent. “0.05–80 Hz processed passband” describes the instrumental processing bounds, not a complete transfer function for that baseline operation. Preserve the baseline-window sensitivity and, preferably, quantify its effect on integrated energy as well as peak pressure for the principal event. Do not infer a broadband yield from these numbers.

### 8. Treat array speed uncertainty as geometry-dependent, not just window repeatability

**Location:** main §§2.1, 4.3 and 5.2; supplement S4.

The unresolved-range conclusion is appropriate. With only three sensors, direction and apparent horizontal speed are much better posed than simultaneous source range and speed. However, the 0.41 m/s principal-event window sensitivity and the 3.85 m/s population dispersion omit the stated 1–2 m location uncertainty across a roughly 30 m aperture. That systematic uncertainty matters when interpreting differences of a few m/s.

**Recommended action:** perturb reconstructed sensor positions within defensible bounds and repeat direction/speed estimation. Report that sensitivity separately from scoring-window stability. Also distinguish horizontal trace velocity from actual wave speed; incidence angle can raise trace velocity even in linear propagation. Agreement near 351–352 m/s supports direct acoustic propagation but is not a precise independent thermometer or a decisive test of a Mach excess of order 0.006.

### 9. The weak-shock calculation is correct as a conditional consistency test

**Location:** main §5.2; supplement S5 and Figure S8.

The stated normal-shock relation agrees with the standard pressure-jump equation.[2] Using 1390 Pa, 101325 Pa, γ=1.4 and the saved meteorology gives M≈1.005862 and ground-relative speed ≈353.019 m/s, consistent with the manuscript.

The inference should remain conditional: a measured positive pressure peak does not independently establish that a resolved shock front was recorded. Instrument bandwidth, baseline processing, reflection, and the difference between peak pressure and front pressure jump matter. Prefer “If interpreted as a normal-shock pressure jump, the measured peak corresponds to…” over “the pressure implies a shock.” Keep the inward 1/r extrapolation as sensitivity only; the manuscript’s warning that it is not a source inversion is essential.

The historical public AGU record verifies the 153-event chronology and earlier cluster counts, but its abstract does not establish the specific historical no-shock conclusion. Archive or cite the exact slide/report passage supporting that claim rather than relying solely on the abstract landing page.[1]

### 10. Clarify which timing comparisons are independent

**Location:** main §§3.4, 4.2 and 5.1; supplement S2, S5 and S7.

The distinction between observed arrival, differential reduction and inferred source time is well constructed. The 1419.9 m seismometer path and 1408.3 m DD2 path give different travel times; the documents now identify them properly.

The camera’s UTC is anchored to the upper-stage chronology, so agreement at that anchor is not an independent absolute timing validation. The genuinely useful checks are relative delays of later features, independently recorded acoustic arrivals, and consistency of physical labels. Replace broad “independently consistent” wording with a precise statement of those tests.

Report an uncertainty budget that separates sample interval, manual picking, video frame interval, synchronization, source position/height, meteorological modelling and possible early nonlinear propagation. The working sound-speed approximation in S2 and `physics.py` needs a citation or validation over the relevant temperature/humidity range, particularly if agreement within 1 m/s is emphasized. Relative intervals can be more precise than absolute source UTC, but do not automatically cancel source-dependent propagation effects.

For S7, preserve the conservative single-station interpretation. Label the table times explicitly as seconds after the adopted upper-stage source time. Clarify that the +3.45 s cutoff precedes the **principal source onset** at +3.6006 s; it is not the expected principal acoustic arrival at the receiver. The causal-filter versus zero-phase range is a sensitivity envelope, not a confidence interval on phase velocity.

### 11. Precursor and regional conclusions should remain observational

**Location:** main Abstract, §§3.2, 4.1 and 5.1; supplement S3 and S6.

The clearer precursor sentence is readable, and the body appropriately specifies a visual multichannel impulse screen. Keep that qualification close to the Results. It does not establish absence of all precursory processes or a calibrated amplitude detection threshold. A useful addition would be a representative pre-event background panel or amplitude/noise summary, with frequency band and channel dependence; this could go in the supplement.

For the Bartlett screen, the 99.5th empirical percentile is estimated from only 153 background windows. It is therefore controlled by approximately the two largest observations and should not be interpreted as a precisely calibrated 0.5% false-alarm probability, especially across 17,839 overlapping searched windows. The current emphasis on subsequent review is appropriate; document background duration, comparable search grids, and threshold stability.

The regional candidate handling is appropriately cautious. Preserve the rejection of an inferred common branch without coherent moveout. The post-hoc pseudo-p value is descriptive, not formal confirmatory evidence. There is no need to convert these unconfirmed packets into a period–yield estimate.

## Literature and interpretation checks

The numerical pressure/velocity comparison with Novoselov et al. is reasonable: the reported velocity transfer coefficients are approximately 1.99–2.74 µm/s/Pa, comparable in scale to the reciprocal of the manuscript’s median pressure/PGV ratio.[3] The differences in frequency band, signal definition, site and geometry remain important; numerical similarity does not identify the same coupling mechanism or yield a transferable universal coefficient.

The 93 ms engineering timeline is documented in the NASA-hosted SpaceX anomaly update.[4] Keeping it as external context, rather than evidence that the seismograms diagnose a COPV mechanism, is appropriate. The historical report’s reuse of the same calibration is provenance, not a statistically independent calibration experiment.

## Presentation and submission checks

The principal scientific figures should stay in the main manuscript. Moving the instrument table is a sensible way to satisfy the display-item limit without weakening the evidence sequence. Seismica explicitly counts figures and tables together and sets a ten-item main-text limit.[5]

The published plots have several smaller issues worth fixing during the scientific revision: the Figure 4 normalization note overlaps the right end of the bottom trace; Figure S14 has crowded/marginal map annotations; and the full event table needs clear definitions of Q, S_p and S_v in its caption or immediately adjacent text. Figure S16’s caption says a focused onset measurement is “used in the main paper,” although the detailed measurement is now confined to the supplement. Reconcile that description.

The version 38 builds retain some overfull-line warnings and old font-package warnings; compilation success is not a declaration of final publication layout. The installed class loads a 10-point base class. Check Seismica’s submission checklist, which asks for 12-point text, line numbers and double spacing, before generating submission PDFs.[6] The DOI/repository placeholders also need completion. These are production matters, distinct from the scientific findings above.

## Changes implemented in version 38

| Material | Version 37 | Version 38 |
|---|---|---|
| Instrument geometry/calibration | Main Table 1 | Supplementary Table S1 |
| Opening-event measurements | Main Table 2 | Main Table 1 |
| Quality definitions | Supplementary Table S1 | Supplementary Table S2 |
| Named-event energetics | Supplementary Table S2 | Supplementary Table S3 |
| Complete event measurements | Supplementary Table S3 | Supplementary Table S4 |
| Regional candidates | Supplementary Table S4 | Supplementary Table S5 |
| Focused onset results | Supplementary Table S5 | Supplementary Table S6 |

All nine main figures and all 21 supplementary figures retain their numbering. The main now has **9 figures + 1 table = 10 display items**. The instrument table’s numbers and caption are preserved; only its location and float placement change. The supplement’s two literal references to main Table 2 now point to main Table 1. Label-based supplementary references renumber automatically.

The complete-event input already contains its own label and longtable counter. Removing the redundant wrapper counter/label eliminates the duplicate-label warning and duplicate table destination. No generated table data were modified. Both documents were compiled with the existing class, bibliography, figures and generated event table, through stable cross-references. The relocated table and renumbered main table were visually checked. Original version 37 files were not modified.

## Sources and audit evidence

1. Thompson et al. (2017), [USF record of the AGU presentation](https://digitalcommons.usf.edu/geo_facpub/2182/). Supports historical chronology and cluster counts; the displayed abstract does not contain the detailed weak-shock conclusion.
2. NASA Glenn, [Normal Shock Wave Equations](https://www.grc.nasa.gov/WWW/K-12/airplane/normal.html). Pressure-jump relation used for the conditional numerical check.
3. Novoselov, Fuchs and Bokelmann (2020), [Acoustic-to-seismic ground coupling](https://ucrisportal.univie.ac.at/en/publications/acoustic-to-seismic-ground-coupling-coupling-efficiency-and-infer/), Geophysical Journal International 223, 144–160, DOI 10.1093/gji/ggaa304.
4. SpaceX, [Anomaly Updates, 2 January 2017, archived by NASA](https://sma.nasa.gov/LaunchVehicle/assets/anomaly-updates-spacex.pdf).
5. Seismica, [Author Guidelines](https://seismica.library.mcgill.ca/author-guidelines), checked for the combined display-item limit.
6. Seismica, [Submission Checklist](https://seismica.library.mcgill.ca/libraryFiles/downloadPublic/27).

Local evidence: the supplied `main37.pdf` and `supplement37.pdf`; matching LaTeX sources; `data/outputs/030_reconcile_manual_event_catalogues/final_153_event_catalogue.csv`; Notebook 100 and its `event_acoustic_seismic_amplitudes.csv`, `named_event_catalogue_matches.csv`, `pressure_pgv_regression_summary.csv`, `pressure_pgv_regression_sensitivity.csv`, `event_amplitude_coupling_summary.json` and `acoustic_energetics_metadata.json`; Notebook 040’s background-window and beamforming definitions; Notebook 140 and its onset summary; `modules/project_config.py`, `modules/physics.py`, the weather acoustic summary and the generated complete-event table. All are in the provided local workflow repository. An audit script and CSV outputs accompany this review so the phase counts and regression comparisons can be repeated without rerunning waveform processing.
