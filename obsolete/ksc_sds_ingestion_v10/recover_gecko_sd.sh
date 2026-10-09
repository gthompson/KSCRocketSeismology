#!/bin/bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults
SOURCE="/Volumes/NO NAME"
DEST=""
STATION="B23"
PYTHON_SCRIPT="${SCRIPT_DIR}/recover_gecko_sd.py"

DRY_RUN=0
VERIFY=0
OVERWRITE_MISMATCHED=0
QUIET_EXISTING=0


usage() {
    cat <<EOF
Usage:
  $SCRIPT_NAME -d DESTINATION [options]

Safely recover Gecko / Silicon Graphics digitizer data from an SD card
using recover_gecko_sd.py.

The wrapper defaults to station B23, which is currently the only
Silicon Graphics / Gecko station in this workflow.

Expected SD-card structure:

  data/
    YYYY/
      MM/
        DD/
          HH/
            YYYY-MM-DD hhmm ss B23.ms
            YYYY-MM-DD hhmm ss B23.ss

  histogram/
    YYYY-MM-DD.csv

The recovered files are written beneath the destination while preserving
the original data directory hierarchy:

  DESTINATION/
    YYYY/MM/DD/HH/*.ms
    YYYY/MM/DD/HH/*.ss
    histogram/YYYY-MM-DD.csv
    gecko_recovery.log

Required:
  -d, --destination DEST
        Destination directory.

        Normally this should be the Silicon Graphics download directory,
        for example:

          00_downloads/SiliconGraphics

Options:
  -s, --source SOURCE
        SD-card root or the card's data/ directory.

        Default:
          /Volumes/NO NAME

  -n, --station STATION
        Station code to recover.

        Default:
          B23

        This option is retained as an override in case the workflow
        changes in the future.

  -p, --python-script SCRIPT
        Path to recover_gecko_sd.py.

        Default:
          $PYTHON_SCRIPT

  --dry-run
        Show what would be copied without writing destination files.

  --verify
        SHA256-verify copied files and same-sized existing files.

        This is slower and causes additional reads from the SD card.
        For a card suspected of filesystem corruption, a normal recovery
        pass without --verify is usually preferable first.

  --overwrite-mismatched
        Replace an existing destination file when its size differs from
        the source file.

        Without this option, mismatches are logged and the existing
        destination file is left untouched.

  --quiet-existing
        Do not print a line for every destination file that already
        exists with the same size.

  -h, --help
        Show this help message and exit.

Examples:

  Recover B23 using the default SD-card mount:

    $SCRIPT_NAME \\
      -d "/path/to/00_downloads/SiliconGraphics"

  Dry run first:

    $SCRIPT_NAME \\
      -d "/path/to/00_downloads/SiliconGraphics" \\
      --dry-run

  Recover from a differently named SD card:

    $SCRIPT_NAME \\
      -s "/Volumes/GECKO_SD" \\
      -d "/path/to/00_downloads/SiliconGraphics"

  Use the data/ directory directly:

    $SCRIPT_NAME \\
      -s "/Volumes/NO NAME/data" \\
      -d "/path/to/00_downloads/SiliconGraphics"

  Verify with SHA256 checksums:

    $SCRIPT_NAME \\
      -d "/path/to/00_downloads/SiliconGraphics" \\
      --verify

  Override the default station:

    $SCRIPT_NAME \\
      -d "/path/to/00_downloads/SiliconGraphics" \\
      -n B99

EOF
}


error() {
    echo "ERROR: $*" >&2
}


require_arg() {
    local option="$1"
    local value="${2-}"

    if [[ -z "$value" ]]; then
        error "$option requires an argument."
        echo >&2
        usage >&2
        exit 2
    fi
}


# ----------------------------------------------------------------------
# Parse command-line arguments
# ----------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in

        -s|--source)
            require_arg "$1" "${2-}"
            SOURCE="$2"
            shift 2
            ;;

        -d|--destination)
            require_arg "$1" "${2-}"
            DEST="$2"
            shift 2
            ;;

        -n|--station)
            require_arg "$1" "${2-}"
            STATION="$2"
            shift 2
            ;;

        -p|--python-script)
            require_arg "$1" "${2-}"
            PYTHON_SCRIPT="$2"
            shift 2
            ;;

        --dry-run)
            DRY_RUN=1
            shift
            ;;

        --verify)
            VERIFY=1
            shift
            ;;

        --overwrite-mismatched)
            OVERWRITE_MISMATCHED=1
            shift
            ;;

        --quiet-existing)
            QUIET_EXISTING=1
            shift
            ;;

        -h|--help)
            usage
            exit 0
            ;;

        --)
            shift
            break
            ;;

        -*)
            error "Unknown option: $1"
            echo >&2
            usage >&2
            exit 2
            ;;

        *)
            error "Unexpected positional argument: $1"
            echo >&2
            usage >&2
            exit 2
            ;;
    esac
done


# ----------------------------------------------------------------------
# Validate arguments and environment
# ----------------------------------------------------------------------

if [[ -z "$DEST" ]]; then
    error "Destination is required."
    echo >&2
    usage >&2
    exit 2
fi

if [[ ! -e "$SOURCE" ]]; then
    error "Source does not exist:"
    echo "  $SOURCE" >&2
    exit 2
fi

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    error "Python recovery script not found:"
    echo "  $PYTHON_SCRIPT" >&2
    echo >&2
    echo "Keep recover_gecko_sd.py beside this wrapper, or specify it with:" >&2
    echo "  -p /path/to/recover_gecko_sd.py" >&2
    exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
    error "python3 was not found in PATH."
    exit 2
fi


# ----------------------------------------------------------------------
# Build command safely as an array
# ----------------------------------------------------------------------

CMD=(
    python3
    "$PYTHON_SCRIPT"
    "$SOURCE"
    "$DEST"
    --station
    "$STATION"
)

if [[ "$DRY_RUN" -eq 1 ]]; then
    CMD+=(--dry-run)
fi

if [[ "$VERIFY" -eq 1 ]]; then
    CMD+=(--verify)
fi

if [[ "$OVERWRITE_MISMATCHED" -eq 1 ]]; then
    CMD+=(--overwrite-mismatched)
fi

if [[ "$QUIET_EXISTING" -eq 1 ]]; then
    CMD+=(--quiet-existing)
fi


# ----------------------------------------------------------------------
# Show what is about to run
# ----------------------------------------------------------------------

echo "Gecko / Silicon Graphics SD recovery"
echo "------------------------------------"
echo "Source:                 $SOURCE"
echo "Destination:            $DEST"
echo "Station:                $STATION"
echo "Python recovery script: $PYTHON_SCRIPT"
echo "Dry run:                $([[ "$DRY_RUN" -eq 1 ]] && echo yes || echo no)"
echo "SHA256 verification:    $([[ "$VERIFY" -eq 1 ]] && echo yes || echo no)"
echo "Overwrite mismatches:   $([[ "$OVERWRITE_MISMATCHED" -eq 1 ]] && echo yes || echo no)"
echo "Quiet existing files:   $([[ "$QUIET_EXISTING" -eq 1 ]] && echo yes || echo no)"
echo


# ----------------------------------------------------------------------
# Run recovery
# ----------------------------------------------------------------------

"${CMD[@]}"
