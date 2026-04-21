# LaTeX assets (`latex/`)

Static TeX inputs only (no Jinja). Used by **`pdflatex`** via **`TEXINPUTS`** in the root [`makefile`](../makefile).

- **`twentysecondcv.cls`** — CV document class used by `template.tex`.
- **`template.tex`** — reference layout using `twentysecondcv.cls`; profile images (`izzy.JPG`, etc.) sit here for that build.

The Streamlit app renders tailored output with [`templates/resume_v2_*`](../templates/README.md) (preamble is self-contained; no `twentysecondcv` required for that path). After **Generate LaTeX & PDF**, allowlisted files here are **copied into `OUTPUT_DIR`** (see [`services/latex_assets.py`](../services/latex_assets.py)), and [`services/latex_build.py`](../services/latex_build.py) may run `pdflatex` there. You can also compile manually with the makefile; it prepends this directory to `TEXINPUTS`.
