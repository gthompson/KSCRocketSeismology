"""Add MiniSEED records from other copies (service downloads, backups) into an SDS archive, losslessly.

Each source file is cut into its 512/4096-byte records. Centaur D?? broadband records get the SEED band letter
for their own sample rate (C 250-999 sps, H 80-249 sps), as in rename_band_codes.py, and are routed to that
channel's day file. Within a target day file, a source record is added only if no target record has the same
start time; a same-start record that differs beyond the band letter, sequence number and quality flag is
logged and the target's is kept.
The merged file is sorted by record start time, read back, and must hold every record of the old target file.

--by-header routes each record by its own header codes and start day instead of the source file name (for raw
minute files). --network/--station rewrite those header codes in every record (e.g. FL -> 1R); data untouched.

A target file that is unreadable (e.g. zero-filled) is replaced instead of merged (--replace-unreadable). Any
target file that is changed or replaced is first copied to <SDS>/_added_records_<tag>/ with its relative path,
and every action goes to <SDS>/_added_records_<tag>/manifest.csv. Without --apply nothing is written.

    python add_records.py --sds /Volumes/Pulwtop/SDS_KSC_2026 --tag 20261127 \
        /Volumes/KSCGTdownld/20260922_service/00_download/Centaur/2026/1R/B20/D??.D/*.2026.165 --apply
"""
from __future__ import annotations

import argparse
import csv
import shutil
import struct
from collections import OrderedDict
from pathlib import Path

from obspy import read

from rename_band_codes import BROADBAND_D, band_for, band_masked, byteorder, record_length, sample_rate


def records(data: bytes):
    """[(start key, channel code, record bytes)]; raises on a bad record."""
    out, pos = [], 0
    while pos < len(data):
        bo = byteorder(data[pos:pos + 48])
        rl = record_length(data[pos:pos + 512], bo)
        if not rl or pos + rl > len(data):
            raise ValueError(f"bad record at byte {pos}")
        r = bytearray(data[pos:pos + rl])
        y, j, h, m, s, _, f = struct.unpack(bo + "HHBBBBH", r[20:30])
        cha = r[15:18].decode()
        if cha[:2] in BROADBAND_D:
            b = band_for(sample_rate(r[:48], bo))
            if b is None:
                raise ValueError(f"record at byte {pos}: {cha} at {sample_rate(r[:48], bo)} sps")
            r[15:16] = b
            cha = r[15:18].decode()
        out.append(((y, j, h, m, s, f), cha, bytes(r)))
        pos += rl
    return out


def set_codes(r: bytes, network=None, station=None):
    """Record with its network and/or station code replaced (header bytes 18:20 and 8:13); data untouched."""
    r = bytearray(r)
    if network:
        r[18:20] = network.ljust(2).encode()
    if station:
        r[8:13] = station.ljust(5).encode()
    return bytes(r)


def header_target(sds: Path, r: bytes, key):
    """SDS path for a record, from its own header codes and start day."""
    sta = r[8:13].decode().strip()
    loc = r[13:15].decode().strip()
    cha = r[15:18].decode().strip()
    net = r[18:20].decode().strip()
    y, j = key[0], key[1]
    return sds / str(y) / net / sta / f"{cha}.D" / f"{net}.{sta}.{loc}.{cha}.D.{y}.{j:03d}"


def group_sources(sources, sds: Path, by_header=False, network=None, station=None, day=None):
    """{target path: [(start key, record, source)]}. With by_header, records are routed by their own header
    (codes and start day; `day` = (year, jday) keeps only records starting that day); otherwise by the
    source's SDS file name."""
    groups = OrderedDict()
    for src in map(Path, sources):
        if not by_header:
            n, s, l, c, q, y, j = src.name.split(".")
        for key, cha, r in records(src.read_bytes()):
            if network or station:
                r = set_codes(r, network, station)
            if by_header:
                if day and (key[0], key[1]) != day:
                    continue
                t = header_target(sds, r, key)
            else:
                t = sds / y / (network or n) / (station or s) / f"{cha}.{q}" / \
                    f"{network or n}.{station or s}.{l}.{cha}.{q}.{y}.{j}"
            groups.setdefault(t, []).append((key, r, src))
    return groups


