"""Per-event processing results: tables outside git, loaded into the sqlite catalog.

Everything a run writes goes under ``[products] out_root`` (``~/work/KSC_event_catalog``), not into
the repository: the waveforms and plots per event, and these tables in ``<out_root>/tables/``:

=========================  ================================================================
``processing_runs.csv``    one row per run: run id, code versions, parameters, output root
``event_processing.csv``   one row per event: status, error, data source, channel counts
``measurements.csv``       long table: event x channel x metric (peak, SNR, energy, duration ...)
``onsets.csv``             STA/LTA onset per event and channel, with origin-time estimate
``event_products.csv``     files written per event (miniSEED, plots, manifest) and their paths
=========================  ================================================================

Two small inputs of the catalog stay in git, in ``data/curated/``: ``detected_times.csv``
(detected origin times, read into ``events.detected_time_utc`` — only those that are source times
at the pad, ``ksclib.event_products.catalog_usable``; all detections are in ``event_processing``)
and ``event_links.csv`` (external links per event: webcasts, weather, regional data).

Rows from a newer run replace the rows of older runs for the same event, so re-processing an
event (e.g. after a StationXML fix) never leaves stale metrics behind. ``data_source`` says where
the waveforms came from: ``local_sds:<root>`` now, ``fdsn:<provider>`` for regional data later.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pandas as pd

PRODUCT_TABLES = {
    "processing_runs": "processing_runs.csv",
    "event_processing": "event_processing.csv",
    "measurements": "measurements.csv",
    "onsets": "onsets.csv",
    "event_products": "event_products.csv",
}
DETECTED_CSV = "data/curated/detected_times.csv"
LINKS_CSV = "data/curated/event_links.csv"
LINK_COLUMNS = ["event_id", "link_type", "url", "title", "source", "retrieved_utc", "notes"]
DETECTED_COLUMNS = ["event_id", "detected_time_utc", "detected_time_method", "offset_from_catalog_s",
                    "mad_s", "n_stations", "n_channels", "n_channels_disagree", "nearest_km", "run_id"]


def git_commit(path) -> str:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return ""


def _read(path: Path, **kw) -> pd.DataFrame:
    """CSV as strings; empty frame for a missing or empty file."""
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, **kw)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _upsert(path: Path, new: pd.DataFrame, keys=("event_id",)) -> pd.DataFrame:
    """Replace rows of `path` whose `keys` appear in `new`, then append `new`."""
    if path.exists() and path.stat().st_size:
        old = _read(path)
        if not new.empty and all(k in old for k in keys):
            drop = old.set_index(list(keys)).index.isin(new.astype({k: str for k in keys}).set_index(list(keys)).index)
            old = old[~drop]
        new = pd.concat([old, new.astype(str)], ignore_index=True) if not new.empty else old
    path.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(path, index=False)
    return new


def tables_dir(out_root) -> Path:
    return Path(out_root).expanduser() / "tables"


def save_results(root: Path, tables: Path, run: dict, results: list) -> dict:
    """Write one run's results (ksclib.event_products.EventResult list) to `tables`; detected
    origin times to <root>/data/curated/detected_times.csv."""
    d = Path(tables)
    d.mkdir(parents=True, exist_ok=True)
    _upsert(d / "processing_runs.csv", pd.DataFrame([{**run, "params": json.dumps(run.get("params", {}), default=str)}]),
            keys=("run_id",))
    status = pd.DataFrame([dict(event_id=r.event_id, run_id=run["run_id"], status=r.status, error=r.error,
                                data_source=r.data_source, n_raw=r.n_raw, n_corrected=r.n_corrected,
                                n_metric_channels=(r.metrics.seed_id.nunique() if len(r.metrics) else 0),
                                n_onsets=len(r.onsets),
                                detected_time_utc=r.detected.get("detected_time_utc", ""),
                                detected_offset_s=r.detected.get("offset_s", ""),
                                detected_nearest_km=r.detected.get("nearest_km", ""),
                                detected_n_stations=r.detected.get("n_stations", ""),
                                detected_rival_ratio=r.detected.get("rival_ratio", ""),
                                detected_used_by_catalog=r.detected.get("catalog_usable", ""),
                                detected_not_used_reason=r.detected.get("not_usable_reason", ""),
                                warnings=" | ".join(r.warnings)[:2000]) for r in results])
    _upsert(d / "event_processing.csv", status)
    ok = [r for r in results if r.status == "ok"]
    done = pd.DataFrame({"event_id": [r.event_id for r in ok]})
    cat = lambda frames: pd.concat([f for f in frames if len(f)], ignore_index=True) if any(len(f) for f in frames) else pd.DataFrame()  # noqa: E731
    meas = cat([r.metrics for r in ok])
    ons = cat([r.onsets for r in ok])
    prods = cat([pd.DataFrame(r.products).assign(event_id=r.event_id, run_id=run["run_id"],
                                                 data_source=r.data_source) for r in ok if r.products])
    # events processed OK replace all their earlier rows, even if this run produced none
    for name, df in (("measurements.csv", meas), ("onsets.csv", ons), ("event_products.csv", prods)):
        path = d / name
        if path.exists() and path.stat().st_size and len(done):
            old = _read(path)
            if "event_id" in old:
                old = old[~old.event_id.isin(done.event_id)]
            df = pd.concat([old, df.astype(str)], ignore_index=True) if len(df) else old
        df.to_csv(path, index=False)
    det = pd.DataFrame([dict(event_id=r.event_id, detected_time_utc=r.detected["detected_time_utc"],
                             detected_time_method=r.detected["method"],
                             offset_from_catalog_s=round(r.detected["offset_s"], 3),
                             mad_s=round(r.detected["mad_s"], 3) if r.detected["mad_s"] == r.detected["mad_s"] else "",
                             n_stations=r.detected["n_stations"], n_channels=r.detected["n_channels"],
                             n_channels_disagree=r.detected.get("n_channels_disagree", ""),
                             nearest_km=round(r.detected.get("nearest_km", float("nan")), 2),
                             run_id=run["run_id"]) for r in ok if r.detected and r.detected.get("catalog_usable", True)],
                       columns=DETECTED_COLUMNS)
    # events with no detection lose an older detected time from an earlier run
    detp = Path(root) / DETECTED_CSV
    if detp.exists() and len(done):
        old = _read(detp)
        if "event_id" in old:
            old = old[~old.event_id.isin(done.event_id)]
        det = pd.concat([old, det.astype(str)], ignore_index=True)
    det.sort_values("event_id").to_csv(detp, index=False)
    return dict(ok=len(ok), failed=len(results) - len(ok), measurements=len(meas), onsets=len(ons),
                detected=int(sum(bool(r.detected) for r in ok)))


def load_products(root: Path, tables: Path | None, db_path: Path) -> list[str]:
    """(Re)load the run tables in `tables` (skipped if None or missing) and
    <root>/data/curated/event_links.csv into the sqlite catalog; returns the tables loaded."""
    paths = {t: Path(tables) / n for t, n in PRODUCT_TABLES.items()} if tables else {}
    paths["event_links"] = Path(root) / LINKS_CSV
    loaded = []
    with sqlite3.connect(db_path) as con:
        for table, p in paths.items():
            if not p.exists():
                continue
            df = _read(p)
            if df.empty and not len(df.columns):
                continue
            if table == "measurements":
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
            for c in ("distance_km", "azimuth_deg", "onset_s", "max_ratio", "origin_est_s", "sampling_rate"):
                if c in df:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            con.execute(f"DROP TABLE IF EXISTS {table}")
            df.to_sql(table, con, index=False)
            if "event_id" in df:
                con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_event ON {table}(event_id)")
            loaded.append(table)
        if {"measurements", "event_processing"} <= set(loaded):
            con.executescript(EVENT_TIERS_VIEW)
            loaded.append("event_tiers (view)")
    return loaded


# Usability tiers of science plan section 3.3. "usable" = at least one channel of that kind with
# peak SNR >= 3 that is not a lower bound (Gem overflow). The quantitative tier needs the
# versioned calibration table (not built yet), so it is NULL until then.
EVENT_TIERS_VIEW = """
DROP VIEW IF EXISTS event_tiers;
CREATE VIEW event_tiers AS
WITH good AS (
    SELECT event_id, station, kind FROM measurements
    WHERE metric = 'snr_peak' AND value >= 3 AND qc_flag NOT IN ('lower_bound')
)
SELECT e.event_id, e.event_time_utc, e.event_type, e.vehicle, e.pad,
       COALESCE(a.n_stations, 0) > 0                                   AS has_waveform_data,
       COALESCE(a.n_stations, 0)                                       AS n_stations_archive,
       p.status                                                        AS processing_status,
       p.run_id                                                        AS processing_run,
       (SELECT COUNT(DISTINCT station) FROM good g WHERE g.event_id = e.event_id AND g.kind = 'pressure') AS n_stations_usable_infrasound,
       (SELECT COUNT(DISTINCT station) FROM good g WHERE g.event_id = e.event_id AND g.kind LIKE 'seismic_%') AS n_stations_usable_seismic,
       (SELECT COUNT(DISTINCT station) FROM good g WHERE g.event_id = e.event_id) AS n_stations_usable,
       NULL                                                            AS meets_quantitative_quality
FROM events e
LEFT JOIN event_waveform_availability a ON a.event_id = e.event_id
LEFT JOIN event_processing p ON p.event_id = e.event_id;
"""
