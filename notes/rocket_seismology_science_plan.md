<!--
Shared scientific development plan for all rocket seismology papers.
Provided by Glenn Thompson on 2026-11-25. Every session working on AMOS-6, the
2016–2022 ensemble paper, Artemis II Papers 1 and 2, or New Glenn should read it.
It is a PLAN, not evidence that any analysis exists. See Section 11.
-->

# Rocket Seismology Papers — Scientific Development and Additional Analyses

This handover covers the scientific analyses, figures, methodology, validation and manuscript development. Authorship, funding and collaboration issues are out of scope.

## 1. Overall publication strategy

Five papers are at different stages of development:

1. **AMOS-6 Falcon 9 explosion (2016)**: submitted to Seismica in November 2026.
2. **2016–2022 ensemble paper**: historical seismo-acoustic observations of rocket launches at Kennedy Space Center and Cape Canaveral. Relatively early stage of development.
3. **Artemis II Paper 1**: network validation, instrument performance and recording requirements.
4. **Artemis II Paper 2**: acoustic source characterization, directivity, crackle and acoustic tracking.
5. **New Glenn static-fire explosion**: blast wave, air-to-ground coupling, seismic waves ahead of the airwave and subsurface velocity structure.

The revised plan prioritizes the 2016–2022 ensemble paper. Ideally it is submitted before the three papers based on the 2026 datasets.

The ensemble paper should establish:

- the long-term observational record;
- historical network development;
- instrumentation;
- the launch catalogue;
- a standardized processing methodology;
- first-order empirical relationships.

It should provide much of the context and a common reference for the other papers.

The three 2026 papers are already substantial working drafts. This document identifies additional analyses and improvements for them; it does not redesign their scope.

---

# 2. Analyses and metrics common to all papers

## 2.1. Standardize acoustic amplitude and exposure metrics

The AMOS-6 paper reported peak sound pressure level (SPL). The 2026 manuscripts do not yet report it consistently.

Add peak SPL as a standard measurement across the historical and 2026 datasets:

```
P_REF = 20e-6  # Pa

peak_pressure = np.max(np.abs(pressure))
peak_spl = 20 * np.log10(peak_pressure / P_REF)
```

For example:

| Peak absolute pressure | Peak SPL |
| ---------------------- | -------- |
| 10 Pa                  | 114.0 dB |
| 100 Pa                 | 134.0 dB |
| 500 Pa                 | 148.0 dB |
| 1,000 Pa               | 154.0 dB |
| 2,000 Pa               | 160.0 dB |
| 3,000 Pa               | 163.5 dB |
| 5,000 Pa               | 168.0 dB |

Report both the pressure in Pa and the peak SPL in dB.

Describe these as **band-limited, unweighted peak sound pressure levels**. State the effective measurement bandwidth and the processing.

Peak SPL is not the same as any of these:

- RMS SPL;
- sound exposure level;
- A-weighted sound levels;
- full-bandwidth measurements from conventional sound level meters.

Where appropriate, standardize the following acoustic metrics:

- Peak positive pressure.
- Peak negative pressure.
- Peak absolute pressure.
- Peak-to-peak pressure.
- Peak SPL.
- RMS pressure.
- Equivalent RMS sound pressure level over a defined interval.
- Sound exposure level (SEL).
- Integrated squared pressure.
- Signal duration.
- Pressure waveform skewness and kurtosis.
- Pressure derivative skewness and kurtosis.
- Dominant spectral frequencies.
- Acoustic energy in each frequency band.

SEL is particularly useful for comparing long-duration rocket launches with short-duration explosions, but it depends on the integration window.

Integrated squared pressure has units of Pa² s. Converting it to acoustic energy fluence requires assumptions about acoustic impedance and wave propagation.

For crackle analysis, calculate pressure-derivative statistics at comparable sampling rates, effective bandwidths and filtering. Differentiation amplifies high-frequency noise.

## 2.2. Standardize seismic amplitude metrics

Where reliable and appropriate, calculate:

- Peak ground velocity (PGV).
- Peak ground acceleration (PGA).
- Peak ground displacement (PGD).
- Measurements on the vertical and on each horizontal component.
- Horizontal vector amplitude.
- Three-component vector amplitude.
- RMS ground velocity.
- Integrated squared ground velocity.
- Amplitudes and energies in each frequency band.
- Spectral peaks.
- Signal duration.

State explicitly which PGV is meant: the maximum of the three-component vector magnitude, the largest single component, or a particular component.

Acceleration and displacement need suitable frequency limits, or differentiation and integration will amplify noise.

Use common measurement definitions across the papers wherever practical.

## 2.3. Consistent air-to-ground coupling measurements

Distinguish between:

