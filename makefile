# =============================================================================
# Resume builder — Makefile
#
#   • App — Python / Streamlit (uv): local env and run the web UI
#   • LaTeX — PDF toolchain: install TeX, compile, clean, watch
#
# Usage: make setup | make run | make build | …
# =============================================================================

.DEFAULT_GOAL := help

.PHONY: help setup env run install build clean all watch format format-check lint pre-commit-install

# =============================================================================
# App — Python / Streamlit (uv)
# =============================================================================

UV ?= uv

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env && echo "Created .env from .env.example"; \
	else \
		echo ".env already exists — left unchanged (delete it to copy from .env.example again)"; \
	fi

setup: env
	@echo "Setting up Python environment with uv..."
	command -v $(UV) >/dev/null 2>&1 || (echo "uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/" && exit 1)
	$(UV) sync
	@echo "Setup complete. Fill API keys in .env if needed."

run:
	$(UV) run streamlit run app.py

format:
	@echo "Running isort + black…"
	$(UV) run isort .
	$(UV) run black .

format-check:
	@echo "Checking isort + black (no writes)…"
	$(UV) run isort --check-only --diff .
	$(UV) run black --check .

lint:
	@echo "Running pre-commit (black, isort, pylint, mypy)…"
	@echo "(Hooks only inspect git-tracked files; \`git add\` new Python sources first.)"
	$(UV) run pre-commit run --all-files

pre-commit-install:
	@echo "Installing pre-commit git hooks…"
	$(UV) run pre-commit install

# =============================================================================
# LaTeX — PDF build (pdflatex / latexmk)
#
# TEX_FILE may be a bare name (main.tex) or a path (resumes/foo.tex). Build runs
# from that file’s directory so the PDF and aux files land next to the .tex.
#
# Pass the .tex path without TEX_FILE= (recommended):
#   make build latex/foo.tex
#   make clean latex/foo.tex
#   make watch latex/foo.tex
# Or: make build FILE=latex/foo.tex   (when you only pass the "build" goal)
# Legacy: make build TEX_FILE=latex/foo.tex
# =============================================================================

TEX_FILE ?= main.tex

# Resolve TEX_FILE: positional *.tex goal wins, else FILE=, else default.
CMD_TEX := $(firstword $(filter %.tex,$(MAKECMDGOALS)))
ifneq ($(CMD_TEX),)
  override TEX_FILE := $(CMD_TEX)
else ifneq ($(strip $(FILE)),)
  override TEX_FILE := $(FILE)
endif

PDF_FILE = $(TEX_FILE:.tex=.pdf)
TEX_DIR = $(dir $(TEX_FILE))
TEX_BASE = $(notdir $(TEX_FILE))

PDFLATEX ?= pdflatex
LATEXMK ?= latexmk
# macOS: Homebrew/MacTeX often install here; prepend so `make build` works without editing shell rc
TEXBIN ?= /Library/TeX/texbin
# Local .cls / reference sources (twentysecondcv.cls, template.tex, …). Trailing : keeps default TeX trees.
LATEX_DIR ?= latex
TEXINPUTS_LOCAL := $(abspath $(LATEX_DIR)):

# Extra goals like `make build resumes/a.tex` would otherwise look for a rule named resumes/a.tex
ifneq ($(filter %.tex,$(MAKECMDGOALS)),)
.PHONY: $(filter %.tex,$(MAKECMDGOALS))
$(filter %.tex,$(MAKECMDGOALS)):
	@:
endif

install:
	@echo "Installing LaTeX tools via Homebrew..."
	brew --version >/dev/null 2>&1 || /bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
	brew install --cask mactex-no-gui
	@echo "LaTeX installed. You may need to restart your terminal."

build:
	@echo "Compiling $(TEX_FILE) → $(PDF_FILE)..."
	cd $(TEX_DIR) && \
	  if [ -x "$(TEXBIN)/pdflatex" ]; then export PATH="$(TEXBIN):$$PATH"; fi && \
	  export TEXINPUTS="$(TEXINPUTS_LOCAL)$$TEXINPUTS" && \
	  $(PDFLATEX) -interaction=nonstopmode $(TEX_BASE)
	cd $(TEX_DIR) && \
	  if [ -x "$(TEXBIN)/pdflatex" ]; then export PATH="$(TEXBIN):$$PATH"; fi && \
	  export TEXINPUTS="$(TEXINPUTS_LOCAL)$$TEXINPUTS" && \
	  $(PDFLATEX) -interaction=nonstopmode $(TEX_BASE)

clean:
	@echo "Cleaning LaTeX auxiliary files next to $(TEX_FILE)..."
	rm -f $(TEX_FILE:.tex=.aux) $(TEX_FILE:.tex=.log) $(TEX_FILE:.tex=.out) \
		$(TEX_FILE:.tex=.toc) $(TEX_FILE:.tex=.fls) $(TEX_FILE:.tex=.fdb_latexmk) \
		$(TEX_FILE:.tex=.synctex.gz)

all: clean build

watch:
	@echo "Watching $(TEX_FILE) for changes..."
	if [ -x "$(TEXBIN)/latexmk" ] || [ -x "$(TEXBIN)/pdflatex" ]; then export PATH="$(TEXBIN):$$PATH"; fi && \
	  export TEXINPUTS="$(TEXINPUTS_LOCAL)$$TEXINPUTS" && \
	  $(LATEXMK) -pdf -pvc -cd $(TEX_FILE)

# =============================================================================
# Help
# =============================================================================

help:
	@echo "App (uv / Streamlit)"
	@echo "  make env     Copy .env.example → .env if .env is missing"
	@echo "  make setup   make env, then uv sync (full local app setup)"
	@echo "  make run     streamlit run app.py"
	@echo "  make format       isort + black (writes files; needs: uv sync --group dev)"
	@echo "  make format-check isort + black --check (CI-friendly)"
	@echo "  make lint         pre-commit run --all-files (black, isort, pylint, mypy)"
	@echo "  make pre-commit-install  git hook → pre-commit on commit"
	@echo ""
	@echo "LaTeX"
	@echo "  make install  Install MacTeX via Homebrew (mactex-no-gui)"
	@echo "  make build path/to/file.tex       pdflatex twice (no TEX_FILE=; path is a second goal)"
	@echo "  make build FILE=path/to/file.tex  same, if you prefer a variable"
	@echo "  make clean [path] / watch [path] / all [path]  — same pattern"
	@echo "  Legacy: make build TEX_FILE=path/to/file.tex"
	@echo ""
	@echo "Variables: UV=$(UV)  TEX_FILE=$(TEX_FILE)  FILE=  PDFLATEX=$(PDFLATEX)  TEXBIN=$(TEXBIN)"
	@echo "           LATEX_DIR=$(LATEX_DIR)  (prepended to TEXINPUTS for build/watch)"
