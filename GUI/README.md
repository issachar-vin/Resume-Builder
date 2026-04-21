# GUI (`GUI/`)

This folder holds **all Streamlit user interface code**. The rest of the project (models, services, config) stays free of UI concerns so you can reason about business logic and AI calls separately.

## What lives here

| File / folder | Role |
|----------------|------|
| `__init__.py` | Exports `run_app` and `ResumeTailoringApp` for a clean import from the root `app.py`. |
| `main.py` | `ResumeTailoringApp`: loads config, calls `configure_gemini`, constructs services (`CacheManager`, parsers, scraper, resume writer), sidebar navigation, session init, delegates each screen to `GUI/pages/`. |
| `app_context.py` | `TailoringAppContext` protocol: the minimal attributes page modules need (`settings`, `active_settings`, service instances). |
| `session_keys.py` | `SessionKeys`: single source of truth for `st.session_state` / widget key strings. |
| `constants.py` | Repo paths (`TEMPLATES_DIR`, `PROJECT_ROOT`) and default Gemini/Claude model id presets for Settings. |
| `pages/tailor.py` | **Tailor Resume**: resume source, job URL, fetch, history, Claude tailor, editor, LaTeX/PDF, diff, downloads. |
| `pages/my_resume.py` | **My Resume**: edit `resume.md`, experience preview + append. |
| `pages/cache_manager_page.py` | **Cache Manager**: resume preview, job list/delete, usage metrics. |
| `pages/ai_logs_page.py` | **AI Logs**: live/manual log view; `@fragment(run_every=2)` for auto-refresh. |
| `pages/settings_page.py` | **Settings**: API key status, session model pickers, list Gemini models. |

## How it connects to the app

1. Root [`app.py`](../app.py) only calls `run_app()` from this package.
2. `ResumeTailoringApp.__init__` loads [`config`](../config.py), ensures cache directories exist, configures Gemini once via [`services/gemini_configure.py`](../services/gemini_configure.py), and constructs:
   - `CacheManager`
   - `LatexParserService`
   - `JobScraperService`
   - `ResumeWriterService` (templates path resolves to repo-root [`templates/`](../templates/) via `GUI/constants.py`).
3. `run()` sets Streamlit page options, initializes `st.session_state` keys (via `SessionKeys`), then routes to the page selected in the sidebar.

## Session state keys (conceptual)

Central definitions live in `session_keys.py`. The UI remembers:

- `tailored_markdown` — editable tailored draft (`st.text_area`); drives diff/compare and **Generate LaTeX & PDF**.
- `job_entry` — cached or freshly fetched job summary (`JobCacheEntry`).
- `job_posting_url` — URL field for fetch (bound to the widget; updates use `job_url_pending` + `rerun` to avoid Streamlit widget conflicts).
- `tailor_busy` / `last_tailored_tex_path` — loading spinner during Claude tailor; path to the last generated `.tex` for downloads.
- `experience_preview` — Gemini-formatted block before appending to `resume.md`.
- `resume_editor_value` — text shown in the “My Resume” editor.
- `ui_gemini_model` / `ui_claude_model` — session model ids (Settings).

## Design note

Keeping UI in `GUI/` makes it obvious where to change labels, layout, and flows without touching API clients or file cache logic in [`services/`](../services/). Page modules depend only on the `TailoringAppContext` protocol, not on each other.

## Model selection (session)

Gemini and Claude **model ids** can be chosen under **Settings → Models (this session)**. Values live in `st.session_state` (`SessionKeys.GEMINI_MODEL`, `SessionKeys.CLAUDE_MODEL`) and are merged into `active_settings` via `dataclasses.replace` in `ResumeTailoringApp.__init__`, so all services use the same ids without editing `.env`. **Reset to `.env` defaults** reloads baseline strings from [`config.get_settings()`](../config.py). Sidebar shows the active pair for a quick sanity check.

## Logging

`run_app()` calls [`logging_config.setup_logging()`](../logging_config.py) first. App wiring logs from `GUI.main`; screen-specific logs use the page module’s logger (e.g. `GUI.pages.tailor`). The AI Logs panel includes any logger under the `GUI.` package plus configured service modules (see [`services/ai_log_buffer.py`](../services/ai_log_buffer.py)). Failures use `logger.exception`.
