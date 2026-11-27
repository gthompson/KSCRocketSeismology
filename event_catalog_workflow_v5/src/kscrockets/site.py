"""Static web pages for the event catalog: an index of every event and one page per event.

    ksc-rockets build-site                     # -> <out_root>/site/index.html

The site is written next to the per-event products (``<out_root>/site/``) and links to their plots
and miniSEED files by relative path, so it opens from disk (``file://``) and can be copied, with
the event folders, to any web server. Everything comes from the sqlite catalog: ``events``,
``event_waveform_availability``, and the run tables loaded by ``kscrockets.products``. Events
with no recordings still get a page (catalog details, times, links), ready for regional data,
webcasts and weather later.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from html import escape
from pathlib import Path

import pandas as pd

# per-channel columns of the event page: (metric, header, scale, format)
PRESSURE_COLUMNS = [("peak", "peak (Pa)", 1, "{:.3g}"), ("spl_peak_db", "SPL peak (dB)", 1, "{:.1f}"),
                    ("sel_db", "SEL (dB)", 1, "{:.1f}"), ("snr_peak", "SNR", 1, "{:.0f}"),
                    ("f_dominant_hz", "f dom (Hz)", 1, "{:.2g}"), ("duration_5_95_s", "dur 5–95 (s)", 1, "{:.0f}"),
                    ("t_peak_s", "t peak (s)", 1, "{:.1f}")]
SEISMIC_COLUMNS = [("pgv", "PGV (mm/s)", 1e3, "{:.3g}"), ("pga", "PGA (mm/s²)", 1e3, "{:.3g}"),
                   ("snr_peak", "SNR", 1, "{:.0f}"), ("f_dominant_hz", "f dom (Hz)", 1, "{:.2g}"),
                   ("duration_5_95_s", "dur 5–95 (s)", 1, "{:.0f}"), ("t_peak_s", "t peak (s)", 1, "{:.1f}")]
TYPE_LABELS = {"orbital_launch": "Orbital launch", "launch_failure": "Launch failure", "pad_explosion": "Pad explosion",
               "aborted_launch": "Aborted launch", "suborbital_launch": "Suborbital launch", "air_launch": "Air launch",
               "scrub": "Scrub", "pad_abort": "Pad abort", "booster_landing": "Booster landing",
               "reentry_sonic_boom": "Reentry sonic boom", "aircraft_sonic_boom": "Aircraft sonic boom",
               "bolide": "Bolide", "static_fire": "Static fire", "wet_dress_rehearsal": "Wet dress rehearsal",
               "ground_test": "Ground test", "rollout": "Rollout", "rollback": "Rollback", "crawler_move": "Crawler move"}


def _t(v) -> str:
    """Escaped text; '' for None/NaN."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return escape(str(v))


def _num(v, fmt="{:.3g}", scale=1.0) -> str:
    try:
        x = float(v) * scale
    except (TypeError, ValueError):
        return ""
    return "" if math.isnan(x) else fmt.format(x)


def _when(v) -> str:
    s = _t(v)
    return s.replace("T", " ").replace("Z", "").split(".")[0]


def _query(con, sql) -> pd.DataFrame:
    try:
        return pd.read_sql(sql, con)
    except Exception:            # table not loaded (no run yet, or drive not mounted)
        return pd.DataFrame()


def load_site_data(db_path) -> dict:
    with sqlite3.connect(db_path) as con:
        d = dict(events=_query(con, "SELECT * FROM events ORDER BY event_time_utc"),
                 avail=_query(con, "SELECT * FROM event_waveform_availability"),
                 proc=_query(con, "SELECT * FROM event_processing"),
                 meas=_query(con, "SELECT * FROM measurements"),
                 onsets=_query(con, "SELECT * FROM onsets"),
                 products=_query(con, "SELECT * FROM event_products"),
                 runs=_query(con, "SELECT * FROM processing_runs"),
                 links=_query(con, "SELECT * FROM event_links"),
                 weather=_query(con, "SELECT * FROM event_weather"))
    for k in ("avail", "proc", "products", "links", "weather"):
        if d[k].empty:
            d[k] = pd.DataFrame(columns=["event_id"])
    pads = Path(__file__).resolve().parents[2] / "data/raw/launchpads.csv"
    d["pads"] = pd.read_csv(pads).set_index("pad") if pads.exists() else pd.DataFrame()
    return d


