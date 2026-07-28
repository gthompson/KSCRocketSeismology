# Falcon 9 paper — remaining tasks for `main8.tex`

## Priority 1 — analyses needed before scientific claims can be finalized

- [ ] **Reimplement the legacy polarization workflow in Python.**
  - Recover the MATLAB/GISMO implementation and document the original filter band, moving-window length, overlap, covariance/eigenvalue conventions, coordinate orientation, rectilinearity, planarity, ellipticity, azimuth, and incidence-angle definitions.
  - Validate the Python attributes against selected archived MATLAB outputs and simple synthetic three-component signals.
  - Apply quality masks in low-amplitude windows.
  - Consider broadband and selected frequency-band products.

- [ ] **Reassess the payload/capsule interval.**
  - Regenerate rectilinearity, planarity, ellipticity, particle-motion, and polarization-direction time series.
  - Determine whether a direct seismic impact phase can be separated from the dominant ground-coupled airwaves.
  - Reconstruct the video-derived apparent ground-contact time and its uncertainty.
  - Only reconsider the legacy 885–1186 m/s apparent P-wave-speed estimate if both a defensible source time and a direct seismic arrival are recovered.
  - Update the Methods, Results, Discussion, tables, captions, and conclusions accordingly.

- [ ] **Reassess the prolonged continuous signal.**
  - Confirm its presence and amplitude on HD1, HD2, and HD3 as well as all three seismic channels.
  - Compare it with synchronized video to test the sustained launch-pad-fire interpretation.
  - Use polarization and particle motion to describe the observed wavefield without prematurely assigning P-, S-, or Rayleigh-wave components.
  - Update the overview figure, Results, Discussion, and Conclusions.

- [ ] **Regenerate the synchronized four-panel forensic visualization in Python.**
  - Use the exact public-video identifier and document its source.
  - Include time-referenced video, scrolling six-channel waveforms, a magnified waveform window, and scrolling polarization attributes.
  - Document frame rate, synchronization offset, acoustic-time reduction, filtering, and timing uncertainty.
  - Decide whether audio alignment is illustrative or can be made quantitatively defensible.
  - Check redistribution rights; if redistribution is restricted, archive the rendering script and exact source citation instead of the source video.

- [ ] **Freeze and summarize the modern Python catalogue and array products.**
  - Finalize permissive and core event selections.
  - Generate event-by-event back azimuth, apparent speed, coherence, and stability results.
  - Reconcile the modern results with the legacy 44-event median values.
  - Populate the array-results subsection and its figure.

- [ ] **Complete the finite-range circular-wavefront results.**
  - Report the fixed-SLC-40 best-fitting speed and coherence.
  - Compare planar and circular-wavefront solutions.
  - Generate along-range and cross-range sensitivity plots.
  - Explain the open along-range ridge and range-resolution limitation.

- [ ] **Complete the pressure–PGV regression.**
  - Freeze the accepted event sample.
  - Report the power-law coefficient and exponent, bootstrap interval, proportional-model constant, residual scatter, and sample size.
  - Generate the paper figure and update Results and Discussion.

- [ ] **Recover and verify the legacy energy calculations.**
  - Inspect the original MATLAB routines.
  - Document integration windows, pressure/velocity quantities, density, wave-speed, geometry, spreading, radiation assumptions, and component/sensor treatment.
  - Recompute or independently check the 1030 MJ acoustic energy, 7.8 MJ seismic energy, and equivalent magnitudes 2.88 and 1.46.
  - Decide whether these remain main-text results or move to supplementary material.

## Priority 2 — catalogue, chronology, figures, and tables

- [ ] **Populate phase amplitudes from the frozen catalogue.**
  - Phase 2 peak-pressure range/value.
  - Phase 3 peak-pressure range/value.
  - Phase 4 peak-pressure range/value.
  - Verify event counts, phase boundaries, durations, final-event time, and maximum event rate.

- [ ] **Populate the principal-events table.**
  - Include selected onset events, principal explosion, tentative payload/capsule interval, and first/last events of later phases.
  - Distinguish direct measurements from interpretations.
  - Include timing uncertainty and data provenance where appropriate.

- [ ] **Reconcile all event times.**
  - Separate source times, observed arrival times, reduced times, and video-derived times.
  - Resolve the roles of 13:07:12.080 UTC, 13:07:15.75 UTC, and figure-relative reference times.
  - Apply one consistent convention to text, tables, captions, and supplementary products.

- [ ] **Regenerate the paper figures from the frozen workflow.**
  - Site/array map with final labels.
  - Thirty-minute overview with final phase boundaries and continuous-signal annotation.
  - Initial event waveforms with final calibration and measurements.
  - Opening-sequence figure; decide whether it belongs in the main paper or supplement.
  - Principal-explosion waveform figure with consistent sensor-specific and median-stack annotations.
  - Payload/capsule interval after polarization/video reassessment.
  - Event-catalogue summary.
  - Array results.
  - Finite-range results.
  - Pressure–PGV regression.
  - Integrated forensic chronology.
  - Polarization/particle-motion figure(s).

