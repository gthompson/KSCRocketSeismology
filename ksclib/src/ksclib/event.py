"""Event configuration: everything specific to one launch or explosion, loaded from YAML.

An event file names the source (time, site, kind), the data archive (via the
flovopy.ingest project file), the analysis windows, the channel groups, the
instrument-response locations and where products go. Paths may use
``~``, ``{base_dir}`` (the YAML file's folder), ``{repo_root}``, ``{project_root}``
and ``{run_dir}``; relative paths are taken relative to the YAML file.

Example (abridged)::

    name: Artemis II
    kind: launch                 # or "static" for a stationary source (explosion)
    origin_time: 2026-04-01T22:35:12
    site: {name: LC39B}          # looked up in stations.xls sheet `site_sheet`, or give lat/lon
    window: {pretrigger: 1800, duration: 900, posttrigger: 1800, trim_before: 30, trim_after: 270}
    ingest: {project_yaml: ../2026_ingest_service_runs/config/ksc.yaml, run_id: 20260403_service}
    stations: {file: ~/.../KSC_seismic_network_2016_2022.xls, sheet: artemis2, site_sheet: launchpads_2026}
    output: {dir: ~/.../writing/Artemis2, env: ARTEMIS2_OUT_DIR}
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from obspy import UTCDateTime

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CHANNEL_GROUPS = {
    "USF": ("1R", "*", "*", "D[DH]?"),        # Centaur: Trillium, infraBSU/Chaparral (read as D/C/H; see seedcodes)
    "BSU": ("1R", "*", "*", "HD?"),           # Gem infrasound loggers HDF/HDI (location '' or 10)
    "SmartSolo": ("1R", "*", "*", "DP?"),     # SmartSolo geophones
    "MSFC": ("DG", "*", "*", "C*"),           # Guralp and Silicon Audio (MSFC)
}
DEFAULT_SMARTSOLO_GEOPHONE = dict(f0=5.0, damping=0.7, sensitivity_mV_per_mps=76.7e3)


@dataclass
class Event:
    """A configured source and the data needed to study it."""
    name: str
    kind: str                               # "launch" (moving source) or "static"
    origin_time: UTCDateTime
    site_name: str | None
    site_lat: float
    site_lon: float
    pretrigger: float
    duration: float
    posttrigger: float
    trim_before: float
    trim_after: float
    project_yaml: Path
    run_id: str | None
    project: dict
    project_root: Path
    master_sds: Path
    run_dir: Path | None
    station_file: Path
    station_sheet: str
    site_sheet: str | None
    out_dir: Path
    channel_groups: dict
    centaur_response_dirs: list[Path] = field(default_factory=list)
    infrabsu_xml: Path | None = None
    infrabsu_channels: tuple = ("DD0", "DD1", "DD2")
    restored: dict[str, Path] = field(default_factory=dict)   # seed_id -> SDS root with recovered data
    seed_band_codes: bool = False   # rename Centaur D?? traces to SEED C??/H?? on read (see ksclib.seedcodes)
    smartsolo_geophone: dict = field(default_factory=lambda: dict(DEFAULT_SMARTSOLO_GEOPHONE))
    launch_azimuth_deg: float | None = None
    trajectory: dict = field(default_factory=dict)            # GravityTurnParameters overrides
    paths: dict[str, Path] = field(default_factory=dict)      # any other named paths
    raw: dict = field(default_factory=dict)                   # the YAML as loaded
    yaml_path: Path | None = None

    @property
    def starttime(self):
        return self.origin_time - self.pretrigger

    @property
    def endtime(self):
        return self.origin_time + self.duration + self.posttrigger

    @property
    def starttrim(self):
        return self.origin_time - self.trim_before

    @property
    def endtrim(self):
        return self.origin_time + self.trim_after


def _expand(value, subs, base_dir):
    if value is None:
        return None
    s = str(value)
    for k, v in subs.items():
        s = s.replace("{" + k + "}", str(v))
    p = Path(os.path.expanduser(s))
    return p if p.is_absolute() else (base_dir / p).resolve()


def load_event(yaml_path) -> Event:
    """Load an event configuration file."""
    from flovopy.ingest.config import load_project, master_sds, run_dir

    yaml_path = Path(yaml_path).resolve()
    base_dir = yaml_path.parent
    raw = yaml.safe_load(yaml_path.read_text())
    subs = {"base_dir": base_dir, "repo_root": REPO_ROOT}

    ing = raw.get("ingest", {})
    project_yaml = _expand(ing["project_yaml"], subs, base_dir)
    project = load_project(project_yaml)
    project_root = Path(project["_root"])
    run_id = ing.get("run_id")
    rdir = Path(run_dir(project, run_id)) if run_id else None
    subs.update(project_root=project_root, run_dir=rdir or project_root)
    P = lambda v: _expand(v, subs, base_dir)  # noqa: E731

    st = raw["stations"]
    station_file = P(st["file"])
    site = raw.get("site", {})
    lat, lon = site.get("lat"), site.get("lon")
    if lat is None or lon is None:
        import pandas as pd
        pads = pd.read_excel(station_file, sheet_name=st["site_sheet"]).set_index(st.get("site_column", "pad"))
        lat, lon = (float(x) for x in pads.loc[site["name"], ["lat", "lon"]])

    w = raw.get("window", {})
    out = raw.get("output", {})
    out_dir = Path(os.environ[out["env"]]).expanduser() if out.get("env") in os.environ else P(out["dir"])
    resp = raw.get("responses", {})
    src = raw.get("source", {})

    return Event(
        name=raw["name"], kind=raw.get("kind", "launch"), origin_time=UTCDateTime(str(raw["origin_time"])),
        site_name=site.get("name"), site_lat=float(lat), site_lon=float(lon),
        pretrigger=float(w.get("pretrigger", 1800)), duration=float(w.get("duration", 900)),
        posttrigger=float(w.get("posttrigger", w.get("pretrigger", 1800))),
        trim_before=float(w.get("trim_before", 30)), trim_after=float(w.get("trim_after", 270)),
        project_yaml=project_yaml, run_id=run_id, project=project, project_root=project_root,
        master_sds=Path(master_sds(project)), run_dir=rdir,
        station_file=station_file, station_sheet=st["sheet"], site_sheet=st.get("site_sheet"),
        out_dir=out_dir,
        channel_groups={k: tuple(v) for k, v in raw.get("channel_groups", DEFAULT_CHANNEL_GROUPS).items()},
        centaur_response_dirs=[P(d) for d in resp.get("centaur_dirs", [])],
        infrabsu_xml=P(resp.get("infrabsu_xml")),
        infrabsu_channels=tuple(resp.get("infrabsu_channels", ("DD0", "DD1", "DD2"))),
        restored={k: P(v) for k, v in raw.get("restored", {}).items()},
        seed_band_codes=bool(raw.get("seed_band_codes", False)),
        smartsolo_geophone={**DEFAULT_SMARTSOLO_GEOPHONE, **resp.get("smartsolo_geophone", {})},
        launch_azimuth_deg=src.get("launch_azimuth_deg"),
        trajectory=src.get("trajectory", {}) or {},
        paths={k: P(v) for k, v in raw.get("paths", {}).items()},
        raw=raw, yaml_path=yaml_path,
    )