LEAFLET = ("<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>"
           "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>")


def _event_dir(prods: pd.DataFrame) -> Path | None:
    m = prods[prods.product_type == "manifest"]
    return Path(m.path.iloc[0]).parent if len(m) else None


def _map_data(e, d, prods, meas, wx) -> dict | None:
    """Pad, stations (with their best SNR per kind) and weather sites for the event map."""
    pad = d["pads"].loc[e.pad] if len(d["pads"]) and e.pad in d["pads"].index else None
    edir = _event_dir(prods)
    st = pd.read_csv(edir / "stations.csv") if edir is not None and (edir / "stations.csv").exists() else pd.DataFrame()
    if pad is None and st.empty:
        return None
    best = {}
    if len(meas):
        m = meas[meas.metric == "snr_peak"].assign(value=lambda x: pd.to_numeric(x.value, errors="coerce"))
        for (sta, kind), v in m.groupby(["station", "kind"]).value.max().items():
            k = "pressure" if kind == "pressure" else "seismic"
            best.setdefault(sta, {})[k] = max(best.get(sta, {}).get(k, 0), float(v))
    stations = []
    for r in (st.dropna(subset=["lat", "lon"]) if {"lat", "lon"} <= set(st.columns) else st.iloc[0:0]).itertuples():
        b = best.get(r.station, {})
        stations.append(dict(name=r.station, net=getattr(r, "network", ""), lat=r.lat, lon=r.lon, km=round(float(r.distance_km), 2),
                             p=round(b.get("pressure", 0), 1), s=round(b.get("seismic", 0), 1)))
    sites = []
    if wx is not None:
        if _t(wx.get("near_tower_lat")):
            sites.append(dict(name=f"Tower {wx.get('near_tower')}", lat=float(wx["near_tower_lat"]), lon=float(wx["near_tower_lon"]),
                              kind="tower"))
        if _t(wx.get("airport_lat")):
            sites.append(dict(name=f"Airport K{wx.get('airport')}", lat=float(wx["airport_lat"]), lon=float(wx["airport_lon"]), kind="airport"))
    return dict(pad=dict(name=e.pad, lat=float(pad.lat), lon=float(pad.lon)) if pad is not None else None,
                stations=stations, sites=sites)


def _wind(speed, frm) -> str:
    sp = _num(speed, "{:.1f} m/s")
    return f"{sp} from {_num(frm, '{:.0f}')}°" if sp and _num(frm) else sp


def _offset(s) -> str:
    try:
        x = float(s)
    except (TypeError, ValueError):
        return ""
    return f"{x:+.0f} s" if abs(x) < 120 else f"{x / 60:+.0f} min"


