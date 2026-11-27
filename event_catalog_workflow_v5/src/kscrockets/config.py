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
    database: Path
    event_overrides: Path
    event_id_registry: Path
    metrics_index: Path
    website_output: Path
    analysis_output: Path
    launchpads: Path
    event_waveforms: Path
    website_title: str
    website_subtitle: str
    present: bool = False

    @property
    def interval(self) -> tuple[str, str]:
        """UTC start/end of the catalog interval (end = now when year_max is "present")."""
        start = f"{self.year_min}-01-01T00:00:00Z"
        if self.present:
            import datetime as _dt
            end = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            end = f"{self.year_max}-12-31T23:59:59Z"
        return start, end


def _year_max(value) -> tuple[int, bool]:
    if str(value).strip().lower() in {"present", "now", "today"}:
        import datetime as _dt
        return _dt.datetime.now(_dt.timezone.utc).year, True
    return int(value), False


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
    year_max, present = _year_max(cfg["project"]["year_max"])
    return Settings(
        root=root,
        year_min=int(cfg["project"]["year_min"]),
        year_max=year_max,
        raw_catalog=resolve(p["raw_catalog"]),
        canonical_catalog=resolve(p["canonical_catalog"]),
        database=resolve(p["database"]),
        event_overrides=resolve(p["event_overrides"]),
        event_id_registry=resolve(p["event_id_registry"]),
        metrics_index=resolve(p["metrics_index"]),
        website_output=resolve(p["website_output"]),
        analysis_output=resolve(p["analysis_output"]),
        launchpads=resolve(p["launchpads"]),
        event_waveforms=resolve(p["event_waveforms"]),
        website_title=cfg["website"]["title"],
        website_subtitle=cfg["website"]["subtitle"],
        present=present,
    )
