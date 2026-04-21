# Resume Tailoring App

A Streamlit app that parses a LaTeX resume **once** into editable Markdown, caches job summaries, and tailors resume content to job postings with **Claude** (with prompt caching). Mundane extraction and job summarization use **Google Gemini**.

This README is the **entry point for understanding the project** without reading code first. Each major folder has its own `README.md` with more detail.

## Documentation map

| Location | What you learn there |
|----------|----------------------|
| [GUI/README.md](GUI/README.md) | Streamlit UI: pages, session state, how `ResumeTailoringApp` is structured. |
| [models/README.md](models/README.md) | Pydantic models: resume shape, job cache shape, usage stats. |
| [services/README.md](services/README.md) | Business logic: caching, LaTeX parse, scraping, Claude tailoring. |
| [templates/README.md](templates/README.md) | Jinja2 LaTeX template and how output `.tex` is built. |
| [cache/README.md](cache/README.md) | On-disk layout: `resume.md`, job JSON, tailored markdown, outputs, usage log. |
| [latex/README.md](latex/README.md) | Static `.cls` / `template.tex` / images; makefile `TEXINPUTS` for manual PDF builds. |

## Architecture (one screen)

```text
┌─────────────┐     ┌──────────┐     ┌─────────────────────────────────────┐
│  app.py     │────▶│  GUI/    │────▶│  services/ (no Streamlit imports)  │
│  (thin)     │     │  main.py │     │  cache, latex, jobs, resume_writer │
└─────────────┘     └──────────┘     └─────────────────────────────────────┘
                           │                      │
                           │                      ▼
                           │              ┌───────────────┐
                           │              │  cache/       │
                           └─────────────▶│  resume.md,   │
                                          │  jobs/,       │
                                          │  tailored/,   │
                                          │  outputs/     │
                                          └───────────────┘
```

- **`app.py`** — Only imports and calls `run_app()` from `GUI`. Keeps `streamlit run app.py` as the documented entry command.
- **`config.py`** — Loads `.env`, exposes `Settings`, creates cache/output directories.
- **`GUI/main.py`** — `ResumeTailoringApp`: wires services, session state, and sidebar; each screen lives under **`GUI/pages/`** (`tailor`, `my_resume`, `cache_manager_page`, `ai_logs_page`, `settings_page`). Shared keys: **`GUI/session_keys.py`**; paths/presets: **`GUI/constants.py`**.
- **`models/`** — Shared typed data (`ResumeData`, `JobData`, caches).
- **`services/`** — Side effects and AI calls; atomic file operations live in `cache_manager.py`.
- **`templates/`** — Jinja2 for final `.tex` rendering.
- **`cache/`** — Default data directory (configurable via env).

## Setup

1. Install `uv` (Astral):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Setup local environment and dependencies (`make setup` runs `make env` to copy `.env.example` → `.env` when `.env` is missing, then `uv sync`):
   ```bash
   make setup
   ```
   You can copy the env file only with `make env`.
3. Configure environment variables (if not already created by `make env` / `make setup`):
   ```bash
   cp .env.example .env
   ```
   Fill in:
   - `ANTHROPIC_API_KEY`
   - `GEMINI_API_KEY`
   - optional `GEMINI_MODEL`, `CLAUDE_MODEL`, `CACHE_DIR`, `OUTPUT_DIR`

## Troubleshooting (Gemini 429 / quota)

If you see **HTTP 429** or messages like **quota exceeded** / **free_tier** / **limit: 0** for `gemini-2.0-flash`:

