#!/usr/bin/env bash
set -euo pipefail

LATEX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$LATEX_DIR"

TEXFILE="${1:?Usage: $0 <file.tex>}"

latexmk \
  -pdf \
  -interaction=nonstopmode \
  -halt-on-error \
  "$TEXFILE"

echo "Created ${TEXFILE%.tex}.pdf"