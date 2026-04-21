from __future__ import annotations

import logging

import streamlit as st
from streamlit import fragment

from GUI.session_keys import SessionKeys
from services.ai_log_buffer import clear_ai_log_buffer, get_ai_log_lines

logger = logging.getLogger(__name__)


@fragment(run_every=2.0)
def ai_logs_live_block() -> None:
    lines = get_ai_log_lines(500)
    st.code("\n".join(lines) if lines else "(no AI log lines yet)", language=None)


def render_ai_logs_page() -> None:
    st.title("AI Logs")
    st.write(
        "Live **AI** logs: Gemini/Claude **requests** (model, rough size) and **responses** "
        "(counts, token metadata when available, **short preview**). Same output: terminal and "
        "`cache/logs/app.log`."
    )
    st.warning(
        "Previews may include **resume or job text**. Treat UI and log files as **sensitive**."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Clear on-screen buffer"):
            clear_ai_log_buffer()
            logger.info("AI log ring buffer cleared from UI")
            st.success("Cleared in-memory AI log buffer.")
    with c2:
        auto = st.checkbox(
            "Auto-refresh every 2s", value=True, key=SessionKeys.AI_LOGS_AUTO_REFRESH
        )

    if auto:
        ai_logs_live_block()
    else:
        lines = get_ai_log_lines(500)
        st.code("\n".join(lines) if lines else "(no AI log lines yet)", language=None)
        if st.button("Refresh", key=SessionKeys.AI_LOGS_MANUAL_REFRESH):
            st.rerun()
