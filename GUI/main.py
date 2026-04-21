from __future__ import annotations

import logging
from dataclasses import replace

import streamlit as st

from config import Settings, ensure_directories, get_settings
from GUI.constants import TEMPLATES_DIR
from GUI.pages.ai_logs_page import render_ai_logs_page
from GUI.pages.cache_manager_page import render_cache_manager_page
from GUI.pages.my_resume import render_my_resume_page
from GUI.pages.settings_page import render_settings_page
from GUI.pages.tailor import render_tailor_page
from GUI.session_keys import SessionKeys
from logging_config import setup_logging
from services.cache_manager import CacheManager
from services.gemini_configure import configure_gemini
from services.job_scraper import JobScraperService
from services.latex_parser import LatexParserService
from services.resume_writer import ResumeWriterService

logger = logging.getLogger(__name__)


class ResumeTailoringApp:
    """Wires settings and services and renders the Streamlit UI."""

    def __init__(self) -> None:
        self.settings: Settings = get_settings()
        ensure_directories(self.settings)
        configure_gemini(self.settings.gemini_api_key)

        if SessionKeys.GEMINI_MODEL not in st.session_state:
            st.session_state[SessionKeys.GEMINI_MODEL] = self.settings.gemini_model
        if SessionKeys.CLAUDE_MODEL not in st.session_state:
            st.session_state[SessionKeys.CLAUDE_MODEL] = self.settings.claude_model

        self.active_settings: Settings = replace(
            self.settings,
            gemini_model=st.session_state[SessionKeys.GEMINI_MODEL].strip(),
            claude_model=st.session_state[SessionKeys.CLAUDE_MODEL].strip(),
        )

        logger.info(
            "App init: cache=%s out=%s env_g=%s env_c=%s ui_g=%s ui_c=%s",
            self.settings.cache_dir,
            self.settings.output_dir,
            self.settings.gemini_model,
            self.settings.claude_model,
            self.active_settings.gemini_model,
            self.active_settings.claude_model,
        )
        self.cache_manager = CacheManager(self.settings.cache_dir, self.settings.output_dir)
        self.latex_parser = LatexParserService(self.active_settings, self.cache_manager)
        self.job_scraper = JobScraperService(self.active_settings, self.cache_manager)
        self.resume_writer = ResumeWriterService(
            self.active_settings, self.cache_manager, TEMPLATES_DIR
        )

    def run(self) -> None:
        st.set_page_config(page_title="Resume Tailoring App", layout="wide")
        self._init_session_state()

        page = st.sidebar.radio(
            "Navigate",
            ["Tailor Resume", "My Resume", "Cache Manager", "AI Logs", "Settings"],
        )
        g, c = self.active_settings.gemini_model, self.active_settings.claude_model
        st.sidebar.caption(f"Models (session): **{g}** · **{c}**")
        logger.info("UI page: %s", page)

        if page == "Tailor Resume":
            render_tailor_page(self)
        elif page == "My Resume":
            render_my_resume_page(self)
        elif page == "Cache Manager":
            render_cache_manager_page(self)
        elif page == "AI Logs":
            render_ai_logs_page()
        else:
            render_settings_page(self)

    def _init_session_state(self) -> None:
        if SessionKeys.TAILORED_MARKDOWN not in st.session_state:
            st.session_state[SessionKeys.TAILORED_MARKDOWN] = ""
        if SessionKeys.JOB_ENTRY not in st.session_state:
            st.session_state[SessionKeys.JOB_ENTRY] = None
        if SessionKeys.EXPERIENCE_PREVIEW not in st.session_state:
            st.session_state[SessionKeys.EXPERIENCE_PREVIEW] = ""
        if SessionKeys.RESUME_EDITOR_VALUE not in st.session_state:
            st.session_state[SessionKeys.RESUME_EDITOR_VALUE] = (
                self.cache_manager.read_resume_markdown()
            )
        if SessionKeys.LAST_TAILORED_TEX_PATH not in st.session_state:
            st.session_state[SessionKeys.LAST_TAILORED_TEX_PATH] = ""
        if SessionKeys.TAILOR_BUSY not in st.session_state:
            st.session_state[SessionKeys.TAILOR_BUSY] = False
        if SessionKeys.JOB_POSTING_URL not in st.session_state:
            st.session_state[SessionKeys.JOB_POSTING_URL] = ""


def run_app() -> None:
    """Entry point used by root `app.py` and `make run`."""
    setup_logging()
    ResumeTailoringApp().run()
