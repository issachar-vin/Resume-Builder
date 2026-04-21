# Templates (`templates/`)

Jinja2 templates used by the Python app.

## Files

| File | Purpose |
|------|---------|
| `resume.tex.jinja` | **Fallback**: verbatim Markdown wrapper if structured parse fails. |
| `resume_v2_preamble.tex` | Static LaTeX preamble + `\\begin{document}` (article class + resume macros). Loaded as **plain text**, not parsed by Jinja (avoids `{#1` macro clashes). |
| `resume_v2_body.jinja` | Structured body: name, contact, summary, **Technical Skills**, **Experience**, **Education** (that order in the PDF). `## Gap Flags` is stripped before LaTeX (meta only). |

[`services/resume_writer.py`](../services/resume_writer.py) parses tailored Markdown with [`services/markdown_resume.py`](../services/markdown_resume.py) (same shape as `cache/resume.md`). LLM instructions live in [`services/prompts.py`](../services/prompts.py).

## LaTeX class / reference CVs

See **[`latex/`](../latex/)** and makefile **`TEXINPUTS`**.

## Customization

- Tweak layout in `resume_v2_body.jinja` / `resume_v2_preamble.tex`.
- Adjust Markdown parsing rules in `markdown_resume.py`.
- New Jinja variables → update `ResumeWriterService.render_latex()`.
