from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import Settings
from models.job import JobData, UsageStats
from services.ai_api_log import log_claude_text_response
from services.cache_manager import CacheManager
from services.latex_assets import copy_vendor_latex_assets_to
from services.latex_build import build_pdf
from services.markdown_resume import (
    format_contact_for_latex,
    latex_escape,
    parse_resume_markdown,
    strip_gap_flags_section,
)
from services.prompts import (
    CLAUDE_TAILOR_SYSTEM,
    claude_tailor_user_message,
    claude_tailor_user_message_base_resume,
)

logger = logging.getLogger(__name__)


class ResumeWriterService:
    def __init__(
        self, settings: Settings, cache_manager: CacheManager, templates_dir: Path
    ) -> None:
        self.settings = settings
        self.cache_manager = cache_manager
        self.templates_dir = templates_dir
        self.client = (
            anthropic.Anthropic(api_key=settings.anthropic_api_key)
            if settings.anthropic_api_key
            else None
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=()),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.jinja_env.filters["latex_escape"] = latex_escape

    def tailor_with_claude(
        self,
        resume_markdown: str,
        job_data: JobData,
        job_hash: str,
        *,
        base_resume_only: bool = False,
    ) -> tuple[str, UsageStats]:
        """Run Claude tailoring, save ``cache/tailored/<job_hash>.md``, return markdown + usage."""
        if not self.client:
            raise ValueError("ANTHROPIC_API_KEY is required for resume tailoring.")

        logger.info(
            "Claude tailor_with_claude model=%s job_hash=%s company=%r base_only=%s chars=%s",
            self.settings.claude_model,
            job_hash,
            job_data.company,
            base_resume_only,
            len(resume_markdown),
        )
        user_content = (
            claude_tailor_user_message_base_resume()
            if base_resume_only
            else claude_tailor_user_message(json.dumps(job_data.model_dump(mode="json"), indent=2))
        )
        response = self.client.beta.messages.create(
            model=self.settings.claude_model,
            max_tokens=4096,
            betas=["prompt-caching-2024-07-31"],
            system=[
                {"type": "text", "text": CLAUDE_TAILOR_SYSTEM},
                {
                    "type": "text",
                    "text": resume_markdown,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        tailored_markdown = self._extract_text(response)
        log_claude_text_response(
            logger,
            tailored_markdown,
            operation="tailor_with_claude",
            usage=response.usage,
        )
        self.cache_manager.save_tailored_markdown(job_hash, tailored_markdown)

        usage = UsageStats(
            input_tokens=getattr(response.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(response.usage, "output_tokens", 0) or 0,
            cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0)
            or 0,
            timestamp=datetime.now(timezone.utc),
            company=job_data.company,
            job_hash=job_hash,
        )
        self.cache_manager.log_usage(usage)
        return tailored_markdown, usage

    def build_tex_and_pdf(self, tailored_markdown: str, job_data: JobData, job_hash: str) -> Path:
        """
        Persist tailored markdown to cache, render LaTeX, write ``.tex``, and build PDF.
        """
        self.cache_manager.save_tailored_markdown(
            job_hash, tailored_markdown, archive_previous=True
        )
        tex_output = self.render_latex(tailored_markdown, job_data)
        output_path = self.cache_manager.save_output_tex(job_data.company or "company", tex_output)
        copy_vendor_latex_assets_to(output_path.parent)
        build_pdf(output_path)
        return output_path

    @staticmethod
    def _extract_text(response: anthropic.types.beta.beta_message.BetaMessage) -> str:
        chunks: list[str] = []
        for block in response.content:
            text = getattr(block, "text", "")
            if text:
                chunks.append(text)
        return "\n".join(chunks).strip()

    def render_latex(self, tailored_markdown: str, job_data: JobData) -> str:
        logger.debug("Rendering LaTeX via Jinja for company=%s", job_data.company)
        generated_on = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Gap Flags are tailoring meta only — never ship them in .tex / PDF
        resume_md_for_tex = strip_gap_flags_section(tailored_markdown)
        try:
            parsed = parse_resume_markdown(resume_md_for_tex)
        except ValueError as exc:
            logger.warning(
                "Structured Markdown parse failed (%s); using verbatim LaTeX wrapper. "
                "Ensure tailored output follows cache/resume.md section headings.",
                exc,
            )
            return self.jinja_env.get_template("resume.tex.jinja").render(
                generated_on=generated_on,
                company=job_data.company,
                title=job_data.title,
                markdown_body=resume_md_for_tex,
            )
        preamble = (self.templates_dir / "resume_v2_preamble.tex").read_text(encoding="utf-8")
        body = self.jinja_env.get_template("resume_v2_body.jinja").render(
            full_name=parsed.full_name,
            contact_latex=format_contact_for_latex(parsed.contact_line_raw),
            summary=parsed.summary,
            experiences=parsed.experiences,
            education=parsed.education,
            skills=parsed.skills,
        )
        return preamble + body