- Peak velocity divided by peak pressure.
- RMS velocity divided by RMS pressure.
- Frequency-dependent pressure-to-velocity transfer functions.
- Ground displacement divided by pressure.
- Site-dependent ground compliance.
- Coherence between seismic and acoustic signals.
- Phase relationships between seismic and acoustic signals.

These metrics are related but not interchangeable. For example, independently measured peak pressure and peak ground velocity may occur at different times, so their ratio may not be an instantaneous physical coupling coefficient.

Calculate both broadband and frequency-dependent coupling where the data support it.

Examine whether coupling at each station repeats across different launches and explosions.

## 2.4. Common calibration and data-quality framework

Develop a consistent approach to:

- Instrument response removal.
- Empirical calibration.
- Gain errors.
- Polarity errors.
- Timing errors.
- Clipping and saturation.
- Gem logger overflow and recovery.
- Instrument installation and coupling effects.
- Effective bandwidth.
- Missing and unreliable channels.
- Validity periods for instrument corrections.
- Measurement uncertainty.

A versioned table of calibrations and station quality should underpin all the manuscripts.

Where possible, write reusable processing functions. Avoid separate, slightly different versions of the same measurement in each paper's notebooks.

---

# 3. Ensemble paper: 2016–2022 historical dataset

## 3.1. Scientific purpose

This should become the foundational paper for the rocket seismology research program at Kennedy Space Center and Cape Canaveral.

Its strength should be breadth and duration: systematic characterization of many launches, not detailed modelling of each one.

Potential title:

**Six Years of Rocket Seismology: Systematic Seismo-Acoustic Observations of Space Launches at Cape Canaveral, 2016–2022**

## 3.2. Network history and metadata

Document:

- How the network developed from 2016 to 2022.
- Station locations and deployment epochs.
- Changes to instrumentation.
- Seismometer and microbarometer types.
- Digitizers and recording configurations.
- Sampling rates.
- Sensor calibration procedures.
- Instrument response issues.
- Station relocations.
- When and where data are available.

Produce:

1. A historical network map.
2. A station operation timeline.
3. A station inventory table.
4. A figure of data availability by station and time.
5. A summary of available observations by launch and rocket type.

Incorporate the existing 1R network archive and its DOI where appropriate.

## 3.3. Historical launch catalogue

Finalize the historical launch catalogue. The broader catalogue lists about 195 launches; fewer will have usable, calibrated observations.

Clearly distinguish:

- All catalogued launches.
- Launches with waveform data.
- Launches with usable seismic data.
- Launches with usable infrasound data.
- Launches that meet the quality requirements for quantitative analysis.
- Launches observed at more than one station.

For each launch, include:

- Event identifier.
- Launch date and time.
- Rocket type.
- Launch pad.
- Mission.
- Landing information, where applicable.
- Source coordinates.
- Available stations and channels.
- Waveform availability.
- Data quality.
- Processing status.

Eventually archive the catalogue as a machine-readable research product with a DOI.

## 3.4. Anatomy of rocket launch signals

Produce representative examples of:

- Near-field launch signals.
- Intermediate-distance observations.
- More distant observations.
- Seismic signals that precede the acoustic arrivals.
- Ignition overpressure signals.
- Sustained rocket exhaust noise.
- Acoustic signals during ascent.
- Sonic booms.
- Booster landing signals, where available.

Use waveform and spectrogram examples to establish the terminology and the characteristic signal components that the later papers refer to.

## 3.5. Acoustic amplitude relationships

Calculate standardized acoustic amplitudes for the usable historical observations.

Examine:

- Peak pressure versus distance.
- Peak SPL versus distance.
- RMS pressure versus distance.
- Sound exposure versus distance.
- Variation between rocket types.
- Variation between launch pads.
- Differences with azimuth.
- Variability from event to event.
- Variability from site to site.
- Extreme amplitudes and their reliability.

Fit empirical attenuation relationships with uncertainties and residuals.

Take care when pooling observations from different rocket types, source trajectories, station configurations and calibration epochs. If there are enough observations, consider hierarchical or grouped regression.

## 3.6. Seismic amplitude relationships

Calculate:

- PGV.
- PGA.
- PGD.
- RMS ground velocity.
- Amplitudes on each component.

Examine how these depend on distance, rocket type and site.

Relate the seismic amplitudes to the acoustic amplitudes, and compare the seismic and acoustic attenuation exponents.

Consider whether air-to-ground coupling and local geology explain any apparent differences in seismic amplitude decay.

## 3.7. Air-to-ground coupling

This should be a major section of the ensemble paper.

Use the repeated launches to investigate:

- Whether coupling coefficients are stable at each station.
- How coupling varies spatially.
- Whether coupling depends on acoustic amplitude.
- Whether different rocket types produce different apparent coupling.
- Frequency-dependent coupling.
- The relative importance of site response and acoustic source characteristics.

