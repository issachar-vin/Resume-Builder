from __future__ import annotations

import json
import logging

import streamlit as st

from GUI.app_context import TailoringAppContext
from GUI.constants import DEFAULT_CLAUDE_PRESETS, DEFAULT_GEMINI_PRESETS
from GUI.session_keys import SessionKeys
from services.gemini_models import list_available_gemini_models

logger = logging.getLogger(__name__)


def render_settings_page(app: TailoringAppContext) -> None:
    st.title("Settings")
    st.write("Environment-backed settings. API keys are not written from the UI.")

    st.write("**API key status**")
    st.write(f"Anthropic key loaded: {'Yes' if bool(app.settings.anthropic_api_key) else 'No'}")
    st.write(f"Gemini key loaded: {'Yes' if bool(app.settings.gemini_api_key) else 'No'}")

    st.divider()
    st.subheader("Models (this session)")
    st.write(
        "Pick **Gemini** and **Claude** model ids. Selections apply **immediately** on the next "
        "rerun (no `.env` edit). Defaults load from `.env` on first open."
    )
    gemini_options = list(DEFAULT_GEMINI_PRESETS)
    rows = st.session_state.get(SessionKeys.GEMINI_MODEL_ROWS)
    if rows:
        gemini_options.extend(r.short_id for r in rows if r.supports_generate_content)
    cur_g = st.session_state[SessionKeys.GEMINI_MODEL]
    if cur_g not in gemini_options:
        gemini_options.insert(0, cur_g)
    gemini_options = sorted(set(gemini_options), key=str.lower)

    st.selectbox(
        "Gemini model (`GenerativeModel`)",
        options=gemini_options,
        key=SessionKeys.GEMINI_MODEL,
        help="Used for LaTeX parse, job summary, and experience formatting.",
    )

    cur_c = st.session_state[SessionKeys.CLAUDE_MODEL]
    claude_options = list(DEFAULT_CLAUDE_PRESETS)
    if cur_c not in claude_options:
        claude_options.insert(0, cur_c)
    claude_options = sorted(set(claude_options), key=str.lower)
    st.selectbox(
        "Claude model (tailor resume)",
        options=claude_options,
        key=SessionKeys.CLAUDE_MODEL,
        help="Used for resume tailoring with prompt caching.",
    )

    if st.button("Reset models to `.env` defaults"):
        st.session_state[SessionKeys.GEMINI_MODEL] = app.settings.gemini_model
        st.session_state[SessionKeys.CLAUDE_MODEL] = app.settings.claude_model
        logger.info("Reset UI models to .env defaults")
        st.rerun()

    st.write("**Baseline from `.env` (restart required to reload file)**")
    st.code(
        f"GEMINI_MODEL={app.settings.gemini_model}\nCLAUDE_MODEL={app.settings.claude_model}",
        language="properties",
    )

    st.write("**Directories**")
    st.code(
        json.dumps(
            {
                "CACHE_DIR": str(app.settings.cache_dir),
                "OUTPUT_DIR": str(app.settings.output_dir),
            },
            indent=2,
        )
    )

    st.divider()
    st.subheader("Gemini: models for your API key")
    st.write(
        "This calls Google's **`list_models`** API with your key — the authoritative list for "
        "what you can use (not a hardcoded guess)."
    )
    if st.button("Fetch available Gemini models", disabled=not bool(app.settings.gemini_api_key)):
        try:
            rows = list_available_gemini_models(app.settings.gemini_api_key)
            logger.info("Listed Gemini models: count=%s", len(rows))
            st.session_state[SessionKeys.GEMINI_MODEL_ROWS] = rows
            st.session_state[SessionKeys.GEMINI_MODEL_LIST_ERROR] = None
        except Exception as exc:
            logger.exception("List Gemini models failed")
            st.session_state[SessionKeys.GEMINI_MODEL_ROWS] = None
            st.session_state[SessionKeys.GEMINI_MODEL_LIST_ERROR] = str(exc)

    err = st.session_state.get(SessionKeys.GEMINI_MODEL_LIST_ERROR)
    if err:
        st.error(err)

    gemini_rows = st.session_state.get(SessionKeys.GEMINI_MODEL_ROWS)
    if gemini_rows is not None:
        usable = [r for r in gemini_rows if r.supports_generate_content]
        current = st.session_state[SessionKeys.GEMINI_MODEL].strip()
        if usable:
            ids = {r.short_id for r in usable}
            if current in ids:
                st.success(
                    f"Session model **`{current}`** is listed and supports `generateContent`."
                )
            else:
                st.warning(
                    f"Session Gemini model **`{current}`** is **not** among the listed models that "
                    "support `generateContent`. Pick another id or fetch the list again."
                )
            table = [
                {
                    "GEMINI_MODEL (short id)": r.short_id,
                    "Display name": r.display_name,
                    "API name": r.api_name,
                }
                for r in usable
            ]
            st.dataframe(table, use_container_width=True, hide_index=True)
        else:
            st.warning("No models reported `generateContent` — check API key and project access.")

        with st.expander("All models returned (including without generateContent)"):
            st.dataframe(
                [
                    {
                        "short id": r.short_id,
                        "generateContent": r.supports_generate_content,
                        "display_name": r.display_name,
                    }
                    for r in gemini_rows
                ],
                use_container_width=True,
                hide_index=True,
            )