def _weather_block(wx) -> str:
    if wx is None:
        return "<p class='muted'>Not fetched yet (<code>ksc-rockets fetch-weather</code>).</p>"
    rows = []
    if _t(wx.get("tower_obs_utc")):
        rows.append(("KSC towers, mean of lowest sensors",
                     f"{_t(wx.get('tower_n'))} towers · {_t(wx.get('tower_product'))}",
                     _when(wx.get("tower_obs_utc")), _offset(wx.get("tower_offset_s")),
                     _num(wx.get("tower_temp_c"), "{:.1f} °C"), _num(wx.get("tower_rh_pct"), "{:.0f} %"),
                     _wind(wx.get("tower_wind_speed_mps"), wx.get("tower_wind_from_deg")) +
                     (f" <span class='muted'>({_t(wx.get('tower_wind_heights_ft'))} ft)</span>" if _t(wx.get("tower_wind_heights_ft")) else "")))
    if _t(wx.get("near_tower")):
        rows.append((f"Tower {_t(wx.get('near_tower'))}, nearest the pad",
                     _num(wx.get("near_tower_km"), "{:.1f} km from the pad"),
                     _when(wx.get("tower_obs_utc")), _offset(wx.get("tower_offset_s")),
                     _num(wx.get("near_tower_temp_c"), "{:.1f} °C"), _num(wx.get("near_tower_rh_pct"), "{:.0f} %"),
                     _wind(wx.get("near_tower_wind_speed_mps"), wx.get("near_tower_wind_from_deg")) +
                     (f" <span class='muted'>({_t(wx.get('near_tower_wind_height_ft'))} ft)</span>" if _t(wx.get("near_tower_wind_height_ft")) else "")))
    if _t(wx.get("airport")):
        rows.append((f"Airport K{_t(wx.get('airport'))} (METAR)", f"<code class='small'>{_t(wx.get('airport_metar'))}</code>",
                     _when(wx.get("airport_obs_utc")), _offset(wx.get("airport_offset_s")),
                     _num(wx.get("airport_temp_c"), "{:.1f} °C"), _num(wx.get("airport_rh_pct"), "{:.0f} %"),
                     _wind(wx.get("airport_wind_speed_mps"), wx.get("airport_wind_from_deg")) + " <span class='muted'>(10 m)</span>"))
    if not rows:
        return f"<p class='muted'>No weather data found near this time. {_t(wx.get('error'))}</p>"
    tr = "".join(f"<tr><td>{a}<div class='muted small'>{b}</div></td><td class='nowrap'>{c}</td><td class='num'>{o}</td>"
                 f"<td class='num'>{t}</td><td class='num'>{h}</td><td>{w}</td></tr>" for a, b, c, o, t, h, w in rows)
    prof = _t(wx.get("profiler_files"))
    note = (f"<p class='muted small'>Wind profiler files saved for later analysis: {prof.replace(';', ', ')}.</p>" if prof else "")
    err = f"<p class='muted small'>{_t(wx.get('error'))}</p>" if _t(wx.get("error")) else ""
    return ("<div class='tablewrap'><table><thead><tr><th>Source</th><th>Observed (UTC)</th><th class='num'>from event</th>"
            "<th class='num'>Temp.</th><th class='num'>RH</th><th>Wind</th></tr></thead>"
            f"<tbody>{tr}</tbody></table></div>"
            "<p class='muted small'>Closest observation in time. Towers: KSC Spaceport Weather Archive (not quality controlled); "
            "wind direction is where it blows from. Airports: Iowa Environmental Mesonet ASOS.</p>" + note + err)


def event_summary(meas: pd.DataFrame) -> pd.DataFrame:
    """Per event: strongest pressure (Pa, SPL dB) and seismic (PGV m/s) amplitude among channels
    with SNR >= 3, and whether the strongest pressure is a lower bound (Gem overflow)."""
    cols = ["event_id", "max_pa", "max_spl_db", "max_pa_lower_bound", "max_pgv", "n_sta_pressure", "n_sta_seismic"]
    if meas.empty:
        return pd.DataFrame(columns=cols)
    m = meas.copy()
    m["value"] = pd.to_numeric(m["value"], errors="coerce")
    key = ["event_id", "seed_id"]
    snr = m[m.metric == "snr_peak"].set_index(key).value
    good = snr[snr >= 3].index
    w = m.set_index(key)
    w = w[w.index.isin(good)].reset_index()
    out = []
    for eid, g in w.groupby("event_id"):
        p = g[(g.kind == "pressure") & (g.metric == "peak")]
        spl = g[(g.kind == "pressure") & (g.metric == "spl_peak_db")]
        s = g[g.kind.str.startswith("seismic_") & (g.metric == "pgv")]
        top = p.loc[p.value.idxmax()] if len(p) else None
        out.append(dict(event_id=eid, max_pa=top.value if top is not None else float("nan"),
                        max_spl_db=spl.value.max() if len(spl) else float("nan"),
                        max_pa_lower_bound=bool(top is not None and top.get("qc_flag", "") == "lower_bound"),
                        max_pgv=s.value.max() if len(s) else float("nan"),
                        n_sta_pressure=p.station.nunique(), n_sta_seismic=s.station.nunique()))
    return pd.DataFrame(out, columns=cols)


