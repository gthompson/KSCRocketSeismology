from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from .catalog import read_catalog


def build_ensemble_products(catalog_csv: str | Path, outdir: str | Path, year_min=2016, year_max=2022) -> dict[str, Path]:
    outdir=Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    df=read_catalog(catalog_csv)
    df=df[df.time_utc.dt.year.between(year_min,year_max)].copy()
    df["year"]=df.time_utc.dt.year
    df["family_pad"]=df["vehicle"].astype(str)+" / "+df["pad"].astype(str)
    by_year=df.groupby("year").size().rename("n_launches").reset_index()
    by_vehicle=df.groupby("vehicle").size().rename("n_launches").sort_values(ascending=False).reset_index()
    by_pad=df.groupby("pad").size().rename("n_launches").sort_values(ascending=False).reset_index()
    by_family_pad=df.groupby("family_pad").size().rename("n_launches").sort_values(ascending=False).reset_index()
    paths={}
    for name,table in [("launches_by_year",by_year),("launches_by_vehicle",by_vehicle),("launches_by_pad",by_pad),("launches_by_family_pad",by_family_pad)]:
        p=outdir/f"{name}.csv"; table.to_csv(p,index=False); paths[name]=p

    fig,ax=plt.subplots(figsize=(9,5)); ax.bar(by_year.year.astype(str),by_year.n_launches)
    ax.set(xlabel="Year",ylabel="Number of launches",title=f"KSC/CCSFS launches, {year_min}–{year_max}"); ax.grid(axis="y",alpha=.25)
    fig.tight_layout(); p=outdir/"launches_by_year.png"; fig.savefig(p,dpi=200); plt.close(fig); paths["launches_by_year_plot"]=p

    d=df.sort_values("time_utc").copy(); d["cumulative_launches"]=range(1,len(d)+1)
    fig,ax=plt.subplots(figsize=(10,5)); ax.plot(d.time_utc,d.cumulative_launches)
    ax.set(xlabel="Date (UTC)",ylabel="Cumulative launches",title=f"Cumulative launches, {year_min}–{year_max}"); ax.grid(alpha=.25)
    fig.tight_layout(); p=outdir/"cumulative_launches.png"; fig.savefig(p,dpi=200); plt.close(fig); paths["cumulative_launches_plot"]=p
    d.to_csv(outdir/"ensemble_catalog.csv",index=False,date_format="%Y-%m-%dT%H:%M:%SZ")
    paths["ensemble_catalog"]=outdir/"ensemble_catalog.csv"
    return paths
