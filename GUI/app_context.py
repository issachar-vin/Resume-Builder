"""Protocol for Streamlit pages: services wired by ``ResumeTailoringApp``."""

from __future__ import annotations

from typing import Protocol

from config import Settings
from services.cache_manager import CacheManager
from services.job_scraper import JobScraperService
from services.latex_parser import LatexParserService
from services.resume_writer import ResumeWriterService


class TailoringAppContext(Protocol):
    """Minimal surface passed into per-page render functions."""

    settings: Settings
    active_settings: Settings
    cache_manager: CacheManager
    latex_parser: LatexParserService
    job_scraper: JobScraperService
    resume_writer: ResumeWriterService
