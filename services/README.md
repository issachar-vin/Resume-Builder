# Services (`services/`)

This folder contains **application logic**: file caching, LaTeX parsing, job scraping/summarization, and Claude-based tailoring. The GUI calls these services; they do not import Streamlit.

## Files

| File | Responsibility |
|------|----------------|
| `cache_manager.py` | Atomic reads/writes: `resume.md`, `jobs/<hash>.json`, `tailored/<hash>.md` (+ optional `tailored/archive/`), tailored `.tex` under **OUTPUT_DIR**, `usage_log.jsonl`. URL hashing and safe filename slugs. |
| `prompts.py` | Centralized Claude/Gemini prompts: section bodies use triple-quoted strings; `_blocks` joins labeled parts; `textwrap.dedent` where source indentation should not appear in the model-facing text. Tailoring, LaTeX→JSON extraction, job summary, experience formatting. |
| `latex_parser.py` | **One-time** path: if `resume.md` exists, returns it and does not re-parse `.tex`. Otherwise calls Gemini to extract structured resume data and writes canonical Markdown to `cache/resume.md`. |
| `job_scraper.py` | Fetches job URL with `httpx`, extracts text with BeautifulSoup, summarizes with Gemini into `JobData`, respects job JSON cache before network/API. Also formats new “experience” blocks via Gemini for the resume update flow. |
| `resume_writer.py` | `tailor_with_claude`: Anthropic **prompt caching** (system + cached resume + user job JSON from `prompts.py`); writes `cache/tailored/<hash>.md`. `build_tex_and_pdf`: Jinja render (`resume_v2` preamble + body, or `resume.tex.jinja` fallback), `save_output_tex`, `latex_assets`, `latex_build` (`pdflatex`). Logs usage for tailoring. |
| `markdown_resume.py` | Parses canonical `cache/resume.md` Markdown into `ExperienceEntry` / skills / education for LaTeX rendering; `latex_escape` + contact-line `\\href` helpers. |
| `latex_assets.py` | After each tailored `.tex` write, copies allowlisted files from repo `latex/` (`twentysecondcv.cls`, `template.tex`, images, …) into **OUTPUT_DIR** so `pdflatex` can run there without extra `TEXINPUTS`. |
| `latex_build.py` | Locates `pdflatex`, runs it twice with `TEXINPUTS` (output dir + repo `latex/`). Used when the UI runs **Generate LaTeX & PDF**. |
| `gemini_configure.py` | Single `configure_gemini(api_key)` call so `google.generativeai` is configured once at app startup (see `GUI/main.py`). |
| `gemini_text.py` | `strip_llm_code_fence`: normalizes Gemini outputs (JSON/Markdown in fences) before `json.loads` / display; shared by `latex_parser` and `job_scraper`. |
| `gemini_retry.py` | Wraps Gemini `generate_content` with retries/backoff on HTTP 429 / quota errors and a short actionable error if limits persist. |
| `gemini_models.py` | Calls `google.generativeai.list_models()` with the configured API key and returns rows (short id, display name, whether `generateContent` is supported) for the Settings UI. |
| `ai_log_buffer.py` | In-memory ring buffer + logging handler/filter so AI-related log lines can be shown in the Streamlit **AI Logs** page. Matches loggers by **module name tail** (e.g. `latex_parser`) plus any logger whose name starts with **`GUI.`** (Streamlit pages and `GUI.main`). |
| `ai_api_log.py` | Helpers to log Gemini/Claude response summaries (chars, tokens, truncated preview) for the GUI log. |

**PDF:** The app can run `pdflatex` from the UI when generating tailored output; you can also use **`make build path/to/file.tex`** (see root `makefile`); it prepends `latex/` to `TEXINPUTS`. Vendor copies in `OUTPUT_DIR` are for convenience when compiling from that folder alone.

## Data flow (high level)

```text
.tex (once) → latex_parser → cache/resume.md
job URL → job_scraper → cache/jobs/<hash>.json
resume.md + job → resume_writer.tailor_with_claude → cache/tailored/<hash>.md
edited markdown → resume_writer.build_tex_and_pdf → cache/outputs/<company>_<date>.tex (+ .pdf if pdflatex OK)
```

## Logging

All services use the standard `logging` module (`logger = logging.getLogger(__name__)`). Configure handlers once via root setup in [`logging_config.py`](../logging_config.py) (called from `run_app()`). Expect INFO for major operations (cache writes, API calls) and DEBUG for fine-grained steps when `LOG_LEVEL=DEBUG`.

## Dependencies

- **Gemini** (`google-generativeai`): parsing, job summarization, experience formatting.
- **Claude** (`anthropic` beta prompt caching): tailoring; system prompt forbids inventing experience.
- **httpx / beautifulsoup4**: scraping only when job cache misses.

See also: [`GUI/README.md`](../GUI/README.md) for how the Streamlit layer invokes these services.
