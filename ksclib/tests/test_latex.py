import math

import pandas as pd

from ksclib.latex import latex_table, num, sig, signed, write_table


def test_number_formats():
    assert num(-2.64, 1) == "$-$2.6"
    assert num(float("nan")) == "--"
    assert signed(1.27, 1) == "+1.3" and signed(-0.351, 2) == "$-$0.35"
    assert sig(8.24) == "8.2" and sig(11.45) == "11" and sig(0.0716) == "0.072" and sig(math.nan) == "--"


def test_table(tmp_path):
    df = pd.DataFrame({"A": ["x", "y"], "B": ["1.0", float("nan")]})
    tex = latex_table(df, "Cap.", label="tab:t", colfmt="lr", footnote="$^a$ note")
    assert r"\begin{tabular}{lr}" in tex and r"y & -- \\" in tex
    assert r"\multicolumn{2}{l}{$^a$ note}" in tex and r"\label{tab:t}" in tex
    tex = latex_table(df, "Cap.", insert={1: [r"\midrule", r"A & B \\"]})
    assert r"x & 1.0 \\" + "\n  \\midrule\n  A & B" in tex
    p = write_table(tmp_path / "tables" / "t.tex", df, "Cap.")
    assert p.read_text().startswith("% Written by a notebook")
