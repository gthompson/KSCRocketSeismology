from __future__ import annotations
import argparse
from .config import load_settings
from .catalog import build_catalog, read_catalog, validate_catalog
from .website import build_website
from .analysis import build_ensemble_products


def main(argv=None):
    p=argparse.ArgumentParser(prog="ksc-rockets")
    p.add_argument("--config",default=None)
    sp=p.add_subparsers(dest="command",required=True)
    sp.add_parser("build-catalog")
    sp.add_parser("build-website")
    sp.add_parser("analyze")
    sp.add_parser("build-all")
    sp.add_parser("validate")
    a=p.parse_args(argv); s=load_settings(a.config)
    if a.command in {"build-catalog","build-all"}:
        df=build_catalog(s.raw_catalog,s.canonical_catalog,s.year_min,s.year_max); print(f"catalog: {s.canonical_catalog} ({len(df)} launches)")
    if a.command in {"build-website","build-all"}:
        if not s.canonical_catalog.exists(): build_catalog(s.raw_catalog,s.canonical_catalog,s.year_min,s.year_max)
        pth=build_website(s.canonical_catalog,s.website_output,s.metrics_index,s.website_title,s.website_subtitle); print(f"website: {pth}")
    if a.command in {"analyze","build-all"}:
        if not s.canonical_catalog.exists(): build_catalog(s.raw_catalog,s.canonical_catalog,s.year_min,s.year_max)
        products=build_ensemble_products(s.canonical_catalog,s.analysis_output,s.year_min,s.year_max); print(f"analysis: {len(products)} products in {s.analysis_output}")
    if a.command=="validate":
        errs=validate_catalog(read_catalog(s.canonical_catalog)); print("OK" if not errs else "\n".join(errs)); raise SystemExit(1 if errs else 0)

if __name__=="__main__": main()