def merge_groups(groups, sds: Path, tag: str, apply=False, replace_unreadable=False, quiet=False):
    """Merge each group's records into its target file; returns manifest rows (also appended to the manifest)."""
    bak = sds / f"_added_records_{tag}"
    rows = []
    for t, new in groups.items():
        old, status = [], "new"
        if t.exists():
            try:
                old = [(k, r) for k, _, r in records(t.read_bytes())]
                status = "merge"
            except Exception as e:
                if not replace_unreadable:
                    raise SystemExit(f"{t} is unreadable ({e}); use --replace-unreadable")
                status = "replace-unreadable"
        have = {k: r for k, r in old}
        added = same = clash = 0
        merged = list(old)
        for k, r, src in new:
            if k in have:
                if band_masked(have[k])[8:] == band_masked(r)[8:]:   # ignore sequence number/quality flag
                    same += 1
                else:
                    clash += 1
                continue
            have[k] = r
            merged.append((k, r))
            added += 1
        srcs = sorted({str(x[2]) for x in new})
        srcs = ";".join(srcs) if len(srcs) <= 3 else f"{srcs[0]} ... {srcs[-1]} ({len(srcs)} files)"
        note = f"{len(old)} old records, {added} added, {same} identical, {clash} same-start but different (kept old)"
        action = status if added else "unchanged"
        rows.append(dict(action=action, target=t, sources=srcs, note=note))
        if not quiet or clash:
            print(action, t.name, note, flush=True)
        if not apply or not added:
            continue
        merged.sort(key=lambda x: x[0])
        blob = b"".join(r for _, r in merged)
        if t.exists():
            b = bak / t.relative_to(sds)
            b.parent.mkdir(parents=True, exist_ok=True)
            if not b.exists():
                shutil.copy2(t, b)
                if b.stat().st_size != t.stat().st_size:
                    raise RuntimeError(f"backup of {t} has the wrong size")
        t.parent.mkdir(parents=True, exist_ok=True)
        tmp = t.with_name(t.name + ".tmp")
        tmp.write_bytes(blob)
        if tmp.read_bytes() != blob:
            raise RuntimeError(f"{tmp}: read-back differs")
        kept = {k for k, _, _ in records(tmp.read_bytes())}
        if not {k for k, _ in old} <= kept or len(kept) != len(merged):
            raise RuntimeError(f"{tmp}: records lost")
        ids = {tr.id for tr in read(str(tmp), headonly=True)}
        if len(ids) != 1:
            raise RuntimeError(f"{tmp}: ids {ids}")
        tmp.replace(t)
    if apply:
        bak.mkdir(parents=True, exist_ok=True)
        man = bak / "manifest.csv"
        new_file = not man.exists()
        with open(man, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["action", "target", "sources", "note"])
            if new_file:
                w.writeheader()
            w.writerows(rows)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", help="source MiniSEED files (SDS day-file names unless --by-header)")
    ap.add_argument("--sds", required=True, help="target SDS root")
    ap.add_argument("--tag", required=True, help="suffix of the backup/manifest folder, e.g. 20261127")
    ap.add_argument("--by-header", action="store_true",
                    help="route each record by its own header codes and start day (e.g. raw minute files)")
    ap.add_argument("--network", help="replace the network code in every record (e.g. FL -> 1R)")
    ap.add_argument("--station", help="replace the station code in every record")
    ap.add_argument("--replace-unreadable", action="store_true",
                    help="replace a target file that cannot be parsed (e.g. zero-filled) instead of stopping")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sds = Path(a.sds)
    groups = group_sources(a.sources, sds, a.by_header, a.network, a.station)
    merge_groups(groups, sds, a.tag, a.apply, a.replace_unreadable)
    if a.apply:
        print(f"manifest {sds / f'_added_records_{a.tag}' / 'manifest.csv'}")


if __name__ == "__main__":
    main()