def _rel(path, start) -> str:
    return os.path.relpath(Path(path).expanduser(), start).replace(os.sep, "/")


# ---------------------------------------------------------------------------------------------
# index page

def _index_rows(ev, avail, proc, summ):
    a = avail.set_index("event_id") if len(avail) else pd.DataFrame()
    p = proc.set_index("event_id") if len(proc) else pd.DataFrame()
    s = summ.set_index("event_id") if len(summ) else pd.DataFrame()
    rows, data = [], []
    for e in ev.itertuples():
        eid = e.event_id
        n_sta = int(float(a.at[eid, "n_stations"] or 0)) if eid in a.index else 0
        status = p.at[eid, "status"] if eid in p.index else ""
        det = p.at[eid, "detected_offset_s"] if eid in p.index else ""
        used = str(p.at[eid, "detected_used_by_catalog"]) == "True" if eid in p.index else False
        pa = s.at[eid, "max_pa"] if eid in s.index else float("nan")
        lb = bool(s.at[eid, "max_pa_lower_bound"]) if eid in s.index else False
        spl = s.at[eid, "max_spl_db"] if eid in s.index else float("nan")
        pgv = s.at[eid, "max_pgv"] if eid in s.index else float("nan")
        year = str(e.event_time_utc)[:4]
        title = e.mission if isinstance(e.mission, str) and e.mission else e.name
        det_txt = ""
        if det not in ("", None) and det == det:
            det_txt = f'{float(det):+.1f}' if used else f'<span class="muted" title="not used by the catalog">{float(det):+.1f}</span>'
        data.append(dict(year=year, type=e.event_type, pad=_t(e.pad), vehicle=_t(e.vehicle), data=bool(n_sta),
                         proc=status == "ok", det=bool(det_txt)))
        rows.append(
            f'<tr data-i="{len(rows)}"><td class="nowrap"><a href="events/{eid}.html">{_when(e.event_time_utc)}</a>'
            f'<span class="basis b-{_t(e.event_time_basis)}" title="time from {_t(e.event_time_basis)}: {_t(e.event_time_source)}, precision {_t(e.event_time_precision)}">'
            f'{_t(e.event_time_precision)[:3]}</span></td>'
            f'<td>{_t(TYPE_LABELS.get(e.event_type, e.event_type))}</td><td>{_t(title)}</td><td>{_t(e.vehicle)}</td>'
            f'<td>{_t(e.pad)}</td><td class="num">{n_sta or ""}</td>'
            f'<td class="num" data-v="{_num(spl, "{:.2f}")}">{_num(spl, "{:.0f}")}{"+" if lb else ""}</td>'
            f'<td class="num" data-v="{_num(pa, "{:.6g}")}">{_num(pa)}{"+" if lb else ""}</td>'
            f'<td class="num" data-v="{_num(pgv, "{:.6g}")}">{_num(pgv, scale=1e3)}</td>'
            f'<td class="num">{det_txt}</td></tr>')
    return rows, data