Repeated observations make it possible to establish robust coupling statistics for each station. Report distributions and uncertainties, not only individual examples.

## 3.8. Spectral signatures and Doppler effects

Examine whether each rocket type has a characteristic spectral signature.

Potential analyses:

- Median spectra by rocket type.
- Spectral variability within each rocket type.
- Dominant frequencies.
- Spectral ratios.
- How the spectrum evolves with time.
- Changes in spectral peaks during ascent.
- First-order modelling of the Doppler shift.
- Dependence on station azimuth and source–receiver geometry.

This paper should establish first-order observations and interpretations. Leave detailed physical modelling of directivity and trajectory to the Artemis II acoustic source paper.

## 3.9. Historical research archive

Locate and preserve earlier:

- Conference presentations.
- Posters.
- Abstracts.
- Technical reports.
- Network documentation.
- Historical analyses.
- Research software.
- Original launch catalogues.

Where appropriate and permitted, archive these with persistent identifiers through Zenodo or a similar repository. Keep the original presentation dates separate from the later deposit dates.

Do not publicly archive proprietary reports or restricted materials without the appropriate permissions.

## 3.10. Expected ensemble paper figures

A possible figure sequence:

1. Historical network and launch pad map.
2. Network deployment and station availability timeline.
3. Launch catalogue statistics by year and rocket type.
4. Representative near-field and far-field waveforms and spectrograms.
5. Peak pressure and SPL versus distance.
6. PGV versus distance.
7. Amplitude relationships by rocket type.
8. Seismic versus acoustic amplitudes.
9. Distributions of coupling at each station.
10. Frequency-dependent coupling.
11. Representative spectral signatures by rocket type.
12. Spectral evolution and first-order Doppler modelling.

Keep this paper manageable. More sophisticated analyses can go into later publications.

---

# 4. Artemis II Paper 1: Network validation and recording requirements

## 4.1. Current scientific scope

The paper already covers:

- Gem logger overflow.
- Instrument cross-validation.
- Comparisons between broadband and nodal seismometers.
- Polarity and amplitude discrepancies.
- Instrument enclosure effects.
- Wind noise.
- Useful acoustic and seismic bandwidth.
- Sampling requirements.
- Geophone corner frequencies.
- Air-to-ground coupling.
- Recommendations for future deployments.

The major proposed addition: use the temporary nodal deployment much more systematically, as an independent reference for validating the permanent seismic network.

## 4.2. Identify every launch recorded during the nodal deployment

Determine the actual deployment and recovery dates of each nodal instrument, and cross-reference them against the launch catalogue.

One or more Falcon 9 launches probably occurred while the nodals were deployed for Artemis II. This has not yet been verified.

Identify every event that both a permanent station and a nearby or co-located nodal instrument recorded usable signals for.

Tabulate:

- Launch.
- Date and time.
- Rocket type.
- Permanent station.
- Reference nodal instrument.
- Distance between the two instruments.
- Available components.
- Recording quality.
- Usable common frequency band.

## 4.3. Empirical correction factors for permanent seismic stations

The co-located nodals give an independent way to evaluate the permanent broadband network. This is potentially one of Paper 1's most important contributions.

For each permanent–nodal pair, investigate:

- Timing offsets.
- Waveform correlation.
- Vertical polarity.
- Orientation of the horizontal components.
- Amplitude ratio on each component.
- PGV ratios.
- RMS amplitude ratios.
- Spectral amplitude ratios.
- Phase differences.
- Magnitude-squared coherence.
- Frequency-dependent transfer functions.
- Differences in instrument response and installation.
- Whether the amplitude ratios stay stable from launch to launch.

After the nominal instrument response is removed, define an empirical amplitude correction:

```
C(i,e) = A_nodal(i,e) / A_permanent(i,e)
```

where `i` is the station and `e` is the event. Calculate it for several amplitude metrics and frequency bands.

Do not automatically treat every amplitude difference as a calibration error in the permanent instrument. Differences can also come from:

- Uncertainty in the nodal response.
- Ground coupling.
- Instrument burial depth.
- Instrument orientation.
- The distance between the instruments.
- Local geological variability.
- Differences in frequency response.
- Signal-to-noise ratio.
- Nonlinear or amplitude-dependent instrument behaviour.

A ratio that is stable across several events and independent of frequency would be stronger evidence for a scalar gain correction. A frequency-dependent ratio may need a different interpretation or a frequency-dependent correction.

## 4.4. Independent validation using other launches

Do not derive correction factors from Artemis II and then present the improved agreement on Artemis II as independent validation.

If suitable Falcon 9 recordings exist:

1. Estimate the correction factors from Falcon 9 launches.
2. Apply them to Artemis II without refitting.
3. Measure the improvement in waveform agreement, amplitudes and spectra.
4. Compare the results before and after correction.

