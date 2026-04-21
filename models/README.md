# Models (`models/`)

This folder defines **Pydantic data structures** used across services and the UI. They document the “shape” of resume content, job postings, and usage metrics so JSON parsing and validation stay consistent.

## Files

| File | Purpose |
|------|---------|
| `resume.py` | `ResumeData` and nested types: experience entries, education, skills map. Used when Gemini converts LaTeX into structured data before serializing to Markdown. |
| `job.py` | `JobData` (structured job posting summary), `JobCacheEntry` (URL + hash + timestamps + summary for disk cache), `UsageStats` (token counts per Claude request for the cache manager UI). |

## Why Pydantic

- Validates API responses (Gemini JSON, cache files) at load time.
- Gives clear error messages when cached JSON drifts from the expected schema.
- Serializes cleanly with `model_dump()` for Streamlit `st.json` and file writes.

## Relationship to Markdown

`ResumeData` is an intermediate representation: the **canonical user-editable source** on disk is still [`cache/resume.md`](../cache/README.md) in Markdown form. Models help the LaTeX parsing step; day-to-day editing does not require touching these Python types directly.
