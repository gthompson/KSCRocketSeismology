"""2026 check: Artemis II peaks corrected with the new KSC.xml vs ksclib's Centaur/Gem/SmartSolo path.

The ensemble's 2026 era corrects with Centaur response files + infraBSU stage, gemlog and the
SmartSolo PAZ (ksclib.instrument_correct). The rebuilt StationXML encodes the same responses, so
per-channel peaks should agree to within a few per cent. Writes compare_2026_artemis2.csv.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import read_inventory

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ksclib" / "src"))
from ksclib import catalog_events as ce  # noqa: E402

warnings.filterwarnings("ignore")
XML = sys.argv[1] if len(sys.argv) > 1 else str(REPO / "03_stationxml" / "KSC.xml")

ens = ce.load_ensemble(REPO / "07_ensemble_paper" / "ensemble.yaml")
cat = ce.load_catalog(ens)
row = cat.set_index("event_id").loc["artemis2-20260401"].copy()
row["event_id"] = "artemis2-20260401"
ev = ce.event_from_row(row, ens)
t0 = ev.origin_time
raw = ce.read_raw(ev, starttime=t0 - 400, endtime=t0 + 330)
stations = ce.station_table(ev)
clips = ce.clip_intervals(raw, ev)
a = ce.correct(raw, ev)                                   # ksclib 2026 path
pa = ce.peak_amplitudes(a, ev, stations, clips, signal=(-30, 300), noise=(-330, -30))

inv = read_inventory(XML)
b = raw.copy()
from flovopy.ingest.gem_overflow import repair_gem_overflow  # noqa: E402
out = []
for tr in b.split():
    if tr.stats.npts < 2 * tr.stats.sampling_rate:
        continue
    t = tr.copy()
    try:
        resp = inv.get_response(t.id, t.stats.starttime)
    except Exception:
        continue
    if t.stats.channel.startswith("HD"):
        t = repair_gem_overflow(t)
    u = resp.instrument_sensitivity.input_units.upper()
    t.detrend("linear")
    nyq = 0.5 * t.stats.sampling_rate
    t.remove_response(inventory=inv, output="VEL" if u == "M/S" else "DEF", zero_mean=True, taper=True,
                      pre_filt=(0.01, 0.02, 0.94 * nyq, 0.98 * nyq))
    t.stats.units = "Pa" if u == "PA" else "m/s"
    out.append(t)
from obspy import Stream  # noqa: E402
pb = ce.peak_amplitudes(Stream(out), ev, stations, clips, signal=(-30, 300), noise=(-330, -30))
m = pa[["seed_id", "kind", "peak", "snr"]].merge(pb[["seed_id", "peak"]], on="seed_id", suffixes=("_ksclib", "_newxml"))
m["ratio_newxml_over_ksclib"] = m.peak_newxml / m.peak_ksclib
m.to_csv(HERE / "compare_2026_artemis2.csv", index=False)
pd.set_option("display.width", 200)
print(m.sort_values("seed_id").round(4).to_string(index=False))
print("median ratio by kind:", m.groupby("kind").ratio_newxml_over_ksclib.median().round(4).to_dict())
print("channels in ksclib path but not in new XML:", sorted(set(pa.seed_id) - set(pb.seed_id)))
