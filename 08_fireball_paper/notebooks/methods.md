## 3. Methods

### 3.1 Analysis overview

The analysis was designed to reconstruct the temporal evolution of the Falcon 9 accident using synchronized infrasound and seismic observations from the BCHH array. The workflow comprised: (1) correction of the instrumental responses and conversion to physical units; (2) compilation of surveyed source–receiver geometry and meteorological constraints; (3) manual identification and association of candidate airwave arrivals; (4) measurement of acoustic pulse morphology and signal-to-noise ratio; (5) estimation of back azimuth and apparent propagation speed using three-channel planar-wave coherence analysis; (6) comparison with a finite-range circular-wavefront model; and (7) measurement of acoustic pressure, seismic peak ground velocity, and their amplitude relationship.

All quantitative processing was performed on continuously recorded waveforms sampled at 250 Hz. The canonical analysis interval extended from 180 s before to 1800 s after the initial upper-stage explosion at 13:07:12.080 UTC.

### 3.2 Instrument calibration and response correction

The three seismic components were corrected using the manufacturer response for the Nanometrics Trillium Compact Posthole seismometer–Centaur digitizer combination. The combined sensitivity was \(3.0172\times10^8\) counts \((\mathrm{m\,s^{-1}})^{-1}\). The Centaur digitizer was operated on its 40 V peak-to-peak input range, corresponding to \(4.0\times10^5\) counts V\(^{-1}\) and an implied seismometer sensitivity of approximately 754 V \((\mathrm{m\,s^{-1}})^{-1}\).

The three infraBSU differential-pressure sensors were converted independently from counts to pressure using empirical, sensor-specific field calibrations. The adopted sensitivities were 8.10, 0.690, and 10.0 counts Pa\(^{-1}\) for HD1, HD2, and HD3, respectively. These factors were derived from comparative calibration experiments in which co-located infraBSU sensors were exposed to common pressure changes and impulsive signals. The calibrations should therefore be regarded as empirical field estimates rather than laboratory-traceable absolute calibrations.

For the infrasound channels, the median count level between 20 and 2 s before the initial explosion was removed before response correction. The empirical sensitivities were incorporated into complete instrument-response representations while retaining the nominal poles, zeros, and digitizer stages. Seismic traces were demeaned and linearly detrended. All traces received a 5% cosine taper before frequency-domain response removal.

A four-corner prefilter of 0.02, 0.05, 80, and 100 Hz and a water level of 60 dB were used to stabilize the response inversion. This prefilter was applied only as part of the response-removal operation; no additional Butterworth filtering was applied during event association, amplitude measurement, or array analysis. The corrected seismic channels are expressed as ground velocity in m s\(^{-1}\), and the corrected infrasound channels as differential pressure in Pa.

### 3.3 Source–receiver geometry

Sensor coordinates were obtained from the differential-GPS survey of BCHH and transformed to UTM Zone 17N for array calculations. Horizontal source–receiver distances and geographic azimuths were independently calculated on the WGS84 ellipsoid. The array reference position was the central broadband seismometer at approximately 541820.4 m E and 3160866.5 m N. The reference distance between SLC-40 and BCHH was 1417.9 m, and the back azimuth from the array toward SLC-40 was 199.4°, measured clockwise from north.

HD2 was used as the infrasound reference channel. The individual source-to-sensor distances were retained when calculating differential acoustic travel times. This avoided treating the approximately 30-m array as a single receiver during pick association and waveform alignment.

Approximate source times assigned to the major accident stages were obtained from the video chronology. These times were used to label and interpret key signals but were not required for constructing the general candidate-event catalogue, which was based on the observed infrasound arrivals.

### 3.4 Meteorological correction

Meteorological observations from the Kennedy Space Center tower network between 13:05 and 13:35 UTC were used to estimate the effective acoustic propagation speed. The selected dataset contained 84 temperature and 84 relative-humidity observations. Mean conditions were approximately 26.36 °C and 83.87% relative humidity.

The still-air sound speed was calculated as

\[
c_0 = 331.3 + 0.606T + 1.26h,
\]

