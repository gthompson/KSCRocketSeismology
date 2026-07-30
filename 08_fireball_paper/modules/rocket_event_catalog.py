"""Flat-file catalogue support for KSC/CCSFS seismo-acoustic events.

The event manifest is the authoritative catalogue record.  ``catalog.csv`` is
rebuilt from the manifests and is intended as a convenient index rather than a
second source of truth.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


SCHEMA_VERSION = "1.0"
DEFAULT_EVENT_TYPES = {
    "launch",
    "landing",
    "static_fire",
    "explosion",
    "sonic_boom",
    "earthquake",
    "storm",
    "other",
}


def _utc_datetime(value: Any) -> datetime:
    """Convert ISO text, datetime, or ObsPy UTCDateTime-like input to UTC."""
    if isinstance(value, datetime):
        result = value
    elif hasattr(value, "datetime"):
        result = value.datetime
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        result = datetime.fromisoformat(text)

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def isoformat_utc(value: Any | None) -> str | None:
    """Return an ISO-8601 UTC timestamp with millisecond precision."""
    if value is None:
        return None
    return (
        _utc_datetime(value)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def event_time_token(value: Any) -> str:
    """Return a sortable filesystem-safe UTC timestamp."""
    return _utc_datetime(value).strftime("%Y%m%dT%H%M%S%f")[:-3] + "Z"


def slugify(value: str) -> str:
    """Convert descriptive text to a conservative filesystem slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not slug:
        raise ValueError("Event slug cannot be empty")
    return slug


def filename_token(value: str) -> str:
    """Sanitize an identifier for filenames while preserving code case."""
    token = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    if not token:
        raise ValueError("Filename token cannot be empty")
    return token


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate the SHA-256 checksum of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class EventDetails:
    """Descriptive metadata shared by all station datasets for one event."""

    event_time_utc: Any
    event_type: str
    event_name: str
    slug: str
    event_end_utc: Any | None = None
    event_subtype: str | None = None
    tags: tuple[str, ...] = ()
    status: str = "provisional"
    vehicle: str | None = None
    mission: str | None = None
    operator: str | None = None
    facility: str | None = None
    site: str | None = None
    source: Mapping[str, Any] | None = None
    description: str | None = None
    notes: str | None = None

    @property
    def event_id(self) -> str:
        return f"{event_time_token(self.event_time_utc)}_{slugify(self.slug)}"

    def manifest_fields(self) -> dict[str, Any]:
        event_type = slugify(self.event_type)
        return {
            "event_id": self.event_id,
            "event_time_utc": isoformat_utc(self.event_time_utc),
            "event_end_utc": isoformat_utc(self.event_end_utc),
            "event_type": event_type,
            "event_subtype": (
                None if self.event_subtype is None
                else slugify(self.event_subtype)
            ),
            "tags": sorted({slugify(tag) for tag in self.tags}),
            "status": self.status,
            "event_name": self.event_name,
            "vehicle": self.vehicle,
            "mission": self.mission,
            "operator": self.operator,
            "facility": self.facility,
            "site": self.site,
            "source": (
                None if self.source is None else dict(self.source)
            ),
            "description": self.description,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class StationDataset:
    """Files and channel information contributed by one recording station."""

    network: str
    station: str
    location: str = ""
    channels: tuple[str, ...] = ()
    raw_miniseed: str | Path | None = None
    corrected_miniseed: str | Path | None = None
    corrected_pickle: str | Path | None = None
    original_stationxml: str | Path | None = None
    calibrated_stationxml: str | Path | None = None
    processing_record: str | Path | None = None
    channel_summary: str | Path | None = None
    corrected_units: Mapping[str, str] = field(default_factory=dict)

    @property
    def station_token(self) -> str:
        components = [self.network, self.station]
        if self.location:
            components.append(self.location)
        return "_".join(filename_token(part) for part in components)


PRODUCT_LAYOUT = {
    "raw_miniseed": ("waveforms/raw", "raw", ".mseed"),
    "corrected_miniseed": (
        "waveforms/corrected",
        "corrected",
        ".mseed",
    ),
    "corrected_pickle": (
        "waveforms/pickle",
        "corrected",
        ".pkl",
    ),
    "original_stationxml": (
        "metadata",
        "stations_original",
        ".xml",
    ),
    "calibrated_stationxml": (
        "metadata",
        "stations_calibrated",
        ".xml",
    ),
    "processing_record": (
        "processing",
        "response_removal",
        ".json",
    ),
    "channel_summary": (
        "processing",
        "channel_summary",
        ".csv",
    ),
}


def event_directory(
    catalog_root: str | Path,
    details: EventDetails,
) -> Path:
    """Return the canonical YYYY/MM/DD/event_id directory."""
    time = _utc_datetime(details.event_time_utc)
    return (
        Path(catalog_root)
        / "events"
        / f"{time.year:04d}"
        / f"{time.month:02d}"
        / f"{time.day:02d}"
        / details.event_id
    )


def _copy_product(
    source: str | Path,
    destination: Path,
    *,
    overwrite: bool,
) -> dict[str, Any]:
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Catalogue product not found: {source}")

    source_hash = sha256_file(source)
    if destination.exists():
        destination_hash = sha256_file(destination)
        if destination_hash == source_hash:
            return {
                "sha256": source_hash,
                "size_bytes": destination.stat().st_size,
                "copy_status": "already_identical",
            }
        if not overwrite:
            raise FileExistsError(
                f"Catalogue product differs from source: {destination}"
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)
    return {
        "sha256": source_hash,
        "size_bytes": destination.stat().st_size,
        "copy_status": "copied",
    }


def _initialize_catalog(catalog_root: Path) -> None:
    catalog_root.mkdir(parents=True, exist_ok=True)
    (catalog_root / "events").mkdir(exist_ok=True)
    schema_directory = catalog_root / "schema"
    schema_directory.mkdir(exist_ok=True)

    readme = catalog_root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# KSC/CCSFS Seismo-acoustic Event Catalogue\n\n"
            "Each event manifest is authoritative. `catalog.csv` is generated "
            "from the manifests. Raw waveform products should be treated as "
            "immutable.\n",
            encoding="utf-8",
        )

    schema_path = schema_directory / "event_manifest_schema.json"
    if not schema_path.exists():
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "KSC/CCSFS event manifest",
            "type": "object",
            "required": [
                "schema_version",
                "event_id",
                "event_time_utc",
                "event_type",
                "event_name",
                "stations",
                "files",
            ],
            "properties": {
                "schema_version": {"type": "string"},
                "event_id": {"type": "string"},
                "event_time_utc": {"type": "string"},
                "event_type": {"type": "string"},
                "event_name": {"type": "string"},
                "stations": {"type": "array"},
                "files": {"type": "array"},
            },
        }
        schema_path.write_text(
            json.dumps(schema, indent=2) + "\n",
            encoding="utf-8",
        )