def build_index(d, site: Path, title: str, subtitle: str, summ: pd.DataFrame) -> Path:
    ev = d["events"]
    rows, data = _index_rows(ev, d["avail"], d["proc"], summ)
    years = sorted(ev.event_time_utc.str[:4].unique())
    types = sorted(ev.event_type.unique(), key=lambda t: list(TYPE_LABELS).index(t) if t in TYPE_LABELS else 99)
    pads = sorted(ev["pad"].fillna("").astype(str).unique())
    opt = lambda vals, lab=lambda v: v: "".join(f'<option value="{_t(v)}">{_t(lab(v))}</option>' for v in vals if v)  # noqa: E731
    n_data = sum(x["data"] for x in data); n_proc = sum(x["proc"] for x in data)
    body = f"""
<header><h1>{_t(title)}</h1><p>{_t(subtitle)}</p>
<p class="summary">{len(ev)} events, {years[0]}–{years[-1]} · {n_data} with waveform data in our archives · {n_proc} processed</p></header>
<section class="filters">
 <input id="q" type="search" placeholder="Search name, vehicle, pad, id">
 <select id="f-year"><option value="">All years</option>{opt(years)}</select>
 <select id="f-type"><option value="">All types</option>{opt(types, lambda t: TYPE_LABELS.get(t, t))}</select>
 <select id="f-pad"><option value="">All pads</option>{opt(pads)}</select>
 <select id="f-data"><option value="">All events</option><option value="data">With waveform data</option>
   <option value="proc">Processed</option><option value="det">Detected time</option></select>
 <span id="count" class="muted"></span>
</section>
<div class="tablewrap"><table id="catalog" class="sortable">
<thead><tr><th>UTC</th><th>Type</th><th>Name</th><th>Vehicle</th><th>Pad</th><th class="num" title="stations with data in the archive">Sta</th>
<th class="num" title="strongest SPL peak among pressure channels with SNR ≥ 3 (+ = lower bound, sensor overflow)">SPL dB</th>
<th class="num" title="strongest pressure peak, Pa">Pa</th><th class="num" title="strongest PGV among seismic channels with SNR ≥ 3, mm/s">PGV mm/s</th>
<th class="num" title="detected source time minus catalog time, s (grey = not used by the catalog)">Det. s</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="muted small">Times: <span class="basis b-consensus">sec</span> source catalogs, <span class="basis b-detected">min</span> detected on our records, <span class="basis b-known">sec</span> known (webcast, release). Amplitudes are provisional until the StationXML gains are final.</p>
<script>const ROWS={json.dumps(data)};</script>
<script src="assets/app.js"></script>"""
    p = site / "index.html"
    p.write_text(_page(title, body, "assets/style.css"))
    return p


# ---------------------------------------------------------------------------------------------
# event page

def _dl(pairs) -> str:
    return "<dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in pairs if v not in ("", None)) + "</dl>"


def _times_table(e) -> str:
    rows = [("Event time (best)", e.event_time_utc, f"{_t(e.event_time_basis)}: {_t(e.event_time_source)}", e.event_time_precision),
            ("Source consensus", e.consensus_time_utc, e.consensus_time_source, e.consensus_time_precision),
            ("Known", e.known_time_utc, e.known_time_source, ""),
            ("Detected (our records)", e.detected_time_utc, e.detected_time_method, ""),
            ("Window start", e.window_start_utc, "", ""), ("Window end", e.window_end_utc, "", ""),
            ("Event end", e.event_end_utc, e.route, "")]
    tr = "".join(f"<tr><td>{k}</td><td class='nowrap'>{_when(t)}</td><td>{_t(src)}</td><td>{_t(pr)}</td></tr>"
                 for k, t, src, pr in rows if _t(t))
    return (f"<div class='tablewrap'><table><thead><tr><th></th><th>UTC</th><th>Source</th><th>Precision</th></tr></thead>"
            f"<tbody>{tr}</tbody></table></div>")