where \(T\) is temperature in degrees Celsius and \(h\) is relative humidity expressed as a fraction. This yielded \(c_0=348.33\ \mathrm{m\,s^{-1}}\).

Wind observations were resolved into east and north components, averaged within 10-m height intervals, and linearly interpolated over the lowest 65 m of the atmosphere. The height-averaged wind component parallel to the SLC-40–BCHH propagation path was then added to the still-air sound speed:

\[
c_{\mathrm{eff}} = c_0 + \mathbf{u}\cdot\hat{\mathbf{r}}.
\]

The mean along-path wind component was \(+2.65\ \mathrm{m\,s^{-1}}\), giving an effective acoustic speed of \(350.98\ \mathrm{m\,s^{-1}}\). The corresponding travel time over 1417.9 m was 4.040 s, approximately 0.031 s shorter than the still-air estimate.

### 3.5 Baseline removal and manual arrival picks

Candidate airwave arrivals were initially identified by visual inspection using Antelope `dbpick`. Accepted picks were restricted to non-deleted phase-\(N\) arrivals on HD1, HD2, and HD3. The original pick precision was retained during export to the Python analysis workflow.

Slow variations in the infrasound baseline were removed with a centered, noncausal moving median. For each infrasound trace, a 251-sample window—approximately 1 s at 250 Hz—was used to estimate the baseline, which was then subtracted from the response-corrected pressure waveform. The three seismic channels were retained without this baseline operation. Because a centered median is nonlinear, it is not formally a zero-phase filter, but it introduces no systematic delay equivalent to that of a one-sided causal smoother.

The moving-median window was chosen after comparing unfiltered waveforms, high-pass-filtered waveforms, local linear baselines, and moving-median windows of several durations. High-pass filtering improved some weak arrivals but degraded broader pulses and altered their morphology. Local linear baselines were sometimes controlled by a small number of samples and introduced implausibly steep trends. The 1-s moving median provided the most stable baseline while preserving the short pressure impulses.

### 3.6 Reduced-time association of candidate events

Before association, each accepted pick was corrected for its expected differential travel time relative to HD2:

\[
t_{i,\mathrm{red}}
=
t_i-
\frac{r_i-r_{\mathrm{HD2}}}{c_{\mathrm{eff}}},
\]

where \(r_i\) is the SLC-40–sensor distance and \(c_{\mathrm{eff}}=350.98\ \mathrm{m\,s^{-1}}\). The resulting corrections were approximately 0.090 s for HD1, 0 s for HD2, and 0.013 s for HD3. These corrections were used only to associate likely corresponding arrivals; the final propagation direction and speed were estimated independently.

Reduced picks were sorted by time. Beginning with the earliest unassigned pick, all picks within the following 0.040 s were considered as one candidate cluster. At most one pick per channel was retained, selecting the pick closest to the cluster seed when multiple picks occurred on a channel. A cluster was accepted as a candidate event when it contained picks from at least two distinct infrasound channels. Picks that did not satisfy this criterion remained unassociated rather than being forced into an event.

A fixed six-channel waveform segment extending 0.20 s before to 0.30 s after each reduced event time was saved for subsequent analysis. The provisional time shifts were not written into these event streams; their original observed sample times were preserved.

### 3.7 Acoustic pulse measurements and candidate tiers

For initial pulse characterization, the three infrasound traces were shifted to the HD2 reference time using the meteorologically predicted differential delays and combined using a sample-by-sample median stack. A positive compression followed by a negative excursion was sought between −0.04 and +0.25 s relative to the reduced event time. The negative peak was required to occur between 0.010 and 0.180 s after the positive peak. When multiple pairs satisfied these conditions, the pair with the largest peak-to-peak pressure was selected.

For a positive peak at \(t_+\) and a negative peak at \(t_-\), provisional one-cycle bounds were defined as

\[
t_{\mathrm{start}}
=
t_+ - 0.5(t_- - t_+)
\]

and

\[
t_{\mathrm{end}}
=
t_- + 0.5(t_- - t_+).
\]

Noise was characterized over −0.40 to −0.10 s using the robust scale

\[
\sigma_{\mathrm{robust}}
=
1.4826\,\mathrm{median}\left(
|p-\mathrm{median}(p)|
\right).
\]

