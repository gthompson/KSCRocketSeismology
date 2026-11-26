"""Fix the remastered SDS_KSC archive so that it agrees with KSC.xml (audit of 2026-11-25/26).

Run this on the host that can write to the archive (hal9000), from a checkout of this branch:

    python 03_stationxml/archive_fix/fix_sds_ksc.py --sds /path/to/remastered/SDS_KSC            # dry run
    python 03_stationxml/archive_fix/fix_sds_ksc.py --sds /path/to/remastered/SDS_KSC --apply    # do it

Nothing is deleted. Every file that is removed or replaced is moved into <SDS>/_removed_20261126/ with
the same relative path, so the whole operation can be undone. Once you are happy, `rm -r` that folder.
A manifest of every action (with the check that justified it) is written to
<SDS>/_removed_20261126/manifest.csv (and to ./fix_sds_ksc_manifest.csv on a dry run).

What it does (user decisions of 2026-11-26):
 1. Duplicates -> _removed_ (each one is checked sample-for-sample against the copy that is kept;
    anything that is not identical is reported and left alone):
      * unmatched/<year>/XX/<DAS serial>/ : RT130 data still under the DAS serial
        (91F8 = BHP2 2018-288, 9338 = BHP4.00 2019-085, 9406 = BHP5.10/20 2019-183..197, 9BC5 = 2019-100)
      * unmatched/2020/1R/FIREP/EL? 2020-346 : same samples as FIREP EH?
      * unmatched/2019/1R/BHP8/ : identical copies of the main-tree BHP8 files
      * 2019/1R/BHP8 2019-101..176 : DAS 9BC5 after it moved to BHP7; identical to BHP7.10
 2. BHP8 2019-100 (DAS 9BC5 on the day it was installed at BHP7, no BHP7.10 file that day) is
    relabelled 1R.BHP7.10 (KSC.xml's BHP7.10 epoch now starts 2019-04-10).
 3. Files in unmatched/ whose channel-day has an epoch in KSC.xml are moved into the main tree
    (BHP2 2018-288, JPK1/JPK2 2016-036, ...). If the main tree already has an identical file, the
    unmatched copy goes to _removed_ instead.
 4. XA.MTEGL (2022): every file named day N holds day N+1 (records start ~0.25 s before midnight), so
    ObsPy's SDS client misses them. All MTEGL files of a channel are merged and re-split at UTC
    midnight into correctly named files (same FLOAT32 encoding and record length; lossless).
Left alone in unmatched/: empty inputs (BCHH1 DD3, BCHH4 HD3, S39A3 HD2/HD3, SON1), CARL1/SCMN and the
2016-02-20..23 BCHH bench test (Tampa), SF.LLS02, RB268 floats, BCHH2 2017-318 H-codes, Raspberry Shakes.
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
from obspy import Stream, UTCDateTime, read, read_inventory

HERE = Path(__file__).resolve().parent
TRASH_NAME = "_removed_20261126"


def merged(path):
    st = read(str(path))
    st.merge(method=1)
    return st


def identical(a, b, min_overlap=0.99):
    """True if the (single-channel) files have identical samples over >= min_overlap of file a."""
    A, B = merged(a), merged(b)
    if len(A) != 1 or len(B) != 1:
        return False, f"{len(A)}/{len(B)} traces after merge"
    A, B = A[0], B[0]
    if abs(A.stats.sampling_rate - B.stats.sampling_rate) > 1e-6:
        return False, "sample rate differs"
    t0, t1 = max(A.stats.starttime, B.stats.starttime), min(A.stats.endtime, B.stats.endtime)
    if t1 <= t0:
        return False, "no overlap"
    a, b = A.slice(t0, t1).data, B.slice(t0, t1).data
    n = min(len(a), len(b))
    if n < min_overlap * len(A.data):
        return False, f"overlap {n} of {len(A.data)} samples"
    same = np.array_equal(np.ma.filled(a[:n], 0), np.ma.filled(b[:n], 0))
    return same, f"{'identical' if same else 'DIFFERENT'} over {n} samples"


def sds_path(root, net, sta, loc, cha, year, jday):
    return Path(root) / f"{year}" / net / sta / f"{cha}.D" / f"{net}.{sta}.{loc}.{cha}.D.{year}.{jday:03d}"


def parse(p: Path):
    n, s, l, c, _, y, j = p.name.split(".")
    return n, s, l, c, int(y), int(j)


class Plan:
    def __init__(self, sds, apply):
        self.sds, self.apply = Path(sds), apply
        self.trash = self.sds / TRASH_NAME
        self.rows = []

    def log(self, action, src, dst="", check=""):
        self.rows.append(dict(action=action, src=str(src), dst=str(dst), check=check))
        print(f"{'APPLY' if self.apply else 'DRY'} {action:9s} {src} -> {dst} [{check}]")

    def to_trash(self, src, check):
        dst = self.trash / Path(src).relative_to(self.sds)
        self.log("remove", src, dst, check)
        if self.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    def move(self, src, dst, check):
        self.log("move", src, dst, check)
        if self.apply:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    def write(self, st, dst, encoding, reclen, check):
        self.log("write", f"<{len(st)} trace(s), {sum(len(t.data) for t in st)} samples>", dst, check)
        if self.apply:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            tmp = Path(str(dst) + ".tmp")
            st.write(str(tmp), format="MSEED", encoding=encoding, reclen=reclen)
            os.replace(tmp, dst)

    def save(self):
        out = (self.trash / "manifest.csv") if self.apply else Path("fix_sds_ksc_manifest.csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["action", "src", "dst", "check"])
            w.writeheader()
            w.writerows(self.rows)
        print(f"\n{len(self.rows)} actions; manifest: {out}")


def dedupe_serials(plan):
    """unmatched/<y>/XX/<serial>/H0?: find the identical 1R EH? file the same day and remove the XX copy."""
    um = plan.sds / "unmatched"
    for f in sorted(um.glob("*/XX/*/*.D/XX.*")):
        n, s, l, c, y, j = parse(f)
        cands = sorted(plan.sds.glob(f"{y}/1R/*/EH?.D/1R.*.EH?.D.{y}.{j:03d}")) + \
            sorted(um.glob(f"{y}/1R/*/EH?.D/1R.*.EH?.D.{y}.{j:03d}"))
        hit = None
        for g in cands:
            ok, msg = identical(f, g)
            if ok:
                hit = (g, msg)
                break
        if hit:
            plan.to_trash(f, f"duplicate of {hit[0].relative_to(plan.sds)} ({hit[1]})")
        else:
            plan.log("KEEP", f, "", "no identical 1R EH? file that day - check by hand")


def dedupe_pairs(plan):
    um = plan.sds / "unmatched"
    # FIREP EL? 2020-346 = EH?
    for f in sorted(um.glob("2020/1R/FIREP/EL?.D/*")):
        n, s, l, c, y, j = parse(f)
        g = sds_path(plan.sds, n, s, l, "EH" + c[2], y, j)
        ok, msg = identical(f, g) if g.exists() else (False, "no EH? file")
        plan.to_trash(f, f"duplicate of {g.relative_to(plan.sds)} ({msg})") if ok else plan.log("KEEP", f, "", msg)
    # unmatched BHP8 = main BHP8
    for f in sorted(um.glob("2019/1R/BHP8/*.D/*")):
        n, s, l, c, y, j = parse(f)
        g = sds_path(plan.sds, n, s, l, c, y, j)
        ok, msg = identical(f, g) if g.exists() else (False, "no main-tree file")
        plan.to_trash(f, f"duplicate of {g.relative_to(plan.sds)} ({msg})") if ok else plan.log("KEEP", f, "", msg)


def bhp8_after_move(plan):
    """Main-tree BHP8 2019-100..176: DAS 9BC5 at BHP7. Remove if identical to BHP7.10, else relabel."""
    for f in sorted(plan.sds.glob("2019/1R/BHP8/*.D/1R.BHP8.00.*.D.2019.*")):
        n, s, l, c, y, j = parse(f)
        if j < 100:
            continue
        g = sds_path(plan.sds, "1R", "BHP7", "10", c, y, j)
        if g.exists():
            ok, msg = identical(f, g)
            plan.to_trash(f, f"duplicate of {g.relative_to(plan.sds)} ({msg})") if ok else plan.log("KEEP", f, "", msg)
        else:
            st = read(str(f), details=True)
            enc, reclen = st[0].stats.mseed.encoding, st[0].stats.mseed.record_length
            for tr in st:
                tr.stats.station, tr.stats.location = "BHP7", "10"
            plan.write(st, g, enc, reclen, "relabel BHP8 -> BHP7.10 (DAS 9BC5 install day at BHP7)")
            plan.to_trash(f, f"relabelled as {g.relative_to(plan.sds)}")


def promote_covered(plan, xml):
    inv = read_inventory(str(xml))
    ep = defaultdict(list)
    for n in inv:
        for s in n:
            for c in s:
                ep[(n.code, s.code, c.location_code, c.code)].append(
                    (c.start_date, c.end_date or UTCDateTime(2600, 1, 1)))
    um = plan.sds / "unmatched"
    for f in sorted(um.glob("*/*/*/*.D/*")):
        if not f.is_file() or (plan.apply and not f.exists()):
            continue
        n, s, l, c, y, j = parse(f)
        if n == "XX" or (s == "BHP8") or (s == "FIREP" and c.startswith("EL")):
            continue  # handled above
        d0 = UTCDateTime(year=y, julday=j)
        key = (n, s, "" if l == "--" else l, c)
        if not any(a < d0 + 86400 and b > d0 for a, b in ep.get(key, [])):
            continue
        g = sds_path(plan.sds, n, s, l, c, y, j)
        if not g.exists():
            plan.move(f, g, "channel-day has a KSC.xml epoch; no main-tree file")
        else:
            ok, msg = identical(f, g)
            plan.to_trash(f, f"duplicate of {g.relative_to(plan.sds)} ({msg})") if ok else \
                plan.log("KEEP", f, "", f"main tree already has {g.name}: {msg} - check by hand")


def refile_mtegl(plan):
    for chdir in sorted(plan.sds.glob("2022/XA/MTEGL/*.D")):
        files = sorted(chdir.glob("XA.MTEGL.*"))
        if not files:
            continue
        st = Stream()
        for f in files:
            st += read(str(f), details=True)
        enc, reclen = st[0].stats.mseed.encoding, st[0].stats.mseed.record_length
        n_in = sum(len(t.data) for t in st)
        st.sort()
        st.merge(method=1)        # overlapping identical samples collapse; differing ones become masked
        if any(np.ma.is_masked(t.data) for t in st):
            nmask = sum(int(np.ma.count_masked(t.data)) for t in st)
            st = st.split()
            note = f"{nmask} masked samples (gaps or conflicting overlaps) split into separate traces"
        else:
            note = "no gaps or conflicts"
        n_out = sum(len(t.data) for t in st)
        t0 = min(t.stats.starttime for t in st)
        t1 = max(t.stats.endtime for t in st)
        new = {}
        day = UTCDateTime(t0.date)
        while day <= t1:
            part = st.slice(day, day + 86400 - 1e-6, nearest_sample=False)
            part = Stream([t for t in part if len(t.data)])
            if part:
                n, s, l, c = part[0].id.split(".")
                new[sds_path(plan.sds, n, s, l, c, day.year, day.julday)] = part
            day += 86400
        n_split = sum(len(t.data) for p in new.values() for t in p)
        check = f"{len(files)} files, {n_in} samples in, {n_out} after merge, {n_split} in {len(new)} day files; {note}"
        if n_split != n_out:
            plan.log("KEEP", chdir, "", f"sample count mismatch - not re-filed: {check}")
            continue
        for f in files:
            plan.to_trash(f, "MTEGL file named one day early; replaced by re-split files")
        for dst, part in new.items():
            plan.write(part, dst, enc, reclen, check)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sds", required=True, help="path to remastered SDS_KSC")
    ap.add_argument("--xml", default=str(HERE.parent / "KSC.xml"))
    ap.add_argument("--apply", action="store_true", help="make the changes (default: dry run)")
    a = ap.parse_args()
    plan = Plan(a.sds, a.apply)
    dedupe_serials(plan)
    dedupe_pairs(plan)
    bhp8_after_move(plan)
    promote_covered(plan, a.xml)
    refile_mtegl(plan)
    plan.save()


if __name__ == "__main__":
    main()
