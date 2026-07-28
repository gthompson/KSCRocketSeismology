
"""YAML-backed project configuration and notebook output namespaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError("PyYAML is required: python -m pip install pyyaml") from exc


def discover_project_root(start: str | Path | None = None) -> Path:
    start_path = Path(start or Path.cwd()).resolve()

    for candidate in (start_path, *start_path.parents):
        if (candidate / "config" / "project.yml").exists():
            return candidate

    if start_path.name == "notebooks":
        return start_path.parent

    return start_path


def _resolve(project_root: Path, value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value

    path = Path(value).expanduser()
    return path if path.is_absolute() else (project_root / path).resolve()


@dataclass(frozen=True)
class ProjectConfig:
    project_root: Path
    raw: dict[str, Any]

    @property
    def paths(self) -> dict[str, Any]:
        return self.raw.get("paths", {})

    @property
    def products(self) -> dict[str, str]:
        return self.raw.get("products", {})

    @property
    def analysis(self) -> dict[str, Any]:
        return self.raw.get("analysis", {})

    def path(self, key: str, *, required: bool = False) -> Path | None:
        if key not in self.paths:
            if required:
                raise KeyError(f"Missing paths.{key} in config/project.yml")
            return None
        resolved = _resolve(self.project_root, self.paths[key])
        if required and resolved is not None and not resolved.exists():
            raise FileNotFoundError(f"Configured path does not exist: {resolved}")
        return resolved

    def product(self, key: str, *, required: bool = False) -> Path:
        if key not in self.products:
            raise KeyError(f"Missing products.{key} in config/project.yml")
        resolved = _resolve(self.project_root, self.products[key])
        if required and not resolved.exists():
            raise FileNotFoundError(f"Required upstream product does not exist: {resolved}")
        return resolved


@dataclass(frozen=True)
class NotebookContext:
    config: ProjectConfig
    code: str
    slug: str
    output_dir: Path
    data_dir: Path
    figure_dir: Path
    log_dir: Path
    overwrite_existing: bool

    @property
    def project_root(self) -> Path:
        return self.config.project_root

    def coded_name(self, name: str | Path) -> str:
        name = Path(name).name
        prefix = f"{self.code}_"
        return name if name.startswith(prefix) else prefix + name

    def data_path(self, name: str | Path, *, overwrite: bool | None = None) -> Path:
        return self._output_path(self.data_dir, name, overwrite=overwrite)

    def figure_path(self, name: str | Path, *, overwrite: bool | None = None) -> Path:
        return self._output_path(self.figure_dir, name, overwrite=overwrite)

    def log_path(self, name: str | Path, *, overwrite: bool | None = None) -> Path:
        return self._output_path(self.log_dir, name, overwrite=overwrite)

    def _output_path(
        self,
        directory: Path,
        name: str | Path,
        *,
        overwrite: bool | None,
    ) -> Path:
        path = directory / self.coded_name(name)
        allow_overwrite = self.overwrite_existing if overwrite is None else bool(overwrite)
        if path.exists() and not allow_overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing notebook output: {path}\n"
                "Set outputs.overwrite_existing: true in config/project.yml "
                "or pass overwrite=True deliberately."
            )
        return path


def load_project_config(
    config_file: str | Path | None = None,
    *,
    start: str | Path | None = None,
) -> ProjectConfig:
    root = discover_project_root(start)

    if config_file is None:
        config_path = root / "config" / "project.yml"
    else:
        config_path = Path(config_file).expanduser()
        if not config_path.is_absolute():
            config_path = (root / config_path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Project configuration not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    configured_root = raw.get("project", {}).get("root")
    if configured_root:
        configured_path = Path(configured_root).expanduser()
        root = (
            configured_path.resolve()
            if configured_path.is_absolute()
            else (config_path.parent / configured_path).resolve()
        )

    return ProjectConfig(project_root=root, raw=raw)


def notebook_context(
    notebook_name: str,
    *,
    config_file: str | Path | None = None,
    start: str | Path | None = None,
) -> NotebookContext:
    config = load_project_config(config_file, start=start)

    stem = Path(notebook_name).stem
    match = re.match(r"(?P<code>S?\d+)[_-](?P<slug>.+)", stem)
    if not match:
        raise ValueError(
            f"Notebook name must begin with a numerical code: {notebook_name}"
        )

    code = match.group("code")
    slug = match.group("slug")
    namespace = f"{code}_{slug}"

    output_root_value = config.raw.get("outputs", {}).get("root", "outputs")
    output_root = _resolve(config.project_root, output_root_value)
    output_dir = output_root / namespace
    data_dir = output_dir / "data"
    figure_dir = output_dir / "figures"
    log_dir = output_dir / "logs"

    for directory in (output_dir, data_dir, figure_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    overwrite = bool(
        config.raw.get("outputs", {}).get("overwrite_existing", False)
    )

    return NotebookContext(
        config=config,
        code=code,
        slug=slug,
        output_dir=output_dir,
        data_dir=data_dir,
        figure_dir=figure_dir,
        log_dir=log_dir,
        overwrite_existing=overwrite,
    )


def ensure_output_dirs(
    project_root: str | Path | None = None,
    notebook_code: str | None = None,
) -> dict[str, Path]:
    """
    Backward-compatible helper.

    New notebooks should prefer notebook_context(). Existing notebooks can call
    this function while they are being migrated.
    """
    root = discover_project_root(project_root)
    if notebook_code:
        namespace = str(notebook_code)
        output_dir = root / "outputs" / namespace
    else:
        output_dir = root / "outputs"

    derived = output_dir / "data"
    figures = output_dir / "figures"
    response_correction = root / "outputs" / "01_correct_bchh_instrument_response_refactored" / "data"

    for directory in (output_dir, derived, figures, response_correction):
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "outputs": output_dir,
        "derived": derived,
        "figures": figures,
        "response_correction": response_correction,
    }