def _write_checksums(event_dir: Path, files: Iterable[dict[str, Any]]) -> None:
    lines = [
        f"{item['sha256']}  {item['path']}"
        for item in sorted(files, key=lambda item: item["path"])
    ]
    (event_dir / "checksums.sha256").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def rebuild_catalog_csv(catalog_root: str | Path) -> Path:
    """Rebuild the flat CSV index from all event manifests."""
    catalog_root = Path(catalog_root)
    rows = []
    for manifest_path in catalog_root.glob("events/*/*/*/*/event.yaml"):
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        rows.append({
            "event_id": manifest["event_id"],
            "event_time_utc": manifest["event_time_utc"],
            "event_end_utc": manifest.get("event_end_utc"),
            "event_type": manifest["event_type"],
            "event_subtype": manifest.get("event_subtype"),
            "event_name": manifest["event_name"],
            "site": manifest.get("site"),
            "vehicle": manifest.get("vehicle"),
            "mission": manifest.get("mission"),
            "status": manifest.get("status"),
            "event_directory": manifest_path.parent.relative_to(
                catalog_root
            ).as_posix(),
        })

    rows.sort(key=lambda row: (row["event_time_utc"], row["event_id"]))
    columns = [
        "event_id",
        "event_time_utc",
        "event_end_utc",
        "event_type",
        "event_subtype",
        "event_name",
        "site",
        "vehicle",
        "mission",
        "status",
        "event_directory",
    ]
    catalog_path = catalog_root / "catalog.csv"
    with catalog_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return catalog_path


def register_event(
    *,
    catalog_root: str | Path,
    details: EventDetails,
    station_datasets: Iterable[StationDataset],
    recording_window_start_utc: Any | None = None,
    recording_window_end_utc: Any | None = None,
    provenance: Mapping[str, Any] | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create or refresh a complete flat-file event package.

    Files with identical checksums are accepted without being recopied.
    Conflicting existing files raise ``FileExistsError`` unless ``overwrite``
    is explicitly enabled.
    """
    catalog_root = Path(catalog_root).expanduser().resolve()
    _initialize_catalog(catalog_root)
    event_dir = event_directory(catalog_root, details)
    event_dir.mkdir(parents=True, exist_ok=True)

    datasets = list(station_datasets)
    if not datasets:
        raise ValueError("At least one StationDataset is required")

    station_records = []
    file_records = []
    for dataset in datasets:
        station_records.append({
            "network": dataset.network,
            "station": dataset.station,
            "location": dataset.location,
            "channels": list(dataset.channels),
            "corrected_units": dict(dataset.corrected_units),
        })

        for role, (directory, product_name, suffix) in PRODUCT_LAYOUT.items():
            source = getattr(dataset, role)
            if source is None:
                continue
            filename = (
                f"{details.event_id}_{dataset.station_token}_"
                f"{product_name}{suffix}"
            )
            destination = event_dir / directory / filename
            copy_result = _copy_product(
                source,
                destination,
                overwrite=overwrite,
            )
            file_records.append({
                "role": role,
                "network": dataset.network,
                "station": dataset.station,
                "location": dataset.location,
                "path": destination.relative_to(event_dir).as_posix(),
                "sha256": copy_result["sha256"],
                "size_bytes": copy_result["size_bytes"],
            })

    now = datetime.now(timezone.utc)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        **details.manifest_fields(),
        "recording_window": {
            "start_utc": isoformat_utc(recording_window_start_utc),
            "end_utc": isoformat_utc(recording_window_end_utc),
        },
        "stations": station_records,
        "files": sorted(file_records, key=lambda item: item["path"]),
        "provenance": {
            "catalogued_utc": isoformat_utc(now),
            **({} if provenance is None else dict(provenance)),
        },
        "extra_metadata": (
            {} if extra_metadata is None else dict(extra_metadata)
        ),
    }

    manifest_path = event_dir / "event.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            manifest,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    _write_checksums(event_dir, file_records)
    catalog_path = rebuild_catalog_csv(catalog_root)

    return {
        "event_id": details.event_id,
        "event_directory": event_dir,
        "manifest": manifest_path,
        "catalog": catalog_path,
        "checksums": event_dir / "checksums.sha256",
        "files": file_records,
    }