The initial stack SNR was the maximum absolute pressure within the event bounds divided by this noise scale. The positive–negative morphology was used as a measurement-quality diagnostic, not as the fundamental definition of an event. The principal explosion, for example, was retained despite failing the simple one-cycle morphology because it was an exceptionally strong, coherent multi-channel signal with a more complex pressure history.

Candidate labels based on channel support, reduced-pick span, and SNR were retained as descriptive quality indicators. They were not treated as distinct physical classes.

### 3.8 Eligibility for array analysis

Two configurable threshold sets were applied. The permissive analysis set required a median-stack peak-to-peak pressure of at least 10 Pa, stack SNR of at least 1.5, support from at least two channels, and a valid positive–negative measurement. The named principal explosion was explicitly retained despite failing the short-pulse morphology criterion.

A more conservative core subset required at least 25 Pa peak-to-peak pressure and SNR of at least 3, with the same channel-support requirement. These thresholds were used to distinguish the most readily interpretable events from additional candidates; they do not represent sharp natural boundaries between signal and noise.

### 3.9 Planar-wave array analysis

Back azimuth and apparent horizontal propagation speed were estimated jointly by shifting all three infrasound waveforms according to trial plane-wave models. Back azimuth was defined as the direction from the array toward the source, clockwise from north. For a trial back azimuth \(\theta\) and speed \(v\), the propagation vector toward the array was

\[
\mathbf{k}
=
\left[-\sin\theta,\,-\cos\theta\right],
\]

and the predicted delay at sensor \(i\), relative to HD2, was

\[
\Delta t_i
=
\frac{
(\mathbf{x}_i-\mathbf{x}_{\mathrm{HD2}})\cdot\mathbf{k}
}{v}.
\]

For each trial, the three traces were interpolated after applying the predicted delays and trimmed to the same common overlap. Thus, every point on the search surface was evaluated using the same waveform duration, avoiding the unequal-overlap bias that can favor zero lag in conventional cross-correlation.

Each aligned trace was median-centered and normalized by its RMS amplitude. Coherence was quantified using both three-channel semblance,

\[
S=
\frac{
\sum_t\left[\sum_i x_i(t)\right]^2
}{
N\sum_t\sum_i x_i^2(t)
},
\]

and the mean of the three pairwise correlation coefficients. The pairwise mean was mapped from \([-1,1]\) to \([0,1]\), and the joint score was

\[
C
=
0.60S+
0.40\left(\frac{\overline{\rho}+1}{2}\right).
\]

The coarse search covered back azimuths from 180° to 220° in 0.5° increments and speeds from 280 to 440 m s\(^{-1}\) in 2 m s\(^{-1}\) increments. Each coarse maximum was refined over ±2° in 0.1° increments and ±20 m s\(^{-1}\) in 0.5 m s\(^{-1}\) increments. Most events were scored over −0.04 to +0.18 s; the principal explosion used an extended interval ending at +0.35 s.

Pairwise correlations and residual lags were calculated after applying the best-fitting model. Lag closure,

\[
\tau_{12}+\tau_{23}+\tau_{31},
\]

was retained as a consistency diagnostic. The relative performance of HD1 was described by comparing the HD2–HD3 correlation with the mean of the two pairs containing HD1.

Solution stability was tested by shifting the scoring window by −0.008, 0, and +0.008 s and scaling its duration by 0.9, 1.0, and 1.1. The standard deviations of the resulting back azimuths and speeds were retained as empirical stability measures. Near-maximum widths at score reductions of 0.01 and 0.02 were also calculated, but these widths are descriptive properties of the coherence surface and not formal confidence intervals.

Composite coherence surfaces were constructed by combining the coarse surfaces for all analyzed events and for the core subset. Arithmetic-mean, median, maximum-score-weighted, and individually normalized mean composites were retained.

### 3.10 Finite-range circular-wavefront analysis

The plane-wave approximation was evaluated using exact source–receiver distances in the horizontal plane. For a trial source coordinate \(\mathbf{x}_s\) and propagation speed \(v\), the predicted relative delay was

