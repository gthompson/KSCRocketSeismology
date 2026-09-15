from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import tomllib

@dataclass(frozen=True)
class Settings:
    root: Path
    year_min: int
    year_max: int
    raw_catalog: Path
    canonical_catalog: Path
    metrics_index: Path
    website_output: Path
    analysis_output: Path
    launchpads: Path
    website_title: str
    website_subtitle: str


def load_settings(config_path: str | Path | None = None) -> Settings:
    if config_path is None:
        root = Path.cwd()
        config_path = root / "config" / "default.toml"
    else:
        config_path = Path(config_path).expanduser().resolve()
        root = config_path.parent.parent
    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)
    p = cfg["paths"]
    resolve = lambda x: (root / x).resolve()
    return Settings(
        root=root,
        year_min=int(cfg["project"]["year_min"]),
        year_max=int(cfg["project"]["year_max"]),
        raw_catalog=resolve(p["raw_catalog"]),
        canonical_catalog=resolve(p["canonical_catalog"]),
        metrics_index=resolve(p["metrics_index"]),
        website_output=resolve(p["website_output"]),
        analysis_output=resolve(p["analysis_output"]),
        launchpads=resolve(p["launchpads"]),
        website_title=cfg["website"]["title"],
        website_subtitle=cfg["website"]["subtitle"],
    )
