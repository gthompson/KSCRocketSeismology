Converted the full Methods draft to standalone LaTeX:

[Download falcon9_methods_draft.tex](/Users/thompsong/Documents/Codex/2026-07-15/referenced-chatgpt-conversation-this-is-untrusted/falcon9_methods_draft.tex)

It includes:

- all 14 Methods subsections;
- 16 rendered equation environments;
- SI-unit formatting through `siunitx`;
- the confirmation and citation checklists on separate pages.

Structural checks passed. A TeX compiler was not available here, so I could not produce a PDF. You can compile it in Overleaf or locally with:

```bash
latexmk -pdf falcon9_methods_draft.tex
```

or:

```bash
pdflatex falcon9_methods_draft.tex
```

The confirmation checklist is intentionally included after the Methods. Remove those final two unnumbered sections before submission.