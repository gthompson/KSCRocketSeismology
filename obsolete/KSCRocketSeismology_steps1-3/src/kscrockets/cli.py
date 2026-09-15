from __future__ import annotations
import argparse
from .config import load_settings
from .catalog import build_catalog, read_catalog, validate_catalog
from .database import build_database
from .website import build_website
from .analysis import build_ensemble_products


def _build_catalog(s):
    return build_catalog(s.raw_catalog, s.canonical_catalog, s.year_min, s.year_max,
                         overrides_path=s.event_overrides, id_registry_path=s.event_id_registry)


def main(argv=None):
    p=argparse.ArgumentParser(prog="ksc-rockets")
    p.add_argument("--config",default=None)
    sp=p.add_subparsers(dest="command",required=True)
    for cmd in ("build-catalog","build-db","build-website","analyze","build-all","validate"):
        sp.add_parser(cmd)
    a=p.parse_args(argv); s=load_settings(a.config)
    if a.command in {"build-catalog","build-all"}:
        df=_build_catalog(s); print(f"catalog: {s.canonical_catalog} ({len(df)} events)")
    if a.command in {"build-db","build-all"}:
        if not s.canonical_catalog.exists(): _build_catalog(s)
        pth=build_database(s.canonical_catalog,s.database); print(f"database: {pth}")
    if a.command in {"build-website","build-all"}:
        if not s.canonical_catalog.exists(): _build_catalog(s)
        pth=build_website(s.canonical_catalog,s.website_output,s.metrics_index,s.website_title,s.website_subtitle); print(f"website: {pth}")
    if a.command in {"analyze","build-all"}:
        if not s.canonical_catalog.exists(): _build_catalog(s)
        products=build_ensemble_products(s.canonical_catalog,s.analysis_output,s.year_min,s.year_max); print(f"analysis: {len(products)} products in {s.analysis_output}")
    if a.command=="validate":
        errs=validate_catalog(read_catalog(s.canonical_catalog)); print("OK" if not errs else "\n".join(errs)); raise SystemExit(1 if errs else 0)

if __name__=="__main__": main()
