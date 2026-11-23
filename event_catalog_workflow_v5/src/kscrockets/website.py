from __future__ import annotations
from pathlib import Path
from html import escape
import json, shutil
import pandas as pd
from .catalog import read_catalog
from .metrics import read_metrics_index, catalog_metric_summary


def _txt(v):
    if pd.isna(v): return ""
    return escape(str(v))


def build_website(catalog_csv, outdir, metrics_index=None, title="KSC Rocket Seismology Event Catalog", subtitle=""):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True); (outdir/"events").mkdir(exist_ok=True)
    df=read_catalog(catalog_csv)
    if metrics_index:
        df=catalog_metric_summary(df,read_metrics_index(metrics_index))
    else: df["has_metrics"]=False
    rows=[]
    for _,r in df.sort_values("time_utc",ascending=False).iterrows():
        eid=str(r.event_id); when=r.time_utc.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(r.time_utc) else ""
        rows.append(f'<tr data-year="{r.time_utc.year if pd.notna(r.time_utc) else ""}" data-vehicle="{_txt(r.vehicle)}" data-pad="{_txt(r.pad)}"><td><a href="events/{eid}.html">{when}</a></td><td>{_txt(r.vehicle)}</td><td>{_txt(r.mission)}</td><td>{_txt(r.pad)}</td><td>{"yes" if bool(r.get("has_metrics",False)) else ""}</td></tr>')
        detail=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="../assets/style.css"><title>{_txt(r.mission)}</title></head><body><main><p><a href="../index.html">← Catalog</a></p><h1>{_txt(r.vehicle)}</h1><h2>{_txt(r.mission)}</h2><dl><dt>UTC</dt><dd>{when}</dd><dt>Launch designator</dt><dd>{_txt(r.launch_designator)}</dd><dt>Pad</dt><dd>{_txt(r.pad)}</dd><dt>Provider</dt><dd>{_txt(r.provider)}</dd><dt>Metrics available</dt><dd>{"Yes" if bool(r.get("has_metrics",False)) else "No"}</dd></dl><p class="eventid">{eid}</p></main></body></html>'''
        (outdir/"events"/f"{eid}.html").write_text(detail)
    years=sorted(df.time_utc.dropna().dt.year.unique().tolist())
    vehicles=sorted(df.vehicle.dropna().astype(str).unique().tolist())
    pads=sorted(df["pad"].dropna().astype(str).unique().tolist())
    options=lambda vals: ''.join(f'<option value="{escape(str(v))}">{escape(str(v))}</option>' for v in vals)
    html=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="assets/style.css"><title>{escape(title)}</title></head><body><main><header><h1>{escape(title)}</h1><p>{escape(subtitle)}</p><p class="summary">{len(df)} cataloged launches • {df.time_utc.dt.year.min()}–{df.time_utc.dt.year.max()}</p></header><section class="filters"><input id="q" placeholder="Search mission, vehicle, pad"><select id="year"><option value="">All years</option>{options(years)}</select><select id="vehicle"><option value="">All vehicles</option>{options(vehicles)}</select><select id="pad"><option value="">All pads</option>{options(pads)}</select></section><table id="catalog"><thead><tr><th>UTC</th><th>Vehicle</th><th>Mission</th><th>Pad</th><th>Metrics</th></tr></thead><tbody>{''.join(rows)}</tbody></table></main><script src="assets/app.js"></script></body></html>'''
    (outdir/"index.html").write_text(html)
    (outdir/"catalog.json").write_text(df.assign(time_utc=df.time_utc.astype(str)).to_json(orient="records",indent=2))
    assets=Path(__file__).resolve().parents[2]/"website"/"assets"
    if assets.exists():
        shutil.copytree(assets,outdir/"assets",dirs_exist_ok=True)
    return outdir/"index.html"
