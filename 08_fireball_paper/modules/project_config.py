from __future__ import annotations

from pathlib import Path
import sys


def find_project_root(start: str | Path | None = None) -> Path:
    """Return the project root when called from the root or notebooks folder."""
    current = Path(start or Path.cwd()).resolve()
    if current.name == "notebooks":
        return current.parent
    return current


def add_modules_to_path(project_root: str | Path) -> Path:
    """Add the project's modules directory to sys.path and return it."""
    module_dir = Path(project_root) / "modules"
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
    return module_dir


def ensure_output_dirs(project_root: str | Path) -> dict[str, Path]:
    """Create and return the standard output directories."""
    project_root = Path(project_root)
    paths = {
        "outputs": project_root / "outputs",
        "derived": project_root / "outputs" / "derived",
        "figures": project_root / "outputs" / "figures",
        "response_correction": (
            project_root / "outputs" / "response_correction" / "final_products"
        ),
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