If there are enough events, use leave-one-launch-out cross-validation.

Alternatively, evaluate corrections derived from Artemis II on independently recorded Falcon 9 launches, allowing for differences in signal bandwidth and amplitude.

The aim is to test whether the corrections:

- repeat from launch to launch;
- are independent of the event;
- are independent of amplitude;
- are independent of frequency;
- stay stable between recording epochs.

This could help separate simple gain errors from nonlinear response, clipping, poor installation and more complicated frequency-response problems.

## 4.5. Develop a station calibration table

Create a versioned table containing:

- Permanent station and channel identifier.
- Reference nodal instrument.
- Distance between the instruments.
- Instrument configuration.
- Start and end dates of validity.
- Empirical gain correction.
- Polarity correction.
- Timing correction, where justified.
- Orientation correction, where justified.
- Valid frequency band.
- Number of comparison events.
- Variability between events.
- Estimated uncertainty.
- Quality flag.
- Evidence supporting each correction.

The other 2026 papers and future analyses of the permanent network should be able to use this table.

The seismic nodals cannot calibrate the pressure sensors directly. Infrasound calibration needs separate evaluation against appropriate pressure measurements.

## 4.6. Extend Gem validation

Investigate further:

- Overflow detection.
- Overflow correction.
- Errors remaining after correction.
- Amplitude and frequency limits.
- Waveform distortion.
- Comparison with research-grade microbarometers.
- Timing agreement.
- Effective dynamic range.
- Whether the repaired signals are good enough for peak amplitude measurements.
- Whether different levels of data quality suit different scientific uses.

Define quality criteria for accepting repaired Gem recordings. A Gem record may be usable for arrival timing or spectral analysis but unsuitable for quantitative peak pressure.

Make sure unreliable or incompletely recovered peak pressures do not produce misleading amplitude maps.

## 4.7. Incorporate the three MSFC permanent stations

Obtain waveform data and the relevant instrument metadata for the three MSFC stations.

Where usable, include them in:

- The network inventory.
- Instrument validation.
- Station maps.
- Amplitude measurements.
- Coupling analyses.
- Comparisons with nearby instruments.
- The overall assessment of network performance.

Their actual data availability and quality have not yet been established.

## 4.8. Additional figures

Potential additions:

1. Map of permanent–nodal station pairs.
2. Representative paired waveforms before and after correction.
3. Amplitude ratios for each station across several launches.
4. Spectral amplitude ratios and coherence.
5. Independent validation of the corrections.
6. Summary plot of the permanent-station correction factors and their uncertainties.
7. Gem overflow recovery and quality classification.
8. Updated network amplitude maps using only accepted data.

## 4.9. Existing manuscript issues to revisit

An earlier manuscript review found numerical claims that appeared to have no corresponding notebook output:

- A timing comparison of about 4 ms at B29.
- A reported value of 170 Pa.
- Correlation coefficients of about 0.94–0.95 after overflow repair.
- About 15 s of residual overflow.

Find and verify the analysis output behind each one, or remove or qualify the claim.

Also:

- Regenerate the station amplitude maps once the Gem quality issues are resolved.
- Complete the relevant Gem instrumentation citations.
- Examine the distinction between instrument response and enclosure or installation effects.
- Clarify the limits of generalizing recording requirements from a single heavy-lift launch.
- Make sure the quantitative recommendations follow directly from the data and the analysis bandwidth.

---

# 5. Artemis II Paper 2: Acoustic source, directivity, crackle and tracking

## 5.1. Current scientific scope

The paper currently covers:

- Acoustic amplitude decay.
- Seismic amplitude decay.
- Azimuthal amplitude variations.
- Arrival-time behaviour.
- Rocket trajectory modelling.
- Transformation into source emission time.
- Ignition overpressure.
- Acoustic directivity.
- Forward modelling of acoustic envelopes.
- Acoustic tracking with small arrays.
- Crackle.
- Spectral evolution.

The paper finds an empirical directivity maximum near 57° from the exhaust axis, replacing an initially assumed 30° radiation cone. This central result needs further validation and physical interpretation.

## 5.2. Peak SPL and PGV spatial maps

Restore the originally planned spatial maps of peak acoustic and seismic amplitudes:

1. Peak absolute pressure or peak SPL.
2. Peak ground velocity.
3. Apparent air-to-ground coupling.
4. Residuals between observed and model-predicted acoustic amplitudes.

Report both peak pressure and the corresponding peak SPL. A peak SPL map is just a logarithmic transform of the peak absolute pressure map, so full-sized maps of both may be unnecessary.

Show the individual station measurements prominently.

For contour maps:

