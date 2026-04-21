# Cache (`cache/`)

Runtime **file-based cache** for resume source, job summaries, tailored outputs, and usage logs. Paths default under `./cache` unless overridden by `CACHE_DIR` / `OUTPUT_DIR` in [`.env`](../.env.example).

## Layout

| Path | Purpose |
|------|---------|
| `resume.md` | **Source of truth** after the first LaTeX parse: human-editable Markdown. The app never re-parses `.tex` once this file exists. |
| `jobs/` | One JSON file per job URL: filename is the first 12 hex characters of SHA-256(URL). Stores URL, hash, cache time, raw text length, and structured `JobData` summary. |
| `tailored/` | One `<job_hash>.md` per posting: last tailored Markdown from Claude (or edited before **Generate**). |
| `tailored/archive/` | Optional snapshots of the previous `tailored/<hash>.md` when content is replaced (new tailor or generate with edits). |
| `outputs/` | Generated `.tex` and, when `pdflatex` succeeds, `.pdf` beside them — names like `<company_slug>_<YYYYMMDD>.tex` (company from job summary, date UTC). |
| `usage_log.jsonl` | One JSON object per line: Claude token usage including cache read/creation fields for the Cache Manager UI. |
| `logs/` | Application log files (default `app.log` with rotation). Configure via `LOG_FILE`, `LOG_DIR`, `LOG_LEVEL` in `.env`. |

## Operations

- **Read-heavy**: Tailoring reads `resume.md` and optionally a job cache hit without scraping.
- **Writes**: All writes go through [`services/cache_manager.py`](../services/cache_manager.py) using atomic temp-file + rename.

## Git

Generated files are usually gitignored in real use; this README documents intent so you know what appears on disk after running the app.
