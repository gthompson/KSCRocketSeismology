"""Per-year archives of the event waveform products, for Zenodo (or Box) and the published site.

    ksc-rockets package-waveforms                  # -> <out_root>/archive/ksc_event_waveforms_<YYYY>.zip

Zenodo allows 100 files per record, so the 361+ events go into one zip per year, each holding
``<event_id>/`` with ``raw_counts.mseed`` (as recorded; independent of StationXML),
``corrected.mseed`` (Pa, m/s), ``manifest.json`` (parameters, StationXML, code version),
``stations.csv``, ``metrics.csv`` and ``onsets.csv``. ``files_index.csv`` lists every file with its
size and SHA-256. Once uploaded, put each zip's download URL in
``data/curated/waveform_urls.csv`` (key = year) and run ``ksc-rockets build-site --web``; the event
pages then link there.
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pandas as pd

EVENT_FILES = ("raw_counts.mseed", "corrected.mseed", "manifest.json", "stations.csv", "metrics.csv", "onsets.csv")
README = """KSC rocket seismo-acoustic event waveforms, {year}

One folder per catalog event (event ids as in the KSC rocket event catalog):
  raw_counts.mseed  raw counts as recorded, catalog time -900 s to +900 s (miniSEED, Steim2)
  corrected.mseed   instrument response removed: Pa (pressure), m/s (seismic), float32
  manifest.json     processing parameters, network era, StationXML, code version, warnings
  stations.csv      stations with coordinates, distance and azimuth from the source
  metrics.csv       per-channel metrics (peak, SPL, SEL, PGV, SNR, band energies, ...)
  onsets.csv        STA/LTA onsets and origin-time estimates
Run: {runs}
Amplitudes of corrected.mseed and metrics are provisional until the StationXML gains are final;
raw_counts.mseed does not depend on them.
"""


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def package_waveforms(out_root, dest=None, years=None) -> pd.DataFrame:
    """Write one zip per year from <out_root>/<YYYY>/<event_id>/ folders; returns the file index."""
    out_root = Path(out_root).expanduser()
    dest = Path(dest).expanduser() if dest else out_root / "archive"
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for ydir in sorted(p for p in out_root.iterdir() if p.is_dir() and p.name.isdigit() and len(p.name) == 4):
        if years and ydir.name not in {str(y) for y in years}:
            continue
        events = sorted(p for p in ydir.iterdir() if p.is_dir() and (p / "manifest.json").exists())
        if not events:
            continue
        zpath = dest / f"ksc_event_waveforms_{ydir.name}.zip"
        runs = set()
        tmp = zpath.with_suffix(".zip.part")
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for ev in events:
                try:
                    import json
                    runs.add(json.loads((ev / "manifest.json").read_text()).get("run_id", ""))
                except Exception:
                    pass
                for name in EVENT_FILES:
                    f = ev / name
                    if f.exists():
                        # miniSEED is already compressed (Steim2 / float32 does not shrink much): store it
                        ctype = zipfile.ZIP_STORED if name.endswith(".mseed") else zipfile.ZIP_DEFLATED
                        z.write(f, f"{ev.name}/{name}", compress_type=ctype)
                        rows.append(dict(year=ydir.name, event_id=ev.name, file=name, archive=zpath.name,
                                         bytes=f.stat().st_size, sha256=_sha256(f)))
            z.writestr("README.txt", README.format(year=ydir.name, runs=", ".join(sorted(r for r in runs if r))))
        tmp.replace(zpath)
    index = pd.DataFrame(rows, columns=["year", "event_id", "file", "archive", "bytes", "sha256"])
    index.to_csv(dest / "files_index.csv", index=False)
    return index
