#!/usr/bin/env bash
set -euo pipefail

EEV_PY="$HOME/Developer/flovopy/flovopy/analysis/eev.py"
ROOT="/data/KSC/all_florida_launches/network_detected"
STXML="$HOME/Dropbox/DATA/station_metadata/KSC2.xml"
PATTERN="**/*LAUNCH*"
ENV_NAME="skience24_pyrocko"

# Ensure conda is available in non-interactive shells
if ! command -v conda >/dev/null 2>&1; then
  # fallback to typical install locations
  if [ -n "${CONDA_EXE:-}" ]; then
    # shellcheck disable=SC1090
    source "$(dirname "$CONDA_EXE")/../etc/profile.d/conda.sh"
  elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1090
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
  elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1090
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
  else
    echo "❌ Could not find conda.sh; run 'conda init bash' first." >&2
    exit 1
  fi
fi

# Activate env only if needed
current_env="${CONDA_PREFIX:-}"
if [ -z "$current_env" ] || [ "$(basename "$current_env")" != "$ENV_NAME" ]; then
  echo "🔄 Activating conda environment: $ENV_NAME"
  conda activate "$ENV_NAME"
else
  echo "✅ Already in conda environment: $(basename "$current_env")"
fi

# Sanity checks
if [ ! -f "$EEV_PY" ]; then
  echo "❌ eev script not found: $EEV_PY" >&2
  exit 1
fi
if [ ! -d "$ROOT" ]; then
  echo "❌ Root dir not found: $ROOT" >&2
  exit 1
fi
if [ ! -f "$STXML" ]; then
  echo "⚠ StationXML not found at $STXML (continuing without it)"
  STXML=""
fi

echo "🐍 Using python: $(command -v python)"
python --version
echo "📄 Script: $EEV_PY"
echo "📂 Root:   $ROOT"
echo "🔎 Pattern: $PATTERN"
[ -n "$STXML" ] && echo "🗺 StationXML: $STXML"

# Run (use -u for unbuffered output so you see prints immediately)
if [ -n "$STXML" ]; then
  exec python -u "$EEV_PY" \
    --root "$ROOT" \
    --pattern "$PATTERN" \
    --stationxml "$STXML" \
    --resume
else
  exec python -u "$EEV_PY" \
    --root "$ROOT" \
    --pattern "$PATTERN" \
    --resume
fi