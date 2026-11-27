"""Read-only: does an older copy of SDS_KSC hold data that the current SDS_KSC lacks?

The backup (/ZPOOL_BACKUP/data/remastered/SDS_KSC on hal9000) predates fix_sds_ksc.py and the D->C/H rename,
and its unmatched/ folder is larger. For every file under the backup's unmatched/ (or the whole backup with
--all), this looks for the same channel-day in the current archive, in all of these places:

    <current>/<rel>                                  main tree (rel without the leading unmatched/)
    <current>/unmatched/<rel>
    <current>/_removed_20261126/...                  quarantined by fix_sds_ksc.py
    <current>/_renamed_D_originals_20261126/...      originals of the D->C/H rename
    the C??/H?? name of a Centaur D?? file, in the main tree and unmatched/

and labels the file:

    same        byte-identical to a current copy
    renamed     identical to a current C??/H?? copy apart from the band letter
    differs     the channel-day exists, but no current copy is identical (header summary given)
    absent      no copy of that channel-day anywhere: possibly missing data
    not_sds     not an SDS day-file name

Nothing is written except the CSV (default ./compare_backup_unmatched.csv). Needs ObsPy only for the
header summary of 'differs'/'absent' files.

    python 03_stationxml/archive_fix/compare_backup_unmatched.py \
        --backup /ZPOOL_BACKUP/data/remastered/SDS_KSC --current /data/remastered/SDS_KSC
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
from pathlib import Path

QUARANTINES = ("_removed_20261126", "_renamed_D_originals_20261126")


def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def band_masked(data: bytes):
    """Bytes with byte 15 of every 512-byte block zeroed: the band letter of each record's channel code
    (records are 512 or 4096 bytes, so every record header starts on a 512-byte boundary)."""
    b = bytearray(data)
    for i in range(15, len(b), 512):
        b[i] = 0
    return bytes(b)


def summary(p):
    try:
        from obspy import read
        st = read(str(p), headonly=True)
        return (f"{len(st)} trace(s), {sum(t.stats.npts for t in st)} samples, "
                f"{min(t.stats.starttime for t in st)} - {max(t.stats.endtime for t in st)}, "
                f"{sorted({t.stats.sampling_rate for t in st})} sps")
    except Exception as e:                      # zero-filled or odd files
        return f"unreadable: {e}"


def candidates(cur: Path, rel: Path):
    """Current paths that could hold the same channel-day as backup file `rel` (relative to the backup root)."""
    parts = rel.parts
    inner = Path(*parts[1:]) if parts[0] == "unmatched" else rel          # year/net/sta/cha.D/file
    names = [inner]
    fn = inner.name.split(".")
    if len(fn) == 7 and fn[3][:2] in ("DD", "DH"):
        for band in "CH":
            cha = band + fn[3][1:]
            names.append(Path(*inner.parts[:-2], f"{cha}.{fn[4]}", ".".join(fn[:3] + [cha] + fn[4:])))
    out = []
    for n in names:
        renamed = n != inner
        out += [(cur / n, renamed), (cur / "unmatched" / n, renamed)]
        if not renamed:
            for q in QUARANTINES:
                out += [(cur / q / n, False), (cur / q / "unmatched" / n, False)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backup", required=True, help="old SDS_KSC root")
    ap.add_argument("--current", required=True, help="current SDS_KSC root")
    ap.add_argument("--all", action="store_true", help="compare the whole backup, not only unmatched/")
    ap.add_argument("--out", default="compare_backup_unmatched.csv")
    a = ap.parse_args()
    bk, cur = Path(a.backup), Path(a.current)
    base = bk if a.all else bk / "unmatched"
    files = sorted(p for p in base.rglob("*") if p.is_file())
    print(f"{len(files)} files under {base}")
    rows, tally = [], collections.Counter()
    by_sta = collections.defaultdict(collections.Counter)
    for k, p in enumerate(files, 1):
        rel = p.relative_to(bk)
        fn = p.name.split(".")
        if len(fn) != 7:
            status, match, note = "not_sds", "", ""
        else:
            status, match, note = "absent", "", ""
            size = p.stat().st_size
            h = None
            for c, renamed in candidates(cur, rel):
                if not c.is_file():
                    continue
                status, match = "differs", str(c)
                if c.stat().st_size != size:
                    continue
                if renamed:
                    if band_masked(p.read_bytes()) == band_masked(c.read_bytes()):
                        status = "renamed"
                        break
                else:
                    h = h or sha1(p)
                    if sha1(c) == h:
                        status = "same"
                        break
            if status in ("differs", "absent"):
                note = summary(p)
                if status == "differs":
                    note += " | current: " + summary(match)
        tally[status] += 1
        if len(fn) == 7:
            by_sta[f"{fn[0]}.{fn[1]} {fn[5]}"][status] += 1
        rows.append(dict(status=status, backup=str(p), current=match, note=note))
        if k % 500 == 0:
            print(f"  {k}/{len(files)} {dict(tally)}", flush=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["status", "backup", "current", "note"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n{dict(tally)}; details in {a.out}")
    print("station/year with files that are not in the current archive (differs or absent):")
    for k in sorted(by_sta):
        c = by_sta[k]
        if c["differs"] or c["absent"]:
            print(f"  {k}: absent {c['absent']}, differs {c['differs']}, same/renamed {c['same'] + c['renamed']}")


if __name__ == "__main__":
    main()
