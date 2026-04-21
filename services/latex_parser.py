from __future__ import annotations

import json
import logging

import google.generativeai as genai

from config import Settings
from models.resume import ResumeData
from services.cache_manager import CacheManager
from services.gemini_retry import generate_content_with_retry
from services.gemini_text import strip_llm_code_fence
from services.prompts import GEMINI_LATEX_TO_RESUME_JSON

logger = logging.getLogger(__name__)


class LatexParserService:
    def __init__(self, settings: Settings, cache_manager: CacheManager) -> None:
        self.settings = settings
        self.cache_manager = cache_manager

    def get_or_create_resume_markdown(self, latex_content: str | None) -> str:
        if self.cache_manager.resume_exists():
            logger.info(
                "[LaTeX] Skip Gemini parse: %s already exists. Delete that file if you want to "
                "re-import from a .tex upload.",
                self.cache_manager.resume_md_path,
            )
            return self.cache_manager.read_resume_markdown()

        if not latex_content:
            raise ValueError("Upload .tex content first because resume.md does not exist yet.")

        if not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for first-time LaTeX parsing.")

        logger.info(
            "[LaTeX] Parse start: sending uploaded .tex to Gemini model=%s (input ~%s chars)",
            self.settings.gemini_model,
            len(latex_content),
        )
        model = genai.GenerativeModel(self.settings.gemini_model)
        response = generate_content_with_retry(
            model,
            [GEMINI_LATEX_TO_RESUME_JSON, latex_content],
            operation="latex_to_markdown",
        )
        raw = strip_llm_code_fence((response.text or "").strip())
        payload = json.loads(raw)
        resume_data = ResumeData.model_validate(payload)
        markdown = self._resume_to_markdown(resume_data)
        self.cache_manager.write_resume_markdown(markdown)
        logger.info(
            "[LaTeX] Parse done: wrote %s (%s chars out)",
            self.cache_manager.resume_md_path,
            len(markdown),
        )
        return markdown

    @staticmethod
    def _resume_to_markdown(data: ResumeData) -> str:
        lines: list[str] = []
        lines.append(f"# {data.full_name}")
        lines.append(data.contact_line)
        lines.append("")
        lines.append("## Summary")
        lines.append(data.summary.strip())
        lines.append("")
        lines.append("## Skills")
        for category, items in data.skills.items():
            lines.append(f"**{category}**: {', '.join(items)}")
        lines.append("")

        lines.append("## Experience")
        lines.append("")
        for exp in data.experiences:
            lines.append(f"### {exp.company} — {exp.title}")
            lines.append(f"*{exp.start_date} – {exp.end_date}*")
            for bullet in exp.bullets:
                lines.append(f"- {bullet}")
            lines.append("")

        lines.append("## Education")
        lines.append("")
        for edu in data.education:
            lines.append(f"### {edu.institution} — {edu.degree}")
            lines.append(f"*{edu.year}*")
            lines.append("")

        return "\n".join(lines).strip() + "\n"
