"""Gain tests on the raw-count launch peaks from 10_measure_launch_peaks.py.

Each test converts raw counts with *nominal* sensitivities and asks which setting makes a channel
agree with a reference of known setting:

  T1  RT130 + L-22 geophones (EHZ) vs the co-located Trillium BCHH1 DHZ, 5-20 Hz: gain 1 or 32?
  T2  2016 beach house BCHH: infraBSU 295 (DD1 before the 2016-03-04 swap, DD2 after) vs DD1/DD3.
  T3  Chaparral M25 on a Centaur vs the co-located infraBSU (BCHH1 DD1/DD2, SON1, BCHH4 HDF/HD2,
      BCHH3 HDF vs BCHH2 HD): sensor sensitivity in V/Pa.
  T4  every infrasound channel: distance-reduced pressure p*r against the beach-house references
      (BCHH2 at 1 Vpp; BCHH1 DD2 at 40 Vpp), under 1 Vpp and 40 Vpp.

Writes CSVs to 03_stationxml/audit/ and prints a summary.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from obspy.geodetics import gps2dist_azimuth

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ksclib" / "src"))
from ksclib import catalog_events as ce  # noqa: E402

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 300)
pd.set_option("display.max_columns", 30)

INFRABSU_V_PER_PA = 4.6e-5
CENTAUR_COUNTS_PER_V = 4.0e5          # at 40 Vpp; x40 at 1 Vpp
TRILLIUM = 754.3 * 0.9925 * CENTAUR_COUNTS_PER_V   # counts/(m/s), as the Centaurs write it
L22, RT130 = 62.95, 629129.0           # V/(m/s) (NRL L-22D 2200/10854 Ohm), counts/V at RT130 gain 1
SNR_MIN = 5.0


def infra_counts_per_pa(vpp, v_per_pa=INFRABSU_V_PER_PA):
    return v_per_pa * CENTAUR_COUNTS_PER_V * (40.0 if vpp == 1 else 1.0)


pk = pd.read_csv(HERE / "launch_peaks_counts_2016_2022.csv")
pk["snr_p"] = pk.peak_hp05 / pk.noise_hp05
pk["snr_s"] = pk.peak_bp5_20 / pk.noise_bp5_20
pk["date"] = pk.time.str[:10]


def wide(df, value, snr):
    d = df[df[snr] >= SNR_MIN]
    return d.pivot_table(index=["event_id", "time", "vehicle", "pad"], columns="seed_id", values=value)


# ---------------------------------------------------------------------------------------------
# T1 geophones
# ---------------------------------------------------------------------------------------------
seis = pk[pk.kind == "seismic"]
w = wide(seis, "peak_bp5_20", "snr_s")
rows = []
if "1R.BCHH1.00.DHZ" in w:
    ref = w["1R.BCHH1.00.DHZ"] / TRILLIUM
    for sid in [c for c in w.columns if ".EHZ" in c]:
        r = (w[sid] / (L22 * RT130)) / ref
        for (eid, t, veh, pad), v in r.dropna().items():
            rows.append(dict(event_id=eid, time=t, vehicle=veh, pad=pad, seed_id=sid, ref="1R.BCHH1.00.DHZ",
                             ratio_if_gain1=v, ratio_if_gain32=v / 32.0))
t1 = pd.DataFrame(rows)
t1.to_csv(HERE / "T1_geophone_vs_trillium.csv", index=False)
print("\nT1  geophone EHZ / Trillium BCHH1 DHZ (5-20 Hz, velocity), per channel")
if len(t1):
    s1 = t1.groupby("seed_id").agg(n=("event_id", "size"), median_if_gain1=("ratio_if_gain1", "median"),
                                   median_if_gain32=("ratio_if_gain32", "median"),
                                   p25_if_gain32=("ratio_if_gain32", lambda x: x.quantile(.25)),
                                   p75_if_gain32=("ratio_if_gain32", lambda x: x.quantile(.75)))
    print(s1.round(3))
    print("all channels: median ratio if gain 1 = %.1f ; if gain 32 = %.2f (n=%d)"
          % (t1.ratio_if_gain1.median(), t1.ratio_if_gain32.median(), len(t1)))

# FIREP/TANKP/BHP against DVEL3 DHZ (not co-located): reduced by distance, coarse check only
# (done in T4-style below for pressure; for seismic we just print the raw ratios per launch)
if "1R.DVEL3.00.DHZ" in w:
    ref = w["1R.DVEL3.00.DHZ"] / TRILLIUM
    rr = []
    for sid in [c for c in w.columns if ".EHZ" in c]:
        r = ((w[sid] / (L22 * RT130 * 32)) / ref).dropna()
        if len(r):
            rr.append(dict(seed_id=sid, n=len(r), median_ratio_gain32_vs_DVEL3=r.median()))
    print("\nT1b geophone (gain 32) / DVEL3 DHZ, not co-located (distance not removed):")
    print(pd.DataFrame(rr).round(3).to_string(index=False))

# ---------------------------------------------------------------------------------------------
# T2 2016 BCHH infraBSU 295
# ---------------------------------------------------------------------------------------------
pres = pk[pk.kind == "pressure"]
b = pres[pres.station == "BCHH"].pivot_table(index=["event_id", "time", "vehicle", "location"], columns="channel",
                                             values="peak_hp05")
bs = pres[pres.station == "BCHH"].pivot_table(index=["event_id", "time", "vehicle", "location"], columns="channel",
                                              values="snr_p")
b = b[(bs >= SNR_MIN).all(axis=1)]
b["DD2_over_DD1"] = b.DD2 / b.DD1
b["DD2_over_DD3"] = b.DD2 / b.DD3
b["DD1_over_DD3"] = b.DD1 / b.DD3
b = b.reset_index()
b["sensor_295_on"] = np.where(b.time < "2016-03-04", "DD1", "DD2")
b.to_csv(HERE / "T2_bchh2016_sensor295.csv", index=False)
print("\nT2  BCHH 2016 launch peak ratios (raw counts, all channels 40 Vpp)")
print(b.round(3).to_string(index=False))
after = b[b.sensor_295_on == "DD2"]
corr295 = float(np.median(np.r_[1 / after.DD2_over_DD1, 1 / after.DD2_over_DD3])) if len(after) else np.nan
print(f"sensor 295 (on DD2 after the swap): DD1/DD2 and DD3/DD2 median = {corr295:.2f} over {len(after)} launches")

amb = pd.read_csv(HERE / "ambient_counts.csv")
a16 = amb[amb.station == "BCHH"].pivot(index="day", columns="channel", values="rms_counts").dropna()
a16["DD2_over_DD3"] = a16.DD2 / a16.DD3
a16["DD1_over_DD3"] = a16.DD1 / a16.DD3
print("\nT2b BCHH 2016 night 0.15-0.35 Hz RMS ratios by day (first/last rows):")
print(a16.round(3).head(12).to_string())
print(a16.round(3).tail(5).to_string())

# ---------------------------------------------------------------------------------------------
# T3 Chaparral
# ---------------------------------------------------------------------------------------------
wp = wide(pres, "peak_hp05", "snr_p")
t3 = []
pairs = [("1R.BCHH1.00.DD1", "1R.BCHH1.00.DD2", 40, 40), ("1R.SON1.00.DD1", "1R.SON1.00.DD2", 40, 40),
         ("1R.BCHH4.00.HDF", "1R.BCHH4.00.HD2", 40, 40)]
for chap, inf, vc, vi in pairs:
    if chap in wp and inf in wp:
        r = (wp[chap] / wp[inf]).dropna()
        for (eid, t, veh, pad), v in r.items():
            # counts ratio = (S_chap * G_c) / (S_inf * G_i)  ->  S_chap = ratio * S_inf * G_i / G_c
            t3.append(dict(event_id=eid, time=t, vehicle=veh, chaparral=chap, reference=inf, counts_ratio=v,
                           chaparral_V_per_Pa=v * INFRABSU_V_PER_PA * (40 if vi == 1 else 1) / (40 if vc == 1 else 1)))
# BCHH3 HDF (1 Vpp per its Centaur) against BCHH2 HD4-9 (1 Vpp)
bchh2 = [c for c in wp.columns if c.startswith("1R.BCHH2.00.HD")]
if "1R.BCHH3.00.HDF" in wp and bchh2:
    ref = wp[bchh2].median(axis=1)
    r = (wp["1R.BCHH3.00.HDF"] / ref).dropna()
    for (eid, t, veh, pad), v in r.items():
        t3.append(dict(event_id=eid, time=t, vehicle=veh, chaparral="1R.BCHH3.00.HDF", reference="median BCHH2 HD4-9",
                       counts_ratio=v, chaparral_V_per_Pa=v * INFRABSU_V_PER_PA))
t3 = pd.DataFrame(t3)
t3.to_csv(HERE / "T3_chaparral.csv", index=False)
print("\nT3  Chaparral sensitivity from co-located infraBSU (V/Pa)")
if len(t3):
    print(t3.groupby(["chaparral", "reference"]).chaparral_V_per_Pa.describe()[["count", "25%", "50%", "75%"]])

# ---------------------------------------------------------------------------------------------
# T4 p*r against beach-house references, every infrasound channel
# ---------------------------------------------------------------------------------------------
ens = ce.load_ensemble(REPO / "07_ensemble_paper" / "ensemble.yaml")
cat = ce.load_catalog(ens, extra=False).set_index("event_id")
master = pd.read_excel(REPO / "03_stationxml" / "ksc_stations_master_v3.xlsx", sheet_name="channel_epochs") \
    if (REPO / "03_stationxml" / "ksc_stations_master_v3.xlsx").exists() else None
coords = (pd.read_excel("/Volumes/haldata/KSC/station_metadata/ksc_stations_master_v2.xlsx")
          .groupby("station")[["lat", "lon"]].first())
dist = {}
for eid in pres.event_id.unique():
    try:
        lat0, lon0 = ce.pad_location(ens, cat.loc[eid, "pad_code"] if "pad_code" in cat else cat.loc[eid, "pad"])
    except Exception:
        continue
    for sta, (la, lo) in coords.iterrows():
        dist[(eid, sta)] = gps2dist_azimuth(lat0, lon0, la, lo)[0] / 1000
pres = pres.assign(distance_km=[dist.get((e, s), np.nan) for e, s in zip(pres.event_id, pres.station)])
good = pres[pres.snr_p >= SNR_MIN].copy()

REF40 = {"1R.BCHH1.00.DD2"}
REF1 = {f"1R.BCHH2.00.DD{i}" for i in (4, 5, 6, 9)} | {f"1R.BCHH2.00.HD{i}" for i in (4, 6, 7, 8, 9)}
refrows = []
for eid, g in good.groupby("event_id"):
    for name, ids, vpp in (("BCHH2_1Vpp", REF1, 1), ("BCHH1DD2_40Vpp", REF40, 40)):
        h = g[g.seed_id.isin(ids)]
        if len(h):
            refrows.append(dict(event_id=eid, ref=name,
                                ref_pr=float(np.median(h.peak_hp05 / infra_counts_per_pa(vpp) * h.distance_km))))
refs = pd.DataFrame(refrows).pivot(index="event_id", columns="ref", values="ref_pr")
test = good[~good.seed_id.isin(REF1 | REF40)].join(refs, on="event_id")
test = test[test[[c for c in refs.columns]].notna().any(axis=1)]
for vpp in (40, 1):
    test[f"pr_if_{vpp}Vpp"] = test.peak_hp05 / infra_counts_per_pa(vpp) * test.distance_km
    for ref in refs.columns:
        test[f"ratio_{vpp}Vpp_vs_{ref}"] = test[f"pr_if_{vpp}Vpp"] / test[ref]
test.to_csv(HERE / "T4_reduced_pressure_vs_references.csv", index=False)


def _summ(g):
    out = {"n_launches": g.event_id.nunique(), "first": g.time.min()[:10], "last": g.time.max()[:10]}
    for vpp in (40, 1):
        r = pd.concat([g[c] for c in g.columns if c.startswith(f"ratio_{vpp}Vpp_vs_")]).dropna()
        out[f"median_ratio_if_{vpp}Vpp"] = r.median() if len(r) else np.nan
        out[f"misfit_{vpp}"] = np.median(np.abs(np.log10(r))) if len(r) else np.nan
    out["verdict"] = "1 Vpp" if out["misfit_1"] < out["misfit_40"] else "40 Vpp"
    return pd.Series(out)


s4 = test.groupby("seed_id").apply(_summ)
s4.to_csv(HERE / "T4_summary.csv")
print("\nT4  p*r ratio to beach-house references (1 = agreement), per channel")
print(s4.round(2).to_string())
pairs_ref = refs.dropna()
if len(pairs_ref):
    print("reference consistency BCHH1 DD2 (40 Vpp) / BCHH2 (1 Vpp): median %.2f over %d launches"
          % ((pairs_ref.BCHH1DD2_40Vpp / pairs_ref.BCHH2_1Vpp).median(), len(pairs_ref)))

# RBLAB 2021 (Lucy) and DVEL3 late 2020: launch SNR and peaks in counts
print("\nRB166/RB268/RB383 on 2021-10-16 and DVEL3 Nov-Dec 2020 (raw counts):")
sel = pk[(pk.station.str.startswith("RB") & (pk.time >= "2021")) |
         ((pk.station == "DVEL3") & (pk.time >= "2020-10")) |
         (pk.station.isin(["BCHH1", "BCHH2"]) & (pk.date.isin(["2021-10-16"]) | (pk.time.between("2020-11", "2020-12-12"))))]
print(sel[["time", "vehicle", "seed_id", "peak_hp05", "noise_hp05", "snr_p", "peak_bp5_20", "snr_s"]]
      .sort_values(["time", "seed_id"]).round(1).to_string(index=False))
print("\nambient 2021-10 and 2022 (night 0.15-0.35 Hz RMS counts):")
print(amb[amb.station != "BCHH"].pivot_table(index=["station", "channel"], columns="day", values="rms_counts").round(1))
