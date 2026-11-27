"""Zenodo: upload the per-year waveform zips as a DRAFT deposit; link the published record.

    export ZENODO_TOKEN=...                  # personal token (scope deposit:write), never in git
    ksc-rockets zenodo-upload --sandbox      # trial on sandbox.zenodo.org (its own account and token)
    ksc-rockets zenodo-upload                # zenodo.org: creates a draft, uploads, prints its URL
    # review the draft on the web page, add co-authors/grants if needed, press Publish yourself
    ksc-rockets zenodo-links --record 1234567
    ksc-rockets build-site --web

Default access is restricted (zenodo_metadata.json): the record and DOI are public, the files only
for people the owner grants access (Zenodo: Share -> add people or create a link; or approve an
access request). Switch the record to open on zenodo.org when the data may be public, then rerun
zenodo-links with --access open.

The upload never publishes: publishing mints a DOI and cannot be undone, so it is left to the
owner on zenodo.org. Metadata come from data/curated/zenodo_metadata.json (edit it first).
`--deposition ID` adds files to an existing draft (e.g. a new version opened on the web page).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

HOSTS = {False: "https://zenodo.org", True: "https://sandbox.zenodo.org"}


def _session(token: str):
    import requests
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    return s


def archive_files(archive_dir: Path) -> list[Path]:
    """The year zips and the files index, in upload order."""
    d = Path(archive_dir).expanduser()
    files = sorted(d.glob("ksc_event_waveforms_*.zip"))
    if (d / "files_index.csv").exists():
        files.append(d / "files_index.csv")
    return files


def upload_draft(archive_dir, metadata_path, *, sandbox=False, deposition=None, token=None, log=print) -> dict:
    """Create (or reuse) a draft deposition, upload the archive files not yet in it; returns the draft."""
    token = token or os.environ.get("ZENODO_TOKEN")
    if not token:
        raise SystemExit("zenodo-upload: set ZENODO_TOKEN (a personal access token with deposit:write)")
    api = HOSTS[bool(sandbox)] + "/api"
    s = _session(token)
    files = archive_files(archive_dir)
    if not files:
        raise SystemExit(f"zenodo-upload: no ksc_event_waveforms_*.zip in {archive_dir} (run package-waveforms)")
    if deposition:
        r = s.get(f"{api}/deposit/depositions/{deposition}", timeout=60)
    else:
        meta = json.loads(Path(metadata_path).read_text())
        r = s.post(f"{api}/deposit/depositions", json={"metadata": meta.get("metadata", meta)}, timeout=60)
    r.raise_for_status()
    dep = r.json()
    have = {f["filename"]: f for f in dep.get("files", [])}
    bucket = dep["links"]["bucket"]
    for f in files:
        size = f.stat().st_size
        if f.name in have and int(have[f.name].get("filesize", -1)) == size:
            log(f"zenodo: {f.name} already in draft {dep['id']}")
            continue
        log(f"zenodo: uploading {f.name} ({size / 1e9:.2f} GB)")
        with open(f, "rb") as fh:
            u = s.put(f"{bucket}/{f.name}", data=fh, timeout=None)
        u.raise_for_status()
    dep = s.get(f"{api}/deposit/depositions/{dep['id']}", timeout=60).json()
    log(f"zenodo: draft {dep['id']} has {len(dep.get('files', []))} files; review and publish at "
        f"{dep['links'].get('html', HOSTS[bool(sandbox)] + '/uploads/' + str(dep['id']))}")
    return dep


def record_links(record: int | str, archive_dir, urls_csv, *, sandbox=False, access="restricted") -> pd.DataFrame:
    """Write data/curated/waveform_urls.csv rows (key = year) for the zips of a published record.
    `access` ("restricted" or "open") is shown on the event pages next to the links. Other keys
    already in the file (single events, other archives) are kept."""
    base = f"{HOSTS[bool(sandbox)]}/records/{record}/files"
    rows = []
    for f in sorted(Path(archive_dir).expanduser().glob("ksc_event_waveforms_*.zip")):
        year = f.stem.rsplit("_", 1)[-1]
        rows.append(dict(key=year, url=f"{base}/{f.name}?download=1", notes=f"Zenodo record {record}",
                         access=access, record_url=f"{HOSTS[bool(sandbox)]}/records/{record}"))
    new = pd.DataFrame(rows, columns=["key", "url", "notes", "access", "record_url"])
    p = Path(urls_csv)
    if p.exists() and p.stat().st_size:
        old = pd.read_csv(p, dtype=str, keep_default_na=False)
        new = pd.concat([old[~old.key.isin(new.key)], new], ignore_index=True)
    new.to_csv(p, index=False)
    return new