- Avoid unsupported extrapolation beyond the network.
- Mask poorly constrained regions.
- Consider station spacing and interpolation uncertainty.
- Do not interpolate across large spatial gaps without appropriate qualification.
- Distinguish measured values from interpolated or model-predicted ones.
- Exclude unreliable or saturated channels.
- Where Paper 1 has independently validated station corrections, recalculate the seismic amplitudes with them.

The maps should exploit the unusually dense spatial coverage of the Artemis II deployment.

## 5.3. Spatial variability in coupling

Compare the spatial distribution of acoustic amplitudes with that of seismic amplitudes.

Investigate:

- Whether the two amplitude fields have similar spatial patterns.
- Whether local acoustic pressure largely explains the seismic amplitudes.
- Areas of anomalously strong or weak apparent coupling.
- Whether the anomalies correlate with station installation or local geology.
- Whether coupling factors from repeated historical launches at each station explain the observed seismic amplitudes.

Calculate spatially resolved coupling only where suitable pressure and seismic observations are close enough together.

## 5.4. Directivity versus propagation

The directivity analysis needs to distinguish between:

- The true source radiation pattern.
- Geometrical spreading.
- Changes in source strength during ascent.
- Atmospheric attenuation.
- Nonlinear propagation.
- Source height.
- Source–receiver distance.
- Rocket velocity.
- The changing emission angle.

Small emission angles may occur mainly later in the trajectory, at different source heights and distances. Directivity, source evolution and propagation can therefore trade off against each other.

Test whether the inferred radiation maximum stays stable with:

- Different attenuation assumptions.
- Different subsets of stations.
- Different trajectory parameters.
- Different source-strength histories.
- Different time intervals.

Give the directivity angle a confidence or sensitivity range, not a single optimum value.

## 5.5. Independent model validation

The empirical directivity model improves the timing fit between observed and predicted acoustic envelopes, which is encouraging. However, the amplitude observations that define the directivity and the timing observations that test it come from the same launch.

Investigate more independent validation:

- Fit with one subset of stations and validate with another.
- Fit with one azimuthal sector and evaluate another.
- Where physically appropriate, fit selected source-time intervals and evaluate independent ones.
- Check whether the conclusions hold for different station configurations.

Do not overstate how independent the validation is when the observables share the same underlying waveforms.

## 5.6. Acoustic envelope arrival times

Clarify the difference between the two apparent velocities reported earlier, about 127 m/s and 176 m/s. They apparently come from different peak-arrival or envelope measurements. Make the definitions explicit and consistent across the abstract, results and discussion.

Explain why the apparent propagation speed of peak amplitudes need not equal the physical speed of sound.

## 5.7. Rocket trajectory uncertainty

The manuscript uses a nominal, modelled trajectory. Quantify sensitivity to:

- Rocket position.
- Rocket altitude.
- Velocity.
- Acceleration.
- Gravity-turn parameters.
- Launch azimuth.
- Atmospheric sound speed.
- Winds.
- Assumptions about where the dominant acoustic source is.

Give uncertainty or sensitivity ranges for:

- emission times;
- emission angles;
- predicted arrival times;
- the inferred directivity.

Keep uncertainty in the rocket trajectory separate from uncertainty in atmospheric propagation.

## 5.8. Acoustic tracking using small arrays

Develop a more explicit uncertainty assessment for the two small arrays. Examine:

- Array geometry.
- Uncertainty in sensor coordinates.
- Timing precision.
- Coherence.
- Back-azimuth uncertainty.
- Apparent wave speed.
- Choice of time window.
- Dependence on frequency band.
- Atmospheric propagation assumptions.
- How sensitive the inferred source position is to back-azimuth errors.

Where possible, compare the independently inferred track with the nominal trajectory.

Do not overstate the source-location accuracy when the array geometry or the intersecting back azimuths constrain it only weakly.

## 5.9. Crackle and jet noise

Strengthen the analysis and its interpretation with the literature on rocket acoustics and volcanic jet noise.

Potential additional measurements:

- Pressure waveform skewness.
- Pressure waveform kurtosis.
- Pressure derivative skewness.
- Pressure derivative kurtosis.
- Shock rise times, where resolvable.
- Impulsiveness as a function of frequency.
- How crackle evolves with time.
- Dependence on distance.
- Dependence on emission angle.

Investigate whether the observations mainly reflect:

- Crackle generated at the source.
- Nonlinear steepening during propagation.
- Shock coalescence.
- Atmospheric attenuation.
- Changes in the rocket source during ascent.

These mechanisms may be hard to separate with the available measurements. State the limitations explicitly.

Relevant literature includes work by Kent Gee and Robin Matoza, particularly on rocket jet acoustics, directivity, crackle and volcanic jet noise.

## 5.10. Spatial model residuals

Calculate, for each station, the difference between observed and model-predicted acoustic amplitude:

```
Residual_dB = 20 * log10(P_observed / P_predicted)
```

Examine the residuals as functions of:

