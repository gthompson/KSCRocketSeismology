# ksclib: KSC shared library

Shared code for the KSC rocket papers (Artemis II, New Glenn explosion, 2016–2026 ensemble).
Launch-agnostic signal processing lives in [flovopy](https://github.com/gthompson/flovopy)
(e.g. `flovopy.ingest.gem_overflow`); everything specific to KSC instruments, sites and
moving rocket sources lives here; everything specific to one event lives in that paper's YAML.

```bash
pip install -e ksclib          # from the repository root, in the flovopy_plus environment
```

```python
import ksclib
ev = ksclib.load_event("09_artemis2_paper/artemis2.yaml")
raw = ksclib.event_stream_raw(ev)              # master SDS + restored channels
st = ksclib.instrument_correct(raw, ev)        # Pa and m/s; Gem overflow repaired
stations = ksclib.station_table(ev)            # distance/azimuth from the event site
geo = ksclib.source_geometry(ev, "B29")        # source-time mapping along the trajectory
```

| Module | Contents |
|---|---|
| `event` | `Event` and `load_event`: origin time, site, windows, archive, responses, output folder |
| `data` | SDS access with per-file fallback, restored channels, `event_stream_raw` |
| `responses` | Centaur StationXML with the infraBSU stage; SmartSolo geophone PAZ |
| `correct` | `instrument_correct` for Trillium, infraBSU, Gem and SmartSolo |
| `geometry` | station table relative to the site; moving- or static-source geometry |
| `model` | gravity-turn trajectory and directional point-source model (was `rocket_infrasound_model`) |
| `centaur` | Centaur-only correction with a response-file fallback (earliest file after the event) and the Chaparral M25 stage |
| `physics` | sound speed (simple, Cramer 1993), standard atmosphere, weak-shock speed, wind along a ray (from AMOS-6) |
| `weather` | KSC weather-tower loading, wind vectors, height profiles, along-ray acoustic summary (from AMOS-6) |
| `pressure` | baseline-corrected pressure peaks and distance-reduced pressures (from AMOS-6) |
| `kml` | named points from KML files (from AMOS-6) |
| `clipping` | clipping found against a co-located unclipped reference sensor, and raw-count saturation |
| `surfacewaves` | Rayleigh dispersion (disba if installed, else a thin-layer solver), head-wave times, layer resonance |

Event kinds: `launch` (moving source along a trajectory and launch azimuth) and `static`
(source fixed at the site, e.g. an explosion on the pad). See `09_artemis2_paper/artemis2.yaml`
for a complete example, and `10_NewGlenn_paper/newglenn.yaml` for a static source.
The AMOS-6 ports are imported as submodules (`from ksclib import physics`) and take a ksclib `Event`
in place of AMOS-6's `project_config`.

Each paper folder stays thin (event YAML, numbered notebooks, LaTeX). At publication, copy the
paper folder and the `ksclib` version it used into a frozen release repository.

## Launch-catalog ensembles

`ksclib.catalog_events` turns a row of the launch catalog (`event_catalog_workflow_v5`) into an
`Event`, choosing the network *era* from the event time: `stationxml` eras (2016–2022 campaigns:
`03_stationxml/KSC.xml` for coordinates and responses, `/Volumes/classdata/remastered/SDS_KSC`)
or `centaur` eras (2026 network, configured as in `artemis2.yaml`). See
`07_ensemble_paper/ensemble.yaml`.

```python
from ksclib import catalog_events as ce
ens = ce.load_ensemble("07_ensemble_paper/ensemble.yaml")
cat = ce.load_catalog(ens)                       # sqlite events + extra_events, with vehicle/pad_code/era
ev = ce.event_from_row(cat.iloc[0], ens)
raw = ce.read_raw(ev); st = ce.correct(raw, ev)
peaks = ce.peak_amplitudes(st, ev, ce.station_table(ev), ce.clip_intervals(raw, ev))
```
