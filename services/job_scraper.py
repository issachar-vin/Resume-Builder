from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import google.generativeai as genai
import httpx
from bs4 import BeautifulSoup

from config import Settings
from models.job import JobCacheEntry, JobData
from services.cache_manager import CacheManager
from services.gemini_retry import generate_content_with_retry
from services.gemini_text import strip_llm_code_fence
from services.prompts import GEMINI_FORMAT_EXPERIENCE_BLOCK, GEMINI_JOB_POSTING_SUMMARY

logger = logging.getLogger(__name__)

# Minimum pasted characters for manual summarization (avoid empty / accidental submits).
MIN_MANUAL_PASTE_CHARS = 80


class JobScraperService:
    def __init__(self, settings: Settings, cache_manager: CacheManager) -> None:
        self.settings = settings
        self.cache_manager = cache_manager

    def get_job_data(self, url: str) -> tuple[JobCacheEntry, bool]:
        cached = self.cache_manager.load_job_cache(url)
        if cached:
            logger.info("Job data from cache hash=%s", cached.hash)
            return cached, True

        if not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for job summarization.")

        logger.info("Fetching job URL (no cache): %s", url)
        raw_text = self._fetch_job_text(url)
        logger.debug("Extracted job text length=%s", len(raw_text))
        summary = self._summarize_job(raw_text)
        entry = JobCacheEntry(
            url=url,
            hash=self.cache_manager.url_hash(url),
            cached_at=datetime.now(timezone.utc),
            raw_text_length=len(raw_text),
            summary=summary,
            source="url",
        )
        self.cache_manager.save_job_cache(entry)
        logger.info("Job summarized: company=%s title=%s", summary.company, summary.title)
        return entry, False

    def summarize_pasted_posting(self, job_url: str, pasted_text: str) -> JobCacheEntry:
        """
        Build job JSON from user-pasted posting text, tied to the listing URL (same cache key
        as URL fetches: `url_hash` on the URL). Overwrites any existing `cache/jobs` entry for
        that URL. Does not re-read from cache before summarizing.
        """
        trimmed_url = (job_url or "").strip()
        if not trimmed_url:
            raise ValueError(
                "Job URL is required so the listing is linked in your cache and tailoring."
            )
        if not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for job summarization.")
        raw = self._compact_visible_text(pasted_text)
        if len(raw) < MIN_MANUAL_PASTE_CHARS:
            raise ValueError(
                f"Pasted text is too short ({len(raw)} characters). "
                f"Add at least {MIN_MANUAL_PASTE_CHARS} characters of the job description."
            )
        logger.info("Summarizing pasted job text url=%s raw_len=%s", trimmed_url, len(raw))
        summary = self._summarize_job(raw)
        entry = JobCacheEntry(
            url=trimmed_url,
            hash=self.cache_manager.url_hash(trimmed_url),
            cached_at=datetime.now(timezone.utc),
            raw_text_length=len(raw),
            summary=summary,
            source="manual",
        )
        self.cache_manager.save_job_cache(entry)
        logger.info("Pasted job summarized: company=%s title=%s", summary.company, summary.title)
        return entry

    @staticmethod
    def _compact_visible_text(text: str) -> str:
        return "\n".join(line for line in text.splitlines() if line.strip())

    def _fetch_job_text(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        with httpx.Client(timeout=25.0, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            logger.debug(
                "HTTP GET %s -> %s bytes=%s", url, response.status_code, len(response.text)
            )

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Empty <main> shells on SPAs: try several roots and pick the richest text.
        min_useful = 120
        candidates: list[str] = []

        for sel in (
            "main",
            "article",
            "[role='main']",
            "#job-description",
            "#jobdetails",
            ".job-description",
            ".jobDescription",
        ):
            el = soup.select_one(sel)
            if el:
                c = self._compact_visible_text(el.get_text("\n", strip=True))
                if c:
                    candidates.append(c)

        if soup.body:
            c = self._compact_visible_text(soup.body.get_text("\n", strip=True))
            if c:
                candidates.append(c)

        c = self._compact_visible_text(soup.get_text("\n", strip=True))
        if c:
            candidates.append(c)

        if not candidates:
            logger.warning(
                "No text nodes after parse url=%s html_len=%s preview=%r",
                url,
                len(response.text),
                response.text[:400],
            )
            raise ValueError(
                "Could not extract readable text from this URL (empty HTML or blocked page). "
                "Try a public job page, paste the description into a gist and use that URL, "
                "or use a site that serves HTML without requiring JavaScript for the posting body."
            )

        # Prefer the longest block that looks like real copy; else take longest overall.
        good = [x for x in candidates if len(x) >= min_useful]
        chosen = max(good, key=len) if good else max(candidates, key=len)
        if len(chosen) < min_useful:
            logger.warning(
                "Very little text extracted (%s chars) from %s — summary quality may be poor.",
                len(chosen),
                url,
            )
        return chosen

    def _summarize_job(self, raw_text: str) -> JobData:
        logger.info("Summarizing job posting with Gemini model=%s", self.settings.gemini_model)
        model = genai.GenerativeModel(self.settings.gemini_model)
        response = generate_content_with_retry(
            model,
            [GEMINI_JOB_POSTING_SUMMARY, raw_text[:25000]],
            operation="job_posting_summary",
        )
        raw = strip_llm_code_fence((response.text or "").strip())
        payload = json.loads(raw)
        return JobData.model_validate(payload)

    def format_experience_with_gemini(
        self,
        company: str,
        title: str,
        start_date: str,
        end_date: str,
        bullets: list[str],
    ) -> str:
        if not self.settings.gemini_api_key:
            logger.info("Formatting experience without Gemini (no API key)")
            block = [f"### {company} — {title}", f"*{start_date} – {end_date}*"]
            block.extend([f"- {b.strip()}" for b in bullets if b.strip()])
            return "\n".join(block)

        logger.info("Formatting experience with Gemini model=%s", self.settings.gemini_model)
        model = genai.GenerativeModel(self.settings.gemini_model)
        content = json.dumps(
            {
                "company": company,
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "bullets": bullets,
            }
        )
        response = generate_content_with_retry(
            model, [GEMINI_FORMAT_EXPERIENCE_BLOCK, content], operation="format_experience"
        )
        return strip_llm_code_fence((response.text or "").strip())