- Distance.
- Azimuth.
- Emission angle.
- Source height.
- Station location.
- Frequency.
- Source time.

Map the residuals. Determine whether systematic patterns point to deficiencies in the source model, the atmospheric propagation assumptions or the station measurements.

## 5.11. Existing manuscript issues to revisit

- Verify the statement that the station groups converge near a source time of about 100 s.
- Check and clarify the different apparent velocities.
- Expand the literature review on jet noise and directivity.
- Strengthen the uncertainty estimates for the directivity maximum.
- Assess the limitations of the nominal trajectory.
- Strengthen the interpretation of crackle.
- Check the supplement references. The manuscript reportedly refers to Tables S1–S2, but the supplement appeared to contain only Table S1.
- Regenerate the amplitude figures using accepted Gem recordings and validated seismic station corrections.
- Make the figures clearer and more consistent.

---

# 6. New Glenn static-fire explosion paper

## 6.1. Current scientific scope

The manuscript covers:

- Characterization of the acoustic blast wave.
- Origin-time estimation.
- Amplitude decay.
- Spectral attenuation.
- Air-to-ground coupling.
- Ground compliance.
- Seismic arrivals ahead of the airwave.
- Rayleigh and Love wave dispersion.
- Polarization.
- H/V measurements.
- Joint inversion for subsurface velocity structure.
- Comparisons with Artemis II and AMOS-6.

## 6.2. Peak SPL

Add peak SPL alongside peak absolute pressure. State the effective measurement bandwidth and any response limitations.

Where appropriate, distinguish:

- Peak positive overpressure.
- Peak negative pressure.
- Peak absolute pressure.
- Peak SPL.

Compare consistently defined acoustic amplitudes with AMOS-6 and Artemis II. Consider SEL or integrated squared pressure as additional comparison metrics.

Take care when comparing the peak amplitudes and integrated exposure of short explosions with those of sustained rocket launch noise.

## 6.3. Apply independently validated permanent station corrections

Where justified, use the empirical permanent-station corrections developed in Artemis II Paper 1. This is potentially an important link between the papers.

First, establish whether the permanent station configurations stayed the same between the Artemis II nodal deployment and the New Glenn explosion. Check for:

- Digitizer changes.
- Gain changes.
- Sensor changes.
- Re-levelling.
- Changes in instrument orientation.
- Changes in installation.
- Timing issues.
- Changes in response metadata.
- Other maintenance or hardware changes.

Do not apply correction factors outside their established validity periods without supporting evidence.

Where appropriate, recalculate:

- PGV.
- Other seismic amplitudes.
- Seismic-to-acoustic ratios.
- Ground compliance.
- Amplitude attenuation relationships.
- Uncertainty estimates.

Determine whether any published interpretation changes materially after correction.

## 6.4. Additional observations

If available and permitted, include usable recordings from the three MSFC stations. Additional stations could improve:

- Acoustic amplitude versus distance relationships.
- Spatial coverage.
- Origin-time estimation.
- Seismic arrival-time measurements.
- Dispersion measurements.
- Ground compliance comparisons.
- Assessment of directional variation.

Whether relevant additional recordings exist, and whether they are usable, has not yet been established.

## 6.5. Subsurface velocity structure

Strengthen the inversion of the Rayleigh and Love wave dispersion. Investigate:

- Trade-offs between model parameters.
- The trade-off between layer thickness and velocity.
- Sensitivity to the number of layers.
- Dependence on the starting model.
- Alternative acceptable models.
- Uncertainty bounds.
- Sensitivity to individual dispersion measurements.
- Sensitivity to the frequency range.
- Differences between inversions with and without H/V constraints.

Where practical, present an ensemble of acceptable models rather than only the single best-fitting one.

Compare the inferred structure with independent geological information:

- Published near-surface velocity models for Florida.
- Borehole information.
- Regional stratigraphy.
- Sediment thickness.
- Near-surface geophysical studies.
- Relevant studies around Cape Canaveral and Kennedy Space Center.

Clearly separate what the observations constrain from what the parameterization and assumptions impose.

## 6.6. Comparison with previous rocket-launch seismic studies

Revisit the comparison with Woo et al. and other studies of Artemis I seismic observations. The differences in inferred seismic group velocities could reflect differences in:

- Source mechanism.
- Propagation path.
- Frequency band.
- Surface-wave mode.
- Geological structure.
- Measurement method.
- Source type, moving or impulsive.

Do not attribute the discrepancies to a specific mechanism without sufficient evidence.

## 6.7. Repeatability of site-dependent ground compliance

At some stations, the compliance measured for New Glenn agrees with that measured for Artemis II. This is potentially important.

Extend the comparison using:

- Validated station calibration corrections.
- Other launches recorded by the same stations.
- Historical observations from comparable station configurations.
- Frequency-dependent transfer functions.
- Uncertainty estimates.