- **Confirm models for your key** — In the app, open **Settings** and click **Fetch available Gemini models**. That calls Google's **`list_models`** API with your `GEMINI_API_KEY` and shows which model **short ids** support `generateContent` (those are valid values for `GEMINI_MODEL`). This is more reliable than guessing from public docs alone.
- **Per-model quotas** — Free tier limits apply per model. Set `GEMINI_MODEL` to a **short id** from that table (e.g. `gemini-1.5-flash`), restart the app, and retry.
- **Billing** — Enabling billing on your Google Cloud / AI Studio project often raises limits; see [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) and [usage](https://ai.dev/rate-limit).
- **Wait** — The API may include a **retry in Ns** hint; the app retries a few times with backoff, but sustained quota exhaustion needs one of the steps above.

## Run

```bash
make run
```

Equivalent: `uv run streamlit run app.py` from the repo root.

## Logging

- **Console**: logs go to **stderr** (Streamlit terminal).
- **File**: by default **`cache/logs/app.log`** (rotating, 5 MB × 5 backups unless overridden).
- **GUI**: open **AI Logs** in the sidebar for a **live** (auto-refreshing) view of AI-related lines: Gemini/Claude requests and **truncated response previews** plus token metadata when available. Same lines also go to stderr and the log file.
- **Configure** (optional, in `.env`): `LOG_LEVEL` (default `INFO`), `LOG_DIR`, `LOG_FILE`, `LOG_FILE_MAX_BYTES`, `LOG_FILE_BACKUP_COUNT`.
- Logging is initialized at app startup in `run_app()` via [`logging_config.py`](logging_config.py). Third-party HTTP/Google client noise is capped at WARNING unless you raise verbosity.

## User workflow

- **First parse**: upload `.tex`; app creates `cache/resume.md`.
- **After that**: the app always uses `cache/resume.md` as source-of-truth and does **not** re-parse `.tex`.
- **Job URL**: checks `cache/jobs/<hash>.json` before scraping or calling Gemini; if `cache/tailored/<hash>.md` exists, it is loaded into the editor.
- **Tailoring**: **Tailor with Claude** writes tailored Markdown to `cache/tailored/<hash>.md` (previous versions may be archived under `cache/tailored/archive/`). You **edit** the draft, then **Generate LaTeX & PDF** to render Jinja → `.tex`, copy vendor files from `latex/`, and run **`pdflatex`** when available. Token usage is logged for the Cache Manager.

## UI pages (conceptual)

| Page | Purpose |
|------|---------|
| **Tailor Resume** | Job URL, fetch/summarize, **past postings** picker, **Claude tailor**, **edit** tailored Markdown, **Generate LaTeX & PDF**, diff, download **`.tex` / `.pdf`**. |
| **My Resume** | Edit `resume.md`, append new experience with preview. |
| **Cache Manager** | Job caches, delete entries, token usage aggregates. |
| **AI Logs** | Live (or manual) view of AI request/response log lines with previews. |
| **Settings** | API key status; **pick Gemini & Claude model ids for this session** (defaults from `.env`); list available Gemini models; paths. |

## Root files worth knowing

| File | Role |
|------|------|
| `app.py` | Streamlit entry: delegates to `GUI.run_app`. |
| `config.py` | Environment and directory bootstrap. |
| `logging_config.py` | Console + rotating file logging for the app. |
| `pyproject.toml` | UV/Python dependencies, `[dependency-groups] dev` (Black/isort), `[tool.black]` / `[tool.isort]`. |
| `makefile` | `make env`, `make setup`, `make run`, `make format` / `make format-check` (isort + black), plus LaTeX PDF targets (`build`, `clean`, `watch`). |
| `.env.example` | Template for required env vars. |

## Guardrails

- Claude is instructed **not** to invent employers, titles, or experience not present in `resume.md`.
- File writes use **atomic** temp + rename via `CacheManager`.
- Job and resume caches avoid redundant API calls when JSON already exists.

## For AI assistants (e.g. Cursor)

When changing behavior:

1. **UI-only** → `GUI/main.py` (app + routing), `GUI/pages/` (per-screen UI), `GUI/session_keys.py`, `GUI/constants.py`, `GUI/app_context.py`.
2. **Caching / files** → `services/cache_manager.py`.
3. **Gemini** → `latex_parser.py`, `job_scraper.py`, `gemini_configure.py`, `gemini_text.py`, `gemini_retry.py`, `gemini_models.py`.
4. **Prompts** → `services/prompts.py` (Claude + Gemini instruction text).
5. **Claude / LaTeX output** → `resume_writer.py` + `templates/resume_v2_{preamble,body}.*` (structured Markdown → LaTeX); fallback `templates/resume.tex.jinja`; `latex_assets.py` + `latex_build.py` (`pdflatex`); vendor assets under `latex/` (makefile `TEXINPUTS`).
6. **Schema** → `models/`.
7. **Logging setup** → `logging_config.py` (handlers); AI ring buffer → `services/ai_log_buffer.py`; structured AI summaries → `services/ai_api_log.py`.

This keeps edits localized and reviewable.
