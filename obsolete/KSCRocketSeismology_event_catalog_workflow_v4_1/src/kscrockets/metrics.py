from __future__ import annotations
from pathlib import Path
import pandas as pd


def read_metrics_index(path: str | Path) -> pd.DataFrame:
    p=Path(path)
    if not p.exists(): return pd.DataFrame()
    df=pd.read_csv(p)
    if "window_start" in df: df["window_start"]=pd.to_datetime(df["window_start"],utc=True,errors="coerce")
    return df


def catalog_metric_summary(catalog: pd.DataFrame, metrics_index: pd.DataFrame) -> pd.DataFrame:
    out=catalog.copy()
    out["has_metrics"]=False
    out["n_traces"]=pd.NA
    if metrics_index.empty: return out
    mi=metrics_index.copy()
    if "launch_designator" in mi:
        keep=[c for c in ["launch_designator","status","n_traces","trace_csv_path","station_csv_path","mseed_path"] if c in mi]
        mi=mi[keep].drop_duplicates("launch_designator",keep="last")
        out=out.merge(mi,on="launch_designator",how="left")
        out["has_metrics"]=out.get("status","").fillna("").eq("ok") | out.get("trace_csv_path",pd.Series(index=out.index,dtype=object)).notna()
    return out
