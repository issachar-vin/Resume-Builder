from __future__ import annotations

import json
import logging

import streamlit as st

from GUI.app_context import TailoringAppContext
from GUI.constants import DEFAULT_CLAUDE_PRESETS, DEFAULT_GEMINI_PRESETS
from GUI.session_keys import SessionKeys
from services.gemini_models import gemini_help_links, list_available_gemini_models

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
        "This calls Google's **`list_models`** API (same `Model` metadata as in the "
        "[developer docs](https://ai.google.dev/api/models)): token limits, supported methods "
        "(`generateContent`, `countTokens`, …), and default generation parameters."
    )
    st.info(
        "Google does **not** include your **remaining free-tier budget** or how many requests "
        "you have used in the last minute in this response — only model capabilities. For "
        "**rate limit tables** and **usage** for your key, use the official links below."
    )
    link_cols = st.columns(4)
    for i, (label, url) in enumerate(gemini_help_links().items()):
        with link_cols[i % 4]:
            st.markdown(f"[{label}]({url})")

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

        def _row_table(r, *, preview_chars: int = 200) -> dict:
            return {
                "short id (set GEMINI_MODEL)": r.short_id,
                "display name": r.display_name,
                "version": r.version,
                "base model id": r.base_model_id,
                "input token limit": r.input_token_limit,
                "output token limit": r.output_token_limit,
                "generateContent": r.supports_generate_content,
                "methods": ", ".join(r.supported_generation_methods),
                "temperature": r.temperature,
                "max_temperature": r.max_temperature,
                "top_p": r.top_p,
                "top_k": r.top_k,
                "description (preview)": (
                    (r.description[:preview_chars] + "…")
                    if len(r.description) > preview_chars
                    else r.description
                ),
            }

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
            st.dataframe(
                [_row_table(r) for r in usable],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("No models reported `generateContent` — check API key and project access.")

        with st.expander("All models (including those without `generateContent`)"):
            st.dataframe(
                [_row_table(r) for r in gemini_rows],
                use_container_width=True,
                hide_index=True,
            )

        with st.expander("Full JSON for one model (exact API fields from `list_models`)"):
            st.caption(
                "Pulled from the same response as the table: values match what the Gemini API "
                "returns for that model (useful to compare with the docs or to debug)."
            )
            if not gemini_rows:
                st.caption("No model rows in the last fetch.")
            else:
                by_id = {r.short_id: r for r in gemini_rows}
                pick = st.selectbox(
                    "Model", options=[r.short_id for r in gemini_rows], key="gemini_model_json_pick"
                )
                if pick in by_id:
                    st.json(by_id[pick].raw)
