#!/usr/bin/env python3
"""
inventory_matfiles.py

Inventory MATLAB .mat files without requiring MATLAB.

Supports:
  - MATLAB v7.3 MAT files via h5py/HDF5
  - Older MATLAB MAT files via scipy.io.whosmat/loadmat
  - Graceful failure for unsupported/corrupt/proprietary objects

Outputs:
  - CSV summary
  - JSON summary
  - Markdown report

Usage:
  python inventory_matfiles.py /Users/thompsong/Library/CloudStorage/Box-Box/thompsong/3_Project_Documents/NASAprojects/201602_Rocket_Seismology/matlab/data --pattern "*.mat" --out /Users/thompsong/mat_inventory
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def human_bytes(n: Optional[int]) -> str:
    if n is None:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"


def is_hdf5(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(8) == b"\x89HDF\r\n\x1a\n"
    except OSError:
        return False


def safe_shape(obj: Any) -> str:
    shape = getattr(obj, "shape", None)
    if shape is None:
        return ""
    return "x".join(str(x) for x in shape)


def safe_dtype(obj: Any) -> str:
    dtype = getattr(obj, "dtype", None)
    return "" if dtype is None else str(dtype)


def matlab_class_from_attrs(attrs: Any) -> str:
    for key in ("MATLAB_class", b"MATLAB_class"):
        if key in attrs:
            value = attrs[key]
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            if hasattr(value, "tobytes"):
                try:
                    return value.tobytes().decode("utf-8", errors="replace").strip("\x00")
                except Exception:
                    return str(value)
            return str(value)
    return ""


def inventory_hdf5_mat(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    import h5py

    rows: List[Dict[str, Any]] = []
    notes: List[str] = []

    with h5py.File(path, "r") as f:
        def visit(name: str, obj: Any) -> None:
            if name.startswith("#refs#"):
                return

            kind = "group" if hasattr(obj, "keys") else "dataset"
            nbytes = None
            if kind == "dataset":
                try:
                    nbytes = int(obj.size * obj.dtype.itemsize)
                except Exception:
                    nbytes = None

            rows.append({
                "file": path.name,
                "path": name,
                "variable": name.split("/")[0],
                "kind": kind,
                "matlab_class": matlab_class_from_attrs(obj.attrs),
                "python_class": type(obj).__name__,
                "shape": safe_shape(obj),
                "dtype": safe_dtype(obj),
                "bytes": nbytes,
                "size_human": human_bytes(nbytes),
            })

        f.visititems(visit)

    return rows, notes


def inventory_old_mat(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    from scipy.io import whosmat, loadmat

    rows: List[Dict[str, Any]] = []
    notes: List[str] = []

    try:
        info = whosmat(path)
    except Exception as exc:
        return [], [f"scipy.io.whosmat failed: {exc}"]

    for name, shape, matlab_class in info:
        nbytes = None
        pyclass = ""
        dtype = ""

        try:
            data = loadmat(path, variable_names=[name], squeeze_me=False, struct_as_record=False)
            value = data.get(name)
            pyclass = type(value).__name__
            dtype = str(getattr(value, "dtype", ""))
            if hasattr(value, "nbytes"):
                nbytes = int(value.nbytes)
        except Exception as exc:
            notes.append(f"Could not fully load {name}: {exc}")

        rows.append({
            "file": path.name,
            "path": name,
            "variable": name,
            "kind": "variable",
            "matlab_class": matlab_class,
            "python_class": pyclass,
            "shape": "x".join(str(x) for x in shape),
            "dtype": dtype,
            "bytes": nbytes,
            "size_human": human_bytes(nbytes),
        })

    return rows, notes


def classify_file(rows: List[Dict[str, Any]], filename: str) -> str:
    names = {str(r["variable"]).lower() for r in rows}
    paths = " ".join(str(r["path"]).lower() for r in rows)
    fname = filename.lower()

    if "master_event" in names or "masterevent" in names:
        return "processed results / master-event cache"
    if "infrasoundevent" in names or "infrasound_event" in names:
        return "processed infrasound event results"
    if "catalog" in names or "arrival" in names or "arrivals" in names:
        return "arrival/catalog intermediate"
    if "traveltimes" in names or "traveltime" in paths or "travel" in fname:
        return "travel-time intermediate"
    if "w" in names or "waveform" in paths or "waveform" in fname or "seismogram" in fname:
        return "waveform cache"
    if "spacex_results" in fname:
        return "likely processed results cache"
    if "spacexplosion" in fname:
        return "likely all-in-one workspace cache"
    if "currentstuff" in fname or fname == "matlab.mat":
        return "likely interactive workspace/prototype"
    return "unknown"


def inventory_file(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "file": str(path),
        "filename": path.name,
        "file_size_bytes": path.stat().st_size if path.exists() else None,
        "file_size_human": human_bytes(path.stat().st_size) if path.exists() else "",
        "format": "",
        "classification": "",
        "variables": [],
        "notes": [],
        "error": "",
    }

    try:
        if is_hdf5(path):
            result["format"] = "MATLAB v7.3 / HDF5"
            rows, notes = inventory_hdf5_mat(path)
        else:
            result["format"] = "MATLAB v5/v6/v7 or unknown"
            rows, notes = inventory_old_mat(path)

        result["variables"] = rows
        result["notes"] = notes
        result["classification"] = classify_file(rows, path.name)

    except ImportError as exc:
        result["error"] = f"Missing Python dependency: {exc}"
    except Exception as exc:
        result["error"] = repr(exc)

    return result


def write_csv(results: List[Dict[str, Any]], out_csv: Path) -> None:
    fields = [
        "file", "file_size_human", "format", "classification",
        "variable", "path", "kind", "matlab_class", "python_class",
        "shape", "dtype", "size_human", "bytes"
    ]

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for res in results:
            if not res["variables"]:
                writer.writerow({
                    "file": res["filename"],
                    "file_size_human": res["file_size_human"],
                    "format": res["format"],
                    "classification": res["classification"],
                })
            for row in res["variables"]:
                writer.writerow({
                    "file": res["filename"],
                    "file_size_human": res["file_size_human"],
                    "format": res["format"],
                    "classification": res["classification"],
                    "variable": row.get("variable", ""),
                    "path": row.get("path", ""),
                    "kind": row.get("kind", ""),
                    "matlab_class": row.get("matlab_class", ""),
                    "python_class": row.get("python_class", ""),
                    "shape": row.get("shape", ""),
                    "dtype": row.get("dtype", ""),
                    "size_human": row.get("size_human", ""),
                    "bytes": row.get("bytes", ""),
                })


def write_markdown(results: List[Dict[str, Any]], out_md: Path) -> None:
    lines: List[str] = []
    lines.append("# MATLAB MAT-file inventory\n")
    lines.append("Generated by `inventory_matfiles.py`.\n")
    lines.append("\n## File summary\n")
    lines.append("| File | Size | Format | Classification | Variables | Notes/Error |")
    lines.append("|---|---:|---|---|---:|---|")

    for res in results:
        note = res["error"] or "; ".join(res["notes"][:2])
        if len(note) > 120:
            note = note[:117] + "..."
        lines.append(
            f"| `{res['filename']}` | {res['file_size_human']} | {res['format']} | "
            f"{res['classification']} | {len(res['variables'])} | {note} |"
        )

    lines.append("\n## Per-file variables\n")

    for res in results:
        lines.append(f"\n### `{res['filename']}`\n")
        lines.append(f"- Size: {res['file_size_human']}")
        lines.append(f"- Format: {res['format']}")
        lines.append(f"- Classification: {res['classification']}")
        if res["error"]:
            lines.append(f"- Error: `{res['error']}`")
        if res["notes"]:
            lines.append("- Notes:")
            for note in res["notes"][:10]:
                lines.append(f"  - {note}")

        if not res["variables"]:
            lines.append("\nNo variables could be inventoried.\n")
            continue

        lines.append("\n| Variable/path | MATLAB class | Python class | Shape | Size |")
        lines.append("|---|---|---|---|---:|")
        shown = 0
        for row in res["variables"]:
            path = row.get("path", "")
            if "/" in str(path) and shown > 80:
                continue
            lines.append(
                f"| `{path}` | {row.get('matlab_class','')} | {row.get('python_class','')} | "
                f"{row.get('shape','')} | {row.get('size_human','')} |"
            )
            shown += 1
            if shown >= 120:
                lines.append("| ... | ... | ... | ... | ... |")
                break

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory MATLAB MAT files without MATLAB.")
    parser.add_argument("path", nargs="?", default=".", help="Directory containing MAT files, or a single MAT file.")
    parser.add_argument("--pattern", default="*.mat", help="Glob pattern when path is a directory. Default: *.mat")
    parser.add_argument("--out", default="mat_inventory", help="Output file prefix. Default: mat_inventory")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if root.is_file():
        files = [root]
        out_prefix = root.parent / args.out
    else:
        files = sorted(root.glob(args.pattern))
        out_prefix = root / args.out

    if not files:
        print(f"No files found: {root} / {args.pattern}")
        return 1

    results = [inventory_file(p) for p in files]

    out_json = out_prefix.with_suffix(".json")
    out_csv = out_prefix.with_suffix(".csv")
    out_md = out_prefix.with_suffix(".md")

    out_json.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    write_csv(results, out_csv)
    write_markdown(results, out_md)

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
