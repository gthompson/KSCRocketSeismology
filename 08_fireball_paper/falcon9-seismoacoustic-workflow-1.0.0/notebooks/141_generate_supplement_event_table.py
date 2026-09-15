#!/usr/bin/env python3
"""Generate the full supplementary event table from Notebook 100's CSV.

Run this script from the repository's ``latex`` directory after Notebook 100.
It deliberately performs CSV parsing outside LaTeX because loading the complete
wide CSV with ``datatool`` can exhaust pdfTeX's main-memory allocation.
"""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import math
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = (
    SCRIPT_DIR.parent
    if (SCRIPT_DIR.parent / "data").is_dir()
    else SCRIPT_DIR
)
SOURCE_CSV = (
    REPOSITORY_ROOT
    / "data"
    / "outputs"
    / "100_measure_event_amplitudes_and_acoustic_seismic_coupling"
    / "event_acoustic_seismic_amplitudes.csv"
)
OUTPUT_FILE = REPOSITORY_ROOT / "latex" / "generated" / "supplement_event_measurements.tex"

REQUIRED_COLUMNS = (
    "event_number",
    "elapsed_time_s",
    "channel_count",
    "corrected_pick_span_s",
    "solution_quality_class",
    "best_back_azimuth_deg",
    "best_apparent_speed_mps",
    "maximum_coherence_score",
    "acoustic_stack_peak_to_peak_pa",
    "pgv_vector_mps",
    "acoustic_stack_p2p_snr",
    "pgv_vector_snr",
    "pgv_window_capture_fraction",
    "passes_regression_quality",
)