def _channel_table(meas: pd.DataFrame, kind: str) -> str:
    cols = PRESSURE_COLUMNS if kind == "pressure" else SEISMIC_COLUMNS
    m = meas[meas.kind.str.startswith(kind)] if kind != "pressure" else meas[meas.kind == "pressure"]
    m = m[m.kind != "seismic_vector"]
    if m.empty:
        return ""
    m = m.assign(value=pd.to_numeric(m.value, errors="coerce"), distance_km=pd.to_numeric(m.distance_km, errors="coerce"))
    wide = m.pivot_table(index=["seed_id", "station", "channel", "distance_km"], columns="metric", values="value", aggfunc="first")
    flags = m.groupby("seed_id").qc_flag.agg(lambda s: ",".join(sorted({x for x in s if isinstance(x, str) and x})))
    head = "".join(f"<th class='num'>{h}</th>" for _, h, _, _ in cols)
    trs = []
    for (sid, sta, cha, dist), r in wide.sort_values("distance_km").sort_index(level="distance_km", sort_remaining=False).iterrows():
        flag = flags.get(sid, "")
        cls = " class='weak'" if "low_snr" in flag else ""
        cells = "".join(f"<td class='num'>{_num(r.get(k), f, s)}{'+' if k in ('peak', 'spl_peak_db', 'sel_db') and 'lower_bound' in flag else ''}</td>"
                        for k, _, s, f in cols)
        trs.append(f"<tr{cls}><td><a href='#sta-{_t(sta)}'>{_t(sta)}</a></td><td>{_t(cha)}</td>"
                   f"<td class='num'>{_num(dist, '{:.2f}')}</td>{cells}<td>{_t(flag)}</td></tr>")
    return (f"<div class='tablewrap'><table class='sortable'><thead><tr><th>Station</th><th>Channel</th><th class='num'>km</th>{head}"
            f"<th>QC</th></tr></thead><tbody>{''.join(trs)}</tbody></table></div>")


def _onset_table(on: pd.DataFrame) -> str:
    if on.empty:
        return ""
    on = on.assign(distance_km=pd.to_numeric(on.distance_km, errors="coerce")).sort_values("distance_km")
    trs = "".join(f"<tr><td>{_t(r.station)}</td><td>{_t(r.channel)}</td><td>{_t(r.kind)}</td><td class='num'>{_num(r.distance_km, '{:.2f}')}</td>"
                  f"<td class='num'>{_num(r.onset_s, '{:+.2f}')}</td><td class='num'>{_num(r.origin_est_s, '{:+.2f}')}</td>"
                  f"<td class='num'>{_num(r.max_ratio, '{:.1f}')}</td></tr>" for r in on.itertuples())
    return ("<details><summary>STA/LTA onsets per channel</summary><div class='tablewrap'><table class='sortable'><thead><tr><th>Station</th>"
            "<th>Channel</th><th>Kind</th><th class='num'>km</th><th class='num'>onset (s)</th><th class='num'>origin est. (s)</th>"
            f"<th class='num'>STA/LTA</th></tr></thead><tbody>{trs}</tbody></table></div></details>")


def _detected_block(p) -> str:
    if p is None or not _t(p.get("detected_time_utc")):
        return "<p class='muted'>No source time detected on these records.</p>"
    used = str(p.get("detected_used_by_catalog")) == "True"
    verdict = ("<strong>used by the catalog</strong> (as the event time only where the source time is coarser than a second)"
               if used else f"<strong>not used by the catalog</strong>: {_t(p.get('detected_not_used_reason'))}")
    return _dl([("Detected source time", _t(p.get("detected_time_utc"))),
                ("Offset from catalog", _num(p.get("detected_offset_s"), "{:+.2f} s")),
                ("Stations / nearest", f"{_t(p.get('detected_n_stations'))} / {_num(p.get('detected_nearest_km'), '{:.1f} km')}"),
                ("Strongest rival arrival", _num(p.get("detected_rival_ratio"), "{:.2f} × the chosen one")),
                ("Status", verdict)])


