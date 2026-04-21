from __future__ import annotations

import logging

import streamlit as st

from GUI.app_context import TailoringAppContext
from GUI.session_keys import SessionKeys

logger = logging.getLogger(__name__)


def render_my_resume_page(app: TailoringAppContext) -> None:
    st.title("My Resume")

    st.subheader("Edit resume.md")
    st.session_state[SessionKeys.RESUME_EDITOR_VALUE] = st.text_area(
        "resume.md",
        value=st.session_state[SessionKeys.RESUME_EDITOR_VALUE],
        height=450,
    )
    if st.button("Save resume.md", type="primary"):
        try:
            app.cache_manager.write_resume_markdown(
                st.session_state[SessionKeys.RESUME_EDITOR_VALUE]
            )
            logger.info(
                "Saved resume.md (%s chars)",
                len(st.session_state[SessionKeys.RESUME_EDITOR_VALUE]),
            )
            st.success("Saved cache/resume.md")
        except Exception as exc:
            logger.exception("Save resume.md failed")
            st.error(str(exc))

    st.divider()
    st.subheader("Update my resume")
    with st.form("add_experience_form"):
        company = st.text_input("Company")
        title = st.text_input("Title")
        start = st.text_input("Start Date")
        end = st.text_input("End Date")
        bullets_raw = st.text_area("3-5 bullet points (one per line)")
        preview_btn = st.form_submit_button("Generate Preview")

    if preview_btn:
        bullets = [line.strip() for line in bullets_raw.splitlines() if line.strip()]
        try:
            logger.info(
                "Experience preview: company=%s title=%s bullets=%s",
                company,
                title,
                len(bullets),
            )
            preview = app.job_scraper.format_experience_with_gemini(
                company, title, start, end, bullets
            )
            st.session_state[SessionKeys.EXPERIENCE_PREVIEW] = preview
        except Exception as exc:
            logger.exception("Experience preview (Gemini) failed")
            st.error(str(exc))

    if st.session_state.get(SessionKeys.EXPERIENCE_PREVIEW):
        st.markdown("### Preview")
        st.code(st.session_state[SessionKeys.EXPERIENCE_PREVIEW])
        if st.button("Confirm and Append to Experience"):
            try:
                updated = app.cache_manager.append_experience_markdown(
                    st.session_state[SessionKeys.EXPERIENCE_PREVIEW]
                )
                st.session_state[SessionKeys.RESUME_EDITOR_VALUE] = updated
                logger.info("Appended experience block to resume.md")
                st.success("Appended new experience to resume.md. Review and Save if needed.")
            except Exception as exc:
                logger.exception("Append experience failed")
                st.error(str(exc))