Determine whether the apparent compliance repeats across different source types and signal amplitudes.

Agreement across a few observations is evidence for repeatable, site-dependent compliance. Do not describe it as definitive proof of a universal site property.

## 6.8. Instrument diagnostics

Review every inferred instrument fault and anomalous channel against:

- Field notes.
- Instrument serial numbers.
- Digitizer configurations.
- Station metadata.
- Maintenance history.
- Comparisons with nearby stations.
- Permanent–nodal comparisons from Artemis II.

Separate demonstrable instrument faults from suspected ones.

## 6.9. Spatial amplitude maps

Depending on how many usable stations there are and where they are, consider maps of:

- Peak pressure or peak SPL.
- PGV.
- Air-to-ground coupling.
- Ground compliance.

The New Glenn network may be too sparse for defensible contour interpolation. If so, colour or scale the station symbols by the measured values instead of drawing continuous contours.

## 6.10. Novelty and interpretation

Qualify broad novelty claims appropriately. For example, the claim of the first observation at Kennedy Space Center of clearly separated seismic and acoustic wavefields may need to be limited to the available observational dataset, unless the literature supports a broader claim.

The separation of the seismic and acoustic wavefields is scientifically valuable, particularly for studying surface-wave dispersion and near-surface structure.

---

# 7. AMOS-6 paper — submitted

The AMOS-6 manuscript has been submitted. It should not become a major new development project unless revisions are required.

It can, however, serve as a methodological reference for the other papers. Relevant components include:

- High-amplitude infrasound calibration.
- Preparation of the pressure waveforms.
- Peak pressure and peak SPL.
- Event cataloguing.
- Independent timing constraints.
- Nonlinear acoustic propagation.
- Acoustic array processing.
- Relationships between seismic and acoustic amplitudes.
- Frequency-dependent pressure-to-velocity transfer functions.
- Acoustic energetics.
- Uncertainty and sensitivity analysis.

Once the ensemble paper is available, consider citing it in the AMOS-6 revision where appropriate.

Comparisons of peak SPL, pressure, coupling and acoustic energetics between AMOS-6 and the other papers must use compatible definitions. Acknowledge the differences in instrument bandwidth, calibration and processing.

---

# 8. Relationship between the papers

Keep a clear division of scientific scope:

| Topic                                       | Primary paper        |
| ------------------------------------------- | -------------------- |
| Historical network development              | Ensemble             |
| Long-term launch catalogue                  | Ensemble             |
| Systematic launch amplitude statistics      | Ensemble             |
| Rocket-type comparisons                     | Ensemble             |
| Repeated historical site coupling           | Ensemble             |
| First-order Doppler observations            | Ensemble             |
| Instrument validation                       | Artemis II Paper 1   |
| Permanent–nodal calibration                 | Artemis II Paper 1   |
| Independent calibration across launches     | Artemis II Paper 1   |
| Gem overflow and performance                | Artemis II Paper 1   |
| Recording and sampling requirements         | Artemis II Paper 1   |
| Detailed heavy-lift rocket amplitude fields | Artemis II Paper 2   |
| Detailed source directivity                 | Artemis II Paper 2   |
| Rocket trajectory modelling                 | Artemis II Paper 2   |
| Acoustic tracking                           | Artemis II Paper 2   |
| Crackle and jet noise                       | Artemis II Paper 2   |
| Explosion blast-wave physics                | AMOS-6 and New Glenn |
| Seismic waves ahead of the airwave          | New Glenn            |
| Rayleigh and Love wave dispersion           | New Glenn            |
| Subsurface velocity inversion               | New Glenn            |

Amplitude measurements, instrument descriptions and air-to-ground coupling will necessarily overlap between papers. Avoid duplicating whole analyses and figures, but let each paper contain the observations its own conclusions need.

Detailed analysis of the Artemis II seismic wavefield remains outside the main scope of the existing Artemis II manuscripts. It could form a separate future paper.

---

# 9. Reusable processing infrastructure

Where practical, develop common analysis code for the five papers. Potential reusable functions and modules:

## Acoustic measurements

- Peak pressure.
- Peak SPL.
- RMS pressure.
- Equivalent RMS SPL.
- Sound exposure level.
- Integrated squared pressure.
- Signal duration.
- Skewness and kurtosis.
- Pressure derivative statistics.
- Measurements in frequency bands.

## Seismic measurements

- PGV, PGA and PGD.
- Component and vector amplitudes.
- RMS amplitudes.
- Spectral measurements.
- Polarization.
- Measurements in frequency bands.

## Calibration and validation

- Permanent–nodal waveform comparisons.
- Lag estimation.
- Polarity detection.
- Orientation comparisons.
- Spectral amplitude ratios.
- Transfer function estimation.
- Coherence.
- Estimation of station corrections.
- Validation on independent events.
- Generating and applying the calibration table.

## Spatial analysis

- Station amplitude maps.
- Peak SPL maps.
- PGV maps.
- Coupling maps.
- Spatial interpolation with uncertainty and masking.
- Model residual maps.

## Catalogue integration

- Query launches by time interval.
- Identify launches that occurred during temporary deployments.
- Associate the available waveform data.
- Associate the instrument configuration epochs.
- Generate tables of measurements by station and event.
- Apply quality flags and validated calibration corrections.

Use the existing waveform processing and event catalogue infrastructure where possible, including EnhancedSDSClient and the relevant FloVoPy functionality. Avoid duplicating functions already implemented elsewhere.

---

# 10. Recommended order of implementation

## Priority 1 — Historical ensemble paper

- Finalize the historical launch catalogue.
- Reconcile the network and instrument metadata.
- Establish standardized measurement definitions.
- Generate the historical amplitude and spectral measurements.
- Develop the attenuation, coupling and rocket-type comparisons.
- Complete and submit the ensemble manuscript.
- Archive supporting datasets, historical presentations and software where appropriate.

## Priority 2 — Cross-launch validation of the permanent stations

This analysis benefits all three 2026 papers.

- Identify the nodal deployment intervals.
- Identify other launches recorded during those intervals.
- Find the permanent–nodal instrument pairs.
- Calculate waveform and spectral comparisons.
- Estimate empirical corrections.
- Validate the corrections independently.
- Produce a versioned calibration table.

## Priority 3 — Recalculate the 2026 measurement products

- Add peak SPL.
- Apply the validated seismic corrections.
- Update the acoustic quality classifications.
- Recalculate amplitudes and coupling.
- Include additional MSFC observations where available.
- Update the station maps and spatial amplitude maps.

## Priority 4 — Artemis II Paper 1

- Complete the instrument validation.
- Complete the evaluation of Gem overflow.
- Add the independent cross-launch calibration results.
- Strengthen the conclusions on recording requirements and network design.
- Resolve the outstanding numerical verification issues.

## Priority 5 — Artemis II Paper 2

- Complete the peak SPL and PGV maps.
- Develop the analysis of spatial model residuals.
- Improve the uncertainty and independent validation of the directivity.
- Examine sensitivity to the trajectory.
- Strengthen the uncertainty of the acoustic tracking.
- Expand the crackle and jet-noise analyses and literature review.

## Priority 6 — New Glenn

- Apply valid station corrections.
- Update the acoustic and seismic amplitude measurements.
- Strengthen the compliance analysis.
- Develop uncertainty and sensitivity tests for the velocity inversion.
- Expand the comparison with independent geological information.
- Improve comparisons with AMOS-6, Artemis II and other rocket seismology studies.

## Priority 7 — Manuscript and figure review

For all three 2026 papers:

- Verify every reported quantitative result against actual analysis output.
- Remove or qualify unsupported numerical claims.
- Make sure tables and figures are generated reproducibly.
- Make the figures more readable and consistent.
- Complete the literature reviews.
- Resolve internal manuscript comments and TODOs.
- Check cross-references between manuscripts and supplements.
- Use consistent definitions, units and terminology.
- Review uncertainty statements and scientific limitations.
- Make sure the conclusions do not overstate what the observations show.

---

# 11. Instructions for Claude

Treat this document as a scientific development plan, not as evidence that the proposed analyses have been done.

Before modifying any manuscript:

1. Inspect the latest source code, notebooks, analysis outputs, figures, tables and LaTeX files.
2. Determine which proposed analyses already exist, which need modifying and which must be implemented from scratch.
3. Identify reusable functionality in the existing codebase.
4. Verify the actual deployment dates and waveform availability.
5. Keep observed results, model predictions and proposed analyses distinct.
6. Do not invent numerical results, uncertainties, calibration factors, event counts or manuscript conclusions.
7. Make sure every quantitative manuscript claim can be traced to a reproducible analysis output.
8. Preserve the scientific scope of each paper unless there is a compelling reason to restructure it.

The highest-value new analysis is probably the use of several independently recorded launches to derive and validate empirical corrections for the permanent seismic stations, using the co-located nodals. That calibration exercise is potentially a substantial new scientific contribution. Adding peak SPL, by contrast, is largely a straightforward extension of existing amplitude measurements.

The highest-priority manuscript is now the historical 2016–2022 ensemble paper.

The most straightforward additions across the existing 2026 manuscripts are standardized peak SPL measurements and improved spatial maps of acoustic and seismic amplitudes.

This handover consolidates earlier discussions; it is not a fresh audit of the manuscript archives or analysis repositories. Check the manuscript issues identified earlier against the latest versions before making any changes.