def build_event_page(e, d, site: Path, out_root: Path, prev_id, next_id) -> Path:
    eid = e.event_id
    edir = site / "events"
    a = d["avail"][d["avail"].event_id == eid]
    p = d["proc"][d["proc"].event_id == eid]
    p = p.iloc[0] if len(p) else None
    meas = d["meas"][d["meas"].event_id == eid] if len(d["meas"]) else pd.DataFrame()
    on = d["onsets"][d["onsets"].event_id == eid] if len(d["onsets"]) else pd.DataFrame()
    prods = d["products"][d["products"].event_id == eid]
    links = d["links"][d["links"].event_id == eid]
    w = d["weather"][d["weather"].event_id == eid]
    wx = w.iloc[0].to_dict() if len(w) else None
    title = e.mission if isinstance(e.mission, str) and e.mission else e.name
    nav = (f"<nav><a href='../index.html'>← All events</a>"
           + (f" · <a href='{prev_id}.html'>‹ previous</a>" if prev_id else "")
           + (f" · <a href='{next_id}.html'>next ›</a>" if next_id else "") + "</nav>")
    src_link = f"<a href='{_t(e.source_url)}'>{_t(e.source)}</a>" if _t(e.source_url) else _t(e.source)
    facts = _dl([("Type", _t(TYPE_LABELS.get(e.event_type, e.event_type))), ("Vehicle", _t(e.vehicle)),
                 ("Pad", _t(e.pad)), ("Provider", _t(e.provider)), ("Launch designator", _t(e.launch_designator)),
                 ("Outcome", {"True": "success", "False": "failure"}.get(str(e.launch_success), "")),
                 ("Landing", " ".join(x for x in (_t(e.landing_type), _t(e.landing_pad)) if x)
                  + ({"True": " (landed)", "False": " (not landed)"}.get(str(e.landing_success), "") if _t(e.landing_attempt) == "True" else "")),
                 ("Sources", f"{src_link} ({_t(e.source_count)})" if _t(e.source_count) else src_link),
                 ("Notes", _t(e.notes)), ("Event id", f"<code>{eid}</code>")])
    parts = [nav, f"<h1>{_t(title)}</h1>",
             f"<p class='lede'>{_t(TYPE_LABELS.get(e.event_type, e.event_type))} · {_when(e.event_time_utc)} UTC · {_t(e.pad)}</p>",
             "<div class='cols'><section>", "<h2>Event</h2>", facts, "</section><section><h2>Times</h2>", _times_table(e), "</section></div>"]
    mp = _map_data(e, d, prods, meas, wx)
    if mp and mp["stations"]:
        parts.append("<h2>Stations</h2><div id='map' class='map'></div>"
                     "<p class='muted small'>Stations that recorded this event, coloured by their best peak SNR "
                     "(<span class='dot d-p'></span> pressure SNR ≥ 3, <span class='dot d-s'></span> seismic only, "
                     "<span class='dot d-n'></span> neither); ★ pad; ◆ weather tower and airport used below.</p>"
                     f"<script>const EVENT_MAP={json.dumps(mp)};</script>")
    parts.append("<h2>Weather</h2>" + _weather_block(wx))
    # waveform data
    parts.append("<h2>Our recordings</h2>")
    n_sta = int(float(a.n_stations.iloc[0] or 0)) if len(a) else 0
    if not n_sta:
        parts.append("<p class='muted'>No day files in our archives for this event. Regional (FDSN) data may be added later.</p>")
    else:
        parts.append(_dl([("Archive", _t(a.archive.iloc[0])), ("Stations with day files", f"{n_sta}: {_t(a.stations.iloc[0]).replace(';', ', ')}")]))
    if p is None and n_sta:
        parts.append("<p class='muted'>Not processed yet.</p>")
    if p is not None:
        parts.append(_dl([("Processing", f"{_t(p.get('status'))} (run {_t(p.get('run_id'))})" + (f": {_t(p.get('error'))}" if _t(p.get('error')) else "")),
                          ("Channels", f"{_t(p.get('n_raw'))} read, {_t(p.get('n_corrected'))} response-corrected, {_t(p.get('n_metric_channels'))} with metrics")]))
        parts.append("<h3>Detected source time</h3>" + _detected_block(p))
        plots = {r.product_type: r.path for r in prods.itertuples() if r.product_type.startswith("record_section")}
        if plots:
            parts.append("<h3>Record sections</h3><div class='plots'>" + "".join(
                f"<figure><a href='{_rel(v, edir)}'><img loading='lazy' src='{_rel(v, edir)}' alt='{k}'></a>"
                f"<figcaption>{'Pressure' if 'pressure' in k else 'Seismic vertical'}</figcaption></figure>"
                for k, v in sorted(plots.items())) + "</div>")
        if len(meas):
            parts.append("<h3>Pressure channels</h3>" + (_channel_table(meas, "pressure") or "<p class='muted'>none</p>"))
            parts.append("<h3>Seismic channels</h3>" + (_channel_table(meas, "seismic") or "<p class='muted'>none</p>"))
            parts.append("<p class='muted small'>Grey rows: SNR below 3. + : lower bound (sensor overflow). Signal window −30 to +300 s from the event time; "
                         "amplitudes are provisional until the StationXML gains are final.</p>")
        parts.append(_onset_table(on))
        st = prods[prods.product_type == "station_waveform_spectrogram"]
        if len(st):
            st = st.assign(dist=st.station.map(meas.groupby("station").distance_km.first().astype(float) if len(meas) else {})).sort_values("dist")
            parts.append("<h3>Stations: waveform and spectrogram</h3><div class='plots stations'>" + "".join(
                f"<figure id='sta-{_t(r.station)}'><a href='{_rel(r.path, edir)}'><img loading='lazy' src='{_rel(r.path, edir)}' alt='{_t(r.station)}'></a>"
                f"<figcaption>{_t(r.station)}{_num(r.dist, ' · {:.1f} km')}</figcaption></figure>" for r in st.itertuples()) + "</div>")
        files = prods[prods.product_type.isin(["raw_counts_mseed", "corrected_mseed", "manifest"])]
        if len(files):
            parts.append("<h3>Files</h3><ul>" + "".join(f"<li><a href='{_rel(r.path, edir)}'>{_t(Path(r.path).name)}</a> ({_t(r.product_type)})</li>"
                                                     for r in files.itertuples()) + "</ul>")
    parts.append("<h2>Links</h2>")
    if len(links):
        parts.append("<ul>" + "".join(f"<li><a href='{_t(r.url)}'>{_t(r.title) or _t(r.url)}</a> <span class='muted'>{_t(r.link_type)}</span></li>"
                                      for r in links.itertuples()) + "</ul>")
    else:
        parts.append("<p class='muted'>None yet (webcasts, weather and regional data will be added here).</p>")
    parts.append(nav)
    path = edir / f"{eid}.html"
    path.write_text(_page(f"{title} · {_when(e.event_time_utc)[:10]}", "\n".join(parts), "../assets/style.css", "../assets/app.js",
                          head=LEAFLET if mp and mp["stations"] else ""))
    return path