def finite_number(value: str) -> float | None:
    """Return a finite float or None for blank/NaN/non-numeric values."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def fixed(value: str, places: int) -> str:
    """Format a finite number to fixed precision for a LaTeX table."""
    number = finite_number(value)
    return "--" if number is None else f"{number:.{places}f}"


def integer(value: str) -> str:
    """Format an integer-valued CSV field."""
    number = finite_number(value)
    return "--" if number is None else str(int(round(number)))


def scientific_tex(value: str, significant_digits: int = 3) -> str:
    """Format a finite value as compact LaTeX scientific notation."""
    number = finite_number(value)
    if number is None:
        return "--"
    if number == 0.0:
        return "0"
    exponent = int(math.floor(math.log10(abs(number))))
    mantissa = number / (10.0 ** exponent)
    decimals = max(0, significant_digits - 1)
    return rf"${mantissa:.{decimals}f}\times10^{{{exponent}}}$"


def quality_code(value: str) -> str:
    """Map the verbose planar-solution class to the printed code."""
    return {
        "A_high_quality": "A",
        "B_probable": "B",
        "C_weak_or_broad": "C",
    }.get(value.strip(), value.strip() or "--")


def yes_no(value: str) -> str:
    """Normalize common Boolean encodings."""
    return "yes" if value.strip().lower() in {"true", "1", "yes", "y"} else "no"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_CSV)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()
    source_csv, output_file = args.source.expanduser().resolve(), args.output.expanduser().resolve()
    if not source_csv.is_file():
        raise FileNotFoundError(
            "Notebook 100 event table not found:\n"
            f"  {source_csv}\n"
            "Run Notebook 100 before generating the supplementary table."
        )

    with source_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or ())]
        if missing:
            raise KeyError(
                "Notebook 100 event table is missing required columns: "
                + ", ".join(missing)
            )
        rows = list(reader)

    if len(rows) != 153:
        raise ValueError(
            f"Expected 153 accepted events, but {source_csv} contains {len(rows)} rows."
        )

    numbers = [finite_number(row["event_number"]) for row in rows]
    if sorted(numbers, key=lambda v: -1 if v is None else v) != list(range(1, 154)):
        raise ValueError("Expected unique integral catalogue IDs 1–153")
    rows.sort(key=lambda row: int(float(row["event_number"])))
    allowed_bool = {"true", "false", "1", "0", "yes", "no", "y", "n"}
    if any(row["passes_regression_quality"].strip().lower() not in allowed_bool for row in rows):
        raise ValueError("Missing or invalid regression-quality Boolean")
    if any(row["solution_quality_class"].strip() not in {"A_high_quality", "B_probable", "C_weak_or_broad"} for row in rows):
        raise ValueError("Unknown planar quality class")
    regression_count = sum(yes_no(row["passes_regression_quality"]) == "yes" for row in rows)
    lines = [
        r"\begin{landscape}",
        r"\tiny",
        r"\setlength{\tabcolsep}{2pt}",
        r"\begin{longtable}{rrrrlrrrrrrrrc}",
        r"\caption{Chronology, association, propagation, and amplitude measurements for",
        r"all 153 accepted pressure transients. Time is elapsed from the first",
        r"DD2-referenced catalogue arrival, and span is the corrected difference between",
        r"the first and last associated pressure picks. Classes A, B, and C denote",
        r"high-quality, intermediate, and weak or broad planar solutions. Pressure is",
        r"the peak-to-peak amplitude of the aligned median waveform; BAZ is from grid north.",
        r"PGV is maximum three-component vector",
        r"ground velocity; capture is the event-window PGV divided by the maximum PGV",
        rf"in the saved short segment. The final column identifies the {regression_count} rows admitted to",
        r"the pressure--PGV regression.}\label{tab:supp_event_measurements}\\",
        r"\toprule",
        r"Event & $t$ (s) & $N$ & Span (s) & Q & BAZ ($^\circ$) &",
        r"$c_{\rm app}$ & Coh. & $p_{\rm p2p}$ & PGV & $S_p$ & $S_v$ & Cap. & Reg. \\",
        r" & & & & & & (m s$^{-1}$) & & (Pa) & (m s$^{-1}$) & & & & \\",
        r"\midrule",
        r"\endfirsthead",
        r"\multicolumn{14}{c}{Table~\thetable\ continued}\\",
        r"\toprule",
        r"Event & $t$ (s) & $N$ & Span (s) & Q & BAZ ($^\circ$) &",
        r"$c_{\rm app}$ & Coh. & $p_{\rm p2p}$ & PGV & $S_p$ & $S_v$ & Cap. & Reg. \\",
        r" & & & & & & (m s$^{-1}$) & & (Pa) & (m s$^{-1}$) & & & & \\",
        r"\midrule",
        r"\endhead",
        r"\midrule",
        r"\multicolumn{14}{r}{Continued on next page}\\",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]

    for row in rows:
        values = (
            integer(row["event_number"]),
            fixed(row["elapsed_time_s"], 2),
            integer(row["channel_count"]),
            fixed(row["corrected_pick_span_s"], 4),
            quality_code(row["solution_quality_class"]),
            fixed(row["best_back_azimuth_deg"], 1),
            fixed(row["best_apparent_speed_mps"], 1),
            fixed(row["maximum_coherence_score"], 3),
            fixed(row["acoustic_stack_peak_to_peak_pa"], 2),
            scientific_tex(row["pgv_vector_mps"]),
            fixed(row["acoustic_stack_p2p_snr"], 1),
            fixed(row["pgv_vector_snr"], 1),
            fixed(row["pgv_window_capture_fraction"], 2),
            yes_no(row["passes_regression_quality"]),
        )
        lines.append(" & ".join(values) + r" \\")

    lines.extend((r"\end{longtable}", r"\end{landscape}", ""))
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")
    metadata = {"producer": "141_generate_supplement_event_table.py", "source_csv": str(source_csv),
        "source_sha256": hashlib.sha256(source_csv.read_bytes()).hexdigest(),
        "output_tex": str(output_file), "catalogue_rows": len(rows), "regression_rows": regression_count,
        "azimuth_convention": "projected grid north", "pressure_statistic": "extrema of aligned median waveform"}
    output_file.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {output_file}")


if __name__ == "__main__":
    main()
