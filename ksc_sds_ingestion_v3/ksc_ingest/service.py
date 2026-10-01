from __future__ import annotations
import shutil
from datetime import date
from pathlib import Path
import yaml
from .config import load_project, load_yaml, run_dir, master_sds, database_path
from .merge_sds_archives import merge_sds_archives, rollback_transaction

INSTRUMENT_DIRS = ("Centaur", "Gem", "SiliconAudio", "Guralp", "SmartSolo", "Pegasus")


def _run_id(start_date: str) -> str:
    return f"{start_date.replace('-', '')}_service"


def new_service_run(project_yaml, start_date, end_date=None, run_id=None):
    project = load_project(project_yaml)
    run_id = run_id or _run_id(str(start_date))
    root = run_dir(project, run_id)
    root.mkdir(parents=True, exist_ok=True)
    raw = root / "00_download"
    for name in INSTRUMENT_DIRS:
        (raw / name).mkdir(parents=True, exist_ok=True)
    (root / "10_conversion").mkdir(exist_ok=True)
    (root / "20_ingest").mkdir(exist_ok=True)
    (root / "30_qc").mkdir(exist_ok=True)
    cfg = {
        "service_run": {"id": run_id, "start_date": str(start_date), "end_date": end_date},
        "paths": {"raw": "00_download", "conversion": "10_conversion", "ingest": "20_ingest", "qc": "30_qc"},
        "sources": {
            "centaur": {"enabled": True, "input": "00_download/Centaur", "mode": "fast"},
            "gem": {"enabled": True, "raw": "00_download/Gem/raw", "converted": "10_conversion/Gem/mseed"},
            "silicon_audio": {"enabled": True, "input": "00_download/SiliconAudio"},
            "guralp": {"enabled": True, "input": "00_download/Guralp"},
            "smartsolo": {"enabled": True, "input": "00_download/SmartSolo"},
            "pegasus": {"enabled": False, "input": "00_download/Pegasus"},
        },
    }
    with (root / "service_run.yaml").open("w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return root


def load_run(project_yaml, run_id):
    project = load_project(project_yaml)
    root = run_dir(project, run_id)
    cfg, _ = load_yaml(root / "service_run.yaml")
    return project, cfg, root


def ingest_centaur(project_yaml, run_id, *, mode=None, dry_run=False, source=None):
    project, cfg, root = load_run(project_yaml, run_id)
    scfg = cfg.get("sources", {}).get("centaur", {})
    if not scfg.get("enabled", True):
        return {"status": "disabled", "instrument": "centaur"}
    src = Path(source) if source else root / scfg.get("input", "00_download/Centaur")
    if not src.exists():
        return {"status": "no_source", "instrument": "centaur", "source": str(src)}
    mode = mode or scfg.get("mode", "fast")
    target = master_sds(project)
    target.mkdir(parents=True, exist_ok=True)
    # Generic FLOVOpy merger keeps its own transaction DB/cache beside the master SDS.
    # KSC provenance can later mirror transaction IDs into ksc_archive.sqlite.
    summary = merge_sds_archives(src, target, mode=mode, dry_run=dry_run)
    return summary.as_dict()


def ingest_run(project_yaml, run_id, instruments=None, *, dry_run=False, centaur_mode=None):
    wanted = [x.lower() for x in (instruments or ["centaur"])]
    out = {}
    if "centaur" in wanted:
        out["centaur"] = ingest_centaur(project_yaml, run_id, mode=centaur_mode, dry_run=dry_run)
    # Other adapters are deliberately deferred until their real acquisition/conversion
    # workflows are finalized. Do not pretend that generic MiniSEED ingestion is correct.
    for name in wanted:
        if name != "centaur":
            out[name] = {"status": "not_implemented", "message": "Adapter intentionally deferred; raw download is preserved."}
    return out


def status(project_yaml, run_id):
    project, cfg, root = load_run(project_yaml, run_id)
    rows = []
    for key, scfg in cfg.get("sources", {}).items():
        rel = scfg.get("input") or scfg.get("raw")
        p = root / rel if rel else None
        rows.append({"instrument": key, "enabled": scfg.get("enabled", True), "path": str(p) if p else None, "exists": bool(p and p.exists())})
    return {"run": run_id, "run_dir": str(root), "master_sds": str(master_sds(project)), "sources": rows}