def _page(title, body, css, js=None, head="") -> str:
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_t(title)}</title>{head}<link rel='stylesheet' href='{css}'></head><body><main>{body}</main>"
            + (f"<script src='{js}'></script>" if js else "") + "</body></html>")


def build_site(db_path, out_root, site_dir=None, title="KSC Rocket Seismology Event Catalog", subtitle="", event_ids=None) -> Path:
    """Write <out_root>/site/: index of all events, and a page per event (`event_ids` limits the event pages)."""
    out_root = Path(out_root).expanduser()
    site = Path(site_dir).expanduser() if site_dir else out_root / "site"
    (site / "events").mkdir(parents=True, exist_ok=True)
    (site / "assets").mkdir(exist_ok=True)
    for name in ("style.css", "app.js"):
        (site / "assets" / name).write_text((Path(__file__).parent / "site_assets" / name).read_text())
    d = load_site_data(db_path)
    summ = event_summary(d["meas"])
    index = build_index(d, site, title, subtitle, summ)
    ev = d["events"]
    ids = list(ev.event_id)
    want = set(event_ids) if event_ids else set(ids)
    for i, e in enumerate(ev.itertuples()):
        if e.event_id in want:
            build_event_page(e, d, site, out_root, ids[i - 1] if i else None, ids[i + 1] if i + 1 < len(ids) else None)
    return index
