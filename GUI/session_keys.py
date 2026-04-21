"""Streamlit ``st.session_state`` and widget keys (single source of truth)."""


class SessionKeys:
    """Session state keys used across GUI pages."""

    GEMINI_MODEL = "ui_gemini_model"
    CLAUDE_MODEL = "ui_claude_model"

    TAILORED_MARKDOWN = "tailored_markdown"
    JOB_ENTRY = "job_entry"
    EXPERIENCE_PREVIEW = "experience_preview"
    RESUME_EDITOR_VALUE = "resume_editor_value"
    LAST_TAILORED_TEX_PATH = "last_tailored_tex_path"
    TAILOR_BUSY = "tailor_busy"
    JOB_POSTING_URL = "job_posting_url"
    NOTICE_JOB_SUMMARY = "notice_job_summary"
    NOTICE_TAILORED_LOADED = "notice_tailored_loaded"
    NOTICE_HISTORY_LOADED = "notice_history_loaded"
    JOB_URL_PENDING = "job_url_pending"
    TAILOR_HISTORY_PICK = "tailor_history_pick"
    GEMINI_MODEL_ROWS = "gemini_model_rows"
    GEMINI_MODEL_LIST_ERROR = "gemini_model_list_error"
    AI_LOGS_AUTO_REFRESH = "ai_logs_auto_refresh"
    AI_LOGS_MANUAL_REFRESH = "ai_logs_manual_refresh"
