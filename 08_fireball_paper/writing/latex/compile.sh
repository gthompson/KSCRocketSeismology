#!/bin/bash
set -e

TEXFILE="${1:?Usage: $0 <file.tex>}"
BASENAME="${TEXFILE%.tex}"

pdflatex "$TEXFILE"
bibtex "$BASENAME"
pdflatex "$TEXFILE"
pdflatex "$TEXFILE"

echo "Created ${BASENAME}.pdf"

# or use latexmk -pdf $TEXFILE