- [ ] **Create supplementary derived-data products.**
  - Response-corrected six-channel waveform excerpts.
  - Regularly sampled polarization attributes.
  - Particle-motion products for key intervals.
  - Full 153-event catalogue.
  - Synchronized forensic movie.
  - Prefer NetCDF/ASDF or a well-documented table as the authoritative polarization product; optional MiniSEED exports should include sidecar metadata defining channel codes, formulas, units, windows, filters, and coordinate conventions.

## Priority 3 — calibration, metadata, and uncertainty

- [ ] **Recover calibration provenance.**
  - Confirm which of the 25 infraBSU sensors were included in the comparative tests.
  - Confirm lift-test procedure and expected pressure step.
  - Confirm door-slam or other impulsive tests.
  - Determine whether routine rocket launches contributed to calibration or validation.
  - Verify the basis for the ±20% absolute pressure uncertainty.
  - Add laboratory huddle-test details for the seismometer only if supported by records.

- [ ] **Verify deployment metadata.**
  - Confirm the 24 February 2016 deployment date.
  - Confirm April 2016 sensor moves and the exact configuration operating on 1 September.
  - Confirm FIRE and TANK locations and whether they need mention or display.
  - Confirm StationXML response epochs and coordinates used by the Python workflow.

- [ ] **Quantify detection and timing limits.**
  - Define what “no detectable energetic precursor” means relative to noise and array sensitivity.
  - Confirm the 37 h pre-event and 10.5 h post-event search intervals.
  - Document manual-pick uncertainties and video synchronization uncertainties.
  - Avoid claiming that the precursor search excludes weak, slow, internal, aseismic, or otherwise undetectable processes.

## Priority 4 — manuscript edits already signaled in `main8.tex`

- [ ] Remove `TO DO` from the `Analysis overview` subsection heading after the workflow language is finalized.
- [ ] Replace the placeholder `Polarization and particle-motion results TO DO` heading and text once the Python analysis is complete.
- [ ] Add the missing reproducibility paragraph covering:
  - Python polarization code;
  - derived polarization data and metadata;
  - particle-motion products;
  - synchronized-video rendering script;
  - video identifier, timing offset, frame-rate handling, filters, and window definitions;
  - redistribution limitations.
- [ ] Update the `Interpretation and provenance` subsection so it explicitly states that polarization analysis is still pending and will become authoritative only after Python validation.
- [ ] Replace all future-tense and provisional statements once products are frozen.
- [ ] Check that “153 events” always refers specifically to the impulsive infrasound catalogue and does not include the prolonged continuous signal or tentative payload/capsule interpretations.
- [ ] Maintain cautious terminology:
  - “payload- or capsule-related activity,” not confirmed impact;
  - “prolonged continuous signal,” not seismic-only tremor;
  - no P/S/Rayleigh attribution until reproduced;
  - no near-surface P-wave speed until the phase and source time are defensible.

## Priority 5 — references, authorship, archive, and submission details

- [ ] Add references on rocket seismo-acoustics and launch monitoring.
- [ ] Add and verify software citations for Antelope, `dbpick`, GISMO, ObsPy, NumPy, SciPy, pandas, Matplotlib, pyproj, and the archival repository.
- [ ] Add citations for KSC meteorological data, instrument responses, infraBSU calibration information, public videos, and the official SpaceX investigation.
- [ ] Confirm whether additional Buncefield, Beirut, Moerdijk, mining-blast, volcanic-explosion, or rocket-monitoring references are needed.
- [ ] Add ORCID identifiers and confirm the corresponding-author address.
- [ ] Complete and verify CRediT author contributions.
- [ ] Complete acknowledgements, funding, KSC support, deployment assistance, weather-data providers, SpaceX wording, and site access.
- [ ] Create the persistent data/code archive and replace repository placeholders with DOI citations.
- [ ] Verify permissions and citation requirements for every video, image, map layer, and supplementary movie.
- [ ] Finalize data and code availability language after the archive contents are fixed.

## Final quality-control pass

- [ ] Compile LaTeX and resolve all missing references, labels, citations, overfull boxes, and figure paths.
- [ ] Confirm consistency of SI units, significant figures, time formats, source/arrival-time terminology, SLC-40 naming, and US/UK spelling.
- [ ] Cross-check every number in the abstract, tables, captions, Results, Discussion, and Conclusions against a frozen output file.
- [ ] Remove internal notes such as `TBD`, `TODO`, “will be regenerated,” “reserved,” and “before final submission.”
- [ ] Ensure the abstract remains within the journal word limit after final numerical updates.
- [ ] Confirm that direct observations, derived quantities, video associations, legacy MATLAB results, and physical interpretations are clearly distinguished throughout.
