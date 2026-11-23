"""Write pandas tables as LaTeX table environments for the papers to \\input.

Each paper keeps its tables in a ``tables/`` folder written by a notebook, so a
rerun of the analysis refreshes the tables as well as the figures::

    from ksclib.latex import write_table, num, signed
    df = pd.DataFrame({"Station": ..., "Distance (km)": d.map(lambda x: num(x, 2))})
    write_table(PAPER_DIR / "tables" / "stations.tex", df, caption="...", label="tab:stations",
                colfmt="lr")

and in the paper ``\\input{tables/stations}``. Cells are written as given (no
escaping), so format numbers as strings first and use LaTeX markup freely.
Requires booktabs.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

MISSING = "--"


def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def num(x, decimals: int = 1) -> str:
    """Fixed decimals; negative numbers use a typeset minus; missing -> '--'."""
    if _missing(x):
        return MISSING
    s = f"{x:.{decimals}f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def signed(x, decimals: int = 1) -> str:
    """Like num() but positive values carry '+'."""
    if _missing(x):
        return MISSING
    return num(x, decimals) if x < 0 else "+" + f"{x:.{decimals}f}"


def sig(x, figures: int = 2) -> str:
    """Round to significant figures without exponent notation (8.24 -> 8.2, 11.45 -> 11)."""
    if _missing(x):
        return MISSING
    if x == 0:
        return "0"
    decimals = max(figures - 1 - int(math.floor(math.log10(abs(x)))), 0)
    return num(round(x, decimals), decimals)


def latex_table(df: pd.DataFrame, caption: str, label: str | None = None, colfmt: str | None = None,
                size: str = "small", placement: str = "htbp", footnote: str | None = None,
                note: str | None = None, insert: dict[int, list[str]] | None = None) -> str:
    """LaTeX table environment (booktabs) for ``df``.

    ``footnote`` is set as a full-width row under the bottom rule; ``note`` as a
    paragraph below the tabular. ``insert`` maps a row position to raw LaTeX lines
    placed before that row (e.g. a second header block: ``{12: [r"\\midrule", ...]}``).
    """
    insert = insert or {}
    colfmt = colfmt or "l" * df.shape[1]
    lines = [r"\begin{tabular}{" + colfmt + "}", r"\toprule",
             " & ".join(str(c) for c in df.columns) + r" \\", r"\midrule"]
    for i, row in enumerate(df.itertuples(index=False)):
        lines += insert.get(i, [])
        lines.append(" & ".join(MISSING if _missing(v) else str(v) for v in row) + r" \\")
    lines.append(r"\bottomrule")
    if footnote:
        lines.append(rf"\multicolumn{{{df.shape[1]}}}{{l}}{{{footnote}}}")
    lines.append(r"\end{tabular}")
    out = [rf"\begin{{table}}[{placement}]", r"  \centering", rf"  \caption{{{caption}}}"]
    if label:
        out.append(rf"  \label{{{label}}}")
    out.append(rf"  \{size}")
    out += ["  " + l for l in lines]
    if note:
        out.append(rf"  \par\smallskip\parbox{{0.95\textwidth}}{{\footnotesize {note}}}")
    out.append(r"\end{table}")
    return "\n".join(out) + "\n"


def write_table(path, df: pd.DataFrame, caption: str, **kwargs) -> Path:
    """Write ``latex_table(df, caption, **kwargs)`` to ``path`` (folders created)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("% Written by a notebook; edit the notebook, not this file.\n"
                    + latex_table(df, caption, **kwargs))
    return path