\[
\Delta t_i
=
\frac{
\left|\mathbf{x}_i-\mathbf{x}_s\right|
-
\left|\mathbf{x}_{\mathrm{HD2}}-\mathbf{x}_s\right|
}{v}.
\]

Because receiver elevations were not available in the adopted geometry, this is strictly a two-dimensional circular-wavefront model rather than a full three-dimensional spherical-wave model.

The primary finite-range calculation held the source at SLC-40 and searched speeds from 280 to 440 m s\(^{-1}\) in 0.5 m s\(^{-1}\) increments. Coherence was calculated with the same waveform windows and scoring metric used for the planar solutions.

Source-position sensitivity was examined in coordinates oriented along and perpendicular to the SLC-40–BCHH path. Along-range offsets from −500 to +500 m and cross-range offsets from −150 to +150 m were evaluated while profiling over the complementary coordinate. These calculations were treated as resolution tests rather than source locations. Three sensors provide only two independent relative delays, so source easting, source northing, and propagation speed cannot be determined independently from these data. Open along-range coherence ridges were therefore interpreted as a fundamental range-resolution limitation.

### 3.11 Acoustic and seismic amplitude measurements

Acoustic and seismic amplitudes were measured for every candidate event using the saved baseline-corrected waveform segments. Event intervals were taken from the positive–negative pulse measurements, except for the principal explosion, for which a fixed −0.04 to +0.35 s interval was used.

For each seismic component, the median of the pre-event interval from −0.18 to −0.05 s was removed. Component PGV was the largest absolute ground velocity within the event interval. Three-component vector PGV was calculated as

\[
\mathrm{PGV}_{\mathrm{vec}}
=
\max_t\sqrt{
v_E^2(t)+v_N^2(t)+v_Z^2(t)
}.
\]

The maximum vector amplitude over the entire saved segment was also retained to test whether the acoustic event interval captured the largest seismic motion.

The infrasound traces were aligned to HD2 using the meteorological differential delays and combined as a median stack. Positive, negative, and peak-to-peak pressures were measured within the same event interval. Acoustic SNR was defined as stack peak-to-peak pressure divided by the robust pre-event noise scale.

Where pressure was reduced to a reference distance of 1 km, spherical geometric spreading was assumed:

\[
p_{\mathrm{red},1\,\mathrm{km}}
=
p_{\mathrm{obs}}\frac{r}{1000\ \mathrm{m}}.
\]

Peak sound-pressure level was calculated from the positive pressure peak as

\[
L_{\mathrm{peak}}
=
20\log_{10}
\left(
\frac{p_+}{20\ \mu\mathrm{Pa}}
\right).
\]

This quantity is explicitly a peak pressure level rather than an RMS sound-pressure level.

The dimensional acoustic-to-seismic amplitude ratio was calculated as peak-to-peak pressure divided by vector PGV, with units of Pa per m s\(^{-1}\). It was used as an empirical amplitude-coupling measure and should not be interpreted as an acoustic-to-seismic energy ratio.

### 3.12 Acoustic–seismic amplitude regression

Regression was restricted to events with seismic vector-PGV SNR of at least 5, acoustic peak-to-peak SNR of at least 5, and an event-window PGV at least 70% of the maximum PGV in the complete saved segment.

A free power-law model,

\[
p_{\mathrm{p2p}}=A\,\mathrm{PGV}^{\,b},
\]

was fitted by ordinary least squares after taking base-10 logarithms. A 95% descriptive interval for the exponent was estimated using 5000 nonparametric event bootstrap resamples. A proportional model,

\[
p_{\mathrm{p2p}}=K\,\mathrm{PGV},
\]

was also evaluated as a constant-ratio alternative. The two models were compared using root-mean-square residuals in base-10 logarithmic space. These fits describe the observed relationship and do not account for uncertainty in both axes, calibration covariance, or censoring near the noise floor.

### 3.13 Video and audio comparison

Public video recordings were used to identify major visible stages of the accident and to assign approximate source-time labels to the upper-stage explosion, principal lower-stage explosion, capsule impact, and subsequent capsule-related explosion. The current quantitative catalogue and array results remain derived from the BCHH geophysical data.

