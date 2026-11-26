"""Rename the Centaur broadband channels in an SDS archive to their SEED band codes: D?? -> C?? (250-999 sps)
or H?? (80-249 sps). User decision 2026-11-26; see seed_band_codes() in make_master_v3.py.

The Centaur names its channels with band code D at 250/500 sps, but D is for sensors with a corner period
< 10 s; the Trillium Compact (120 s), infraBSU (~28 s) and Chaparral M25 are broadband (C). B20
(2026-04-04..06-14) and the B24 huddle (2026-01-08) ran at 100 sps under the D names, so those records
become H??. SmartSolo DP? (5 Hz geophone) is correctly D and is not touched; nor is anything else.

Only the 3-byte channel field of each 512/4096-byte MiniSEED 2 record header is changed. Data bytes are
copied untouched, so the conversion is lossless. Records are routed by their own sample rate, so a day file
that switches from 500 to 100 sps is split into a C?? and an H?? file. The originals are moved to
<SDS>/_renamed_D_originals_20261126/ (same relative paths) unless --delete-originals is given, and every
action is written to a manifest CSV.

    python rename_band_codes.py --sds /Volumes/KSCGTdownld/SDS                  # dry run
    python rename_band_codes.py --sds /Volumes/KSCGTdownld/SDS --apply
    python rename_band_codes.py --sds /path/to/remastered/SDS_KSC --apply      # on hal9000

Run fix_sds_ksc.py first on the remastered archive. Afterwards use KSC.xml (SEED codes) with the archive,
instead of KSC_sds_codes.xml.
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import struct
from collections import OrderedDict
from pathlib import Path

from obspy import read

BROADBAND_D = {"DD", "DH"}            # Centaur infrasound (infraBSU/Chaparral) and Trillium; not DP? (SmartSolo)
QUARANTINE = "_renamed_D_originals_20261126"
SKIP_DIRS = {"_removed_20261126", QUARANTINE}


def band_for(sr):
    if sr >= 250:
        return b"C"
    if sr >= 80:
        return b"H"
    return None


def sample_rate(hdr, bo):
    f, m = struct.unpack(bo + "hh", hdr[32:36])
    if f == 0 or m == 0:
        return 0.0
    if f > 0 and m > 0:
        return float(f * m)
    if f > 0 > m:
        return -f / m
    if f < 0 < m:
        return -m / f
    return 1.0 / (f * m)


def record_length(rec, bo):
    off = struct.unpack(bo + "H", rec[46:48])[0]
    seen = 0
    while off and seen < 20:
        btype, nxt = struct.unpack(bo + "HH", rec[off:off + 4])
        if btype == 1000:
            return 2 ** rec[off + 6]
        off, seen = nxt, seen + 1
    return None


def byteorder(rec):
    year = struct.unpack(">H", rec[20:22])[0]
    return ">" if 1900 <= year <= 2100 else "<"


def split_file(path):
    """{new channel code: bytearray of records} for one D?? file; raises on anything unexpected."""
    data = Path(path).read_bytes()
    out, pos = OrderedDict(), 0
    while pos < len(data):
        rec = data[pos:pos + 48]
        bo = byteorder(rec)
        rl = record_length(data[pos:pos + 512], bo)
        if not rl or pos + rl > len(data):
            raise ValueError(f"bad record at byte {pos}")
        cha = data[pos + 15:pos + 18]
        b = band_for(sample_rate(rec, bo))
        if b is None or cha[:2].decode() not in BROADBAND_D:
            raise ValueError(f"record at byte {pos}: channel {cha!r}, {sample_rate(rec, bo)} sps")
        r = bytearray(data[pos:pos + rl])
        r[15:16] = b
        new = r[15:18].decode()
        out.setdefault(new, bytearray()).extend(r)
        pos += rl
    return out, len(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sds", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--delete-originals", action="store_true",
                    help="delete each original once its renamed copy is written and checked (default: quarantine)")
    a = ap.parse_args()
    sds = Path(a.sds)
    rows, n_ok, n_conf = [], 0, 0
    files = sorted(p for p in sds.rglob("*.D/*") if p.is_file()
                   and not (set(p.relative_to(sds).parts) & SKIP_DIRS)
                   and p.parent.name[:2] in BROADBAND_D and len(p.name.split(".")) == 7)
    print(f"{len(files)} D?? files under {sds}")
    for f in files:
        n, s, l, c, q, y, j = f.name.split(".")
        try:
            parts, nbytes = split_file(f)
        except Exception as e:
            rows.append(dict(action="ERROR", src=f, dst="", check=str(e)))
            print("ERROR", f, e)
            continue
        dsts = {cha: f.parent.parent / f"{cha}.D" / f"{n}.{s}.{l}.{cha}.{q}.{y}.{j}" for cha in parts}
        clash = [d for d in dsts.values() if d.exists()]
        if clash:
            n_conf += 1
            rows.append(dict(action="CONFLICT", src=f, dst=";".join(map(str, clash)), check="destination exists"))
            print("CONFLICT", f, clash)
            continue
        check = f"{nbytes} bytes -> " + ", ".join(f"{k}: {len(v)} bytes" for k, v in parts.items())
        for cha, d in dsts.items():
            rows.append(dict(action="write", src=f, dst=d, check=check))
        if a.apply:
            for cha, d in dsts.items():
                d.parent.mkdir(parents=True, exist_ok=True)
                tmp = d.with_name(d.name + ".tmp")
                tmp.write_bytes(parts[cha])
                st = read(str(tmp), headonly=True)
                ids = {tr.id for tr in st}
                if ids != {f"{n}.{s}.{'' if l == '--' else l}.{cha}"} and ids != {f"{n}.{s}.{l}.{cha}"}:
                    tmp.unlink()
                    raise RuntimeError(f"{tmp}: unexpected ids {ids}")
                os.replace(tmp, d)
            if a.delete_originals:
                f.unlink()
                rows.append(dict(action="delete", src=f, dst="", check="renamed copies written and read back"))
            else:
                q_ = sds / QUARANTINE / f.relative_to(sds)
                q_.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(q_))
                rows.append(dict(action="quarantine", src=f, dst=q_, check=""))
        n_ok += 1
    man = (sds / QUARANTINE / "manifest.csv") if a.apply else Path("rename_band_codes_manifest.csv")
    man.parent.mkdir(parents=True, exist_ok=True)
    with open(man, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["action", "src", "dst", "check"])
        w.writeheader()
        w.writerows(rows)
    errs = sum(r["action"] == "ERROR" for r in rows)
    print(f"{'renamed' if a.apply else 'would rename'} {n_ok} files; {n_conf} conflicts; {errs} errors; manifest {man}")
    # remove empty D?? channel folders left behind
    if a.apply:
        for d in sorted(sds.rglob("D[DH]?.D"), reverse=True):
            if d.is_dir() and not any(d.iterdir()) and not (set(d.relative_to(sds).parts) & SKIP_DIRS):
                d.rmdir()


if __name__ == "__main__":
    main()