For the supplementary opening-sequence visualization, audio extracted from one YouTube recording was demeaned and band-pass filtered from 1 to 2 kHz using a four-pole zero-phase filter. Because the video did not contain an absolute timestamp, its timing was aligned empirically with the BCHH sequence. The audio timing and the source-reduced overview should therefore be treated as illustrative synchronization rather than an independent absolute timing observation.

### 3.14 Reproducibility

Each processing stage writes its numerical products, configuration parameters, intermediate event streams, and diagnostic figures to a dedicated output directory. The canonical workflow comprises the response-correction, input-preparation, meteorological, candidate-association, planar-array, circular-wavefront, acoustic–seismic amplitude, and paper-product notebooks. Event-filter decisions are retained for every candidate, including events that fail the permissive or core thresholds.

## Items still requiring confirmation

1. **Calibration provenance and uncertainty.** The adopted BCHH factors are clear, but the exact mix of lift tests, door-slam experiments, and other impulsive tests used to derive them should be verified from the original notes. The previously proposed ±20% pressure uncertainty is not encoded in the canonical notebooks and needs a documented basis.

2. **Principal-explosion pressure definition.** The current median-stack measurement is approximately \(+1353\) Pa, \(-84\) Pa, and 1437 Pa peak-to-peak. The earlier sensor-specific calculation gave a median positive peak of 1435 Pa and median negative peak of −219 Pa. The paper must distinguish these methods and choose one consistent headline quantity. I recommend sensor-specific positive peaks for absolute overpressure and the aligned median stack for catalogue comparisons.

3. **Back azimuth to SLC-40.** The current configuration gives 199.41°. Older text and derived products contain values near 199.0–199.9°. The final paper should use the value from one frozen geometry file throughout.

4. **Two acoustic speeds must not be conflated.** The meteorologically derived value is 350.98 m s\(^{-1}\). The approximately 366.5–366.8 m s\(^{-1}\) value used in the supplementary video/audio overview is an empirical display alignment and is not the atmospheric propagation estimate.

5. **Unused boundary-refinement configuration.** Notebook 04 sets `REFINE_BOUNDARIES_TO_NOISE=True`, but the adopted measurement function uses only the half-lag extension around the two peaks. Either remove the unused configuration or implement the refinement before describing return-to-noise boundaries.

6. **Event-filter thresholds.** The 10 Pa/1.5 SNR permissive thresholds and 25 Pa/3 SNR core thresholds are configurable divisions along continuous distributions, not data-defined discontinuities. The paper should describe them as operational thresholds.

7. **Circular versus spherical terminology.** With no elevation term, the adopted calculation is a horizontal circular-wavefront model. “Spherical” should be reserved for a later three-dimensional calculation or qualified explicitly.

8. **Video analysis.** The present workflow does not yet contain the full frame-by-frame synchronization shown in the 2017 AGU presentation. Camera locations, video identifiers, frame rates, synchronization procedures, and timing uncertainties must be added before claiming a quantitative video analysis.

9. **Energy and equivalent magnitudes.** Acoustic and seismic energy estimates and their equivalent magnitudes are not currently regenerated by the canonical notebook sequence. They should remain out of the Methods and Results until a reproducible energy notebook and output table are added.

10. **Source-time uncertainties.** The four named source times are stored, but formal uncertainties and the evidence supporting each time are not. The upper-stage onset appears to be the strongest video constraint; the other markers should be labeled approximate unless independently verified.

## Citation placeholders

The final bibliography should include citations for:

- Antelope and `dbpick`;
- ObsPy and its response-removal implementation;
- NumPy, SciPy, pandas, Matplotlib, and pyproj, according to the journal’s software-citation policy;
- the sound-speed temperature–humidity approximation;
- the KSC meteorological dataset or tower-network documentation;
- semblance and array/slowness analysis;
- the Trillium Compact Posthole and Centaur manufacturer responses;
- the infraBSU sensor design or calibration description;
- robust MAD scaling, if the journal expects a statistical-method citation;
- nonparametric bootstrap methods;
- each public video used for chronology, with access date and camera/location metadata where available.