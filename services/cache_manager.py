from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from models.job import JobCacheEntry, UsageStats

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TailoredHistoryItem:
    job_hash: str
    company: str
    title: str
    url: str
    updated_at: datetime


class CacheManager:
    def __init__(self, cache_dir: Path, output_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.jobs_dir = cache_dir / "jobs"
        self.tailored_dir = cache_dir / "tailored"
        self.tailored_archive_dir = self.tailored_dir / "archive"
        self.output_dir = output_dir
        self.resume_md_path = cache_dir / "resume.md"
        self.usage_log_path = cache_dir / "usage_log.jsonl"

    @staticmethod
    def url_hash(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def safe_slug(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
        return cleaned.strip("_") or "unknown"

    def _atomic_write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)
        logger.debug("Wrote %s (%s bytes)", path, len(content.encode("utf-8")))

    def _atomic_write_json(self, path: Path, payload: dict[str, Any]) -> None:
        self._atomic_write_text(path, json.dumps(payload, indent=2, default=str))

    def resume_exists(self) -> bool:
        return self.resume_md_path.exists()

    def read_resume_markdown(self) -> str:
        if not self.resume_md_path.exists():
            return ""
        return self.resume_md_path.read_text(encoding="utf-8")

    def write_resume_markdown(self, markdown: str) -> None:
        self._atomic_write_text(self.resume_md_path, markdown)
        logger.info("Updated resume.md at %s", self.resume_md_path)

    def append_experience_markdown(self, experience_block: str) -> str:
        content = self.read_resume_markdown()
        if not content:
            raise ValueError("resume.md does not exist yet. Parse or create it first.")

        marker = "## Experience"
        idx = content.find(marker)
        if idx == -1:
            updated = content.rstrip() + f"\n\n{marker}\n\n{experience_block.strip()}\n"
            self.write_resume_markdown(updated)
            return updated

        next_section_match = re.search(r"\n##\s+", content[idx + len(marker) :])
        if next_section_match:
            insert_pos = idx + len(marker) + next_section_match.start()
            updated = (
                content[:insert_pos].rstrip()
                + "\n\n"
                + experience_block.strip()
                + "\n\n"
                + content[insert_pos:].lstrip("\n")
            )
        else:
            updated = content.rstrip() + "\n\n" + experience_block.strip() + "\n"

        self.write_resume_markdown(updated)
        return updated

    def get_job_cache_path(self, url: str) -> Path:
        return self.jobs_dir / f"{self.url_hash(url)}.json"

    def load_job_cache(self, url: str) -> JobCacheEntry | None:
        path = self.get_job_cache_path(url)
        if not path.exists():
            logger.debug("Job cache miss hash=%s", self.url_hash(url))
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        logger.debug("Job cache hit path=%s", path)
        return JobCacheEntry.model_validate(payload)

    def save_job_cache(self, entry: JobCacheEntry) -> None:
        path = self.jobs_dir / f"{entry.hash}.json"
        self._atomic_write_json(path, entry.model_dump(mode="json"))
        logger.info("Saved job cache hash=%s path=%s", entry.hash, path)

    def load_job_by_hash(self, job_hash: str) -> JobCacheEntry | None:
        path = self.jobs_dir / f"{job_hash}.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return JobCacheEntry.model_validate(payload)
        except Exception as exc:
            logger.warning("Invalid job cache %s: %s", path, exc)
            return None

    def tailored_markdown_path(self, job_hash: str) -> Path:
        return self.tailored_dir / f"{job_hash}.md"

    def load_tailored_markdown(self, job_hash: str) -> str | None:
        path = self.tailored_markdown_path(job_hash)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def has_tailored_markdown(self, job_hash: str) -> bool:
        return self.tailored_markdown_path(job_hash).is_file()

    def _archive_tailored_if_changed(self, job_hash: str, new_markdown: str) -> None:
        path = self.tailored_markdown_path(job_hash)
        if not path.is_file():
            return
        old = path.read_text(encoding="utf-8")
        if old == new_markdown:
            return
        self.tailored_archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        arc = self.tailored_archive_dir / f"{job_hash}_{stamp}.md"
        shutil.copy2(path, arc)
        logger.info("Archived prior tailored markdown -> %s", arc)

    def save_tailored_markdown(
        self, job_hash: str, markdown: str, *, archive_previous: bool = True
    ) -> Path:
        """Write ``cache/tailored/<job_hash>.md`` (optional archive if content changed)."""
        if archive_previous:
            self._archive_tailored_if_changed(job_hash, markdown)
        path = self.tailored_markdown_path(job_hash)
        self._atomic_write_text(path, markdown)
        logger.info("Saved tailored markdown hash=%s path=%s", job_hash, path)
        return path

    def list_tailored_history(self) -> list[TailoredHistoryItem]:
        """Newest first: rows for each job hash with tailored markdown and matching job JSON."""
        items: list[TailoredHistoryItem] = []
        if not self.tailored_dir.is_dir():
            return items
        for path in sorted(
            self.tailored_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            job_hash = path.stem
            entry = self.load_job_by_hash(job_hash)
            if not entry:
                continue
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            items.append(
                TailoredHistoryItem(
                    job_hash=job_hash,
                    company=entry.summary.company or "(unknown company)",
                    title=entry.summary.title or "(no title)",
                    url=entry.url,
                    updated_at=mtime,
                )
            )
        return items

    def list_job_caches(self) -> list[JobCacheEntry]:
        entries: list[JobCacheEntry] = []
        for file in sorted(self.jobs_dir.glob("*.json")):
            try:
                payload = json.loads(file.read_text(encoding="utf-8"))
                entries.append(JobCacheEntry.model_validate(payload))
            except Exception as exc:
                logger.warning("Skipping invalid job cache file %s: %s", file, exc)
                continue
        return sorted(entries, key=lambda x: x.cached_at, reverse=True)

    def delete_job_cache(self, job_hash: str) -> bool:
        path = self.jobs_dir / f"{job_hash}.json"
        if path.exists():
            path.unlink()
            logger.info("Deleted job cache path=%s", path)
            return True
        return False

    def save_output_tex(self, company: str, tex_content: str) -> Path:
        company_slug = self.safe_slug(company)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        output_path = self.output_dir / f"{company_slug}_{stamp}.tex"
        self._atomic_write_text(output_path, tex_content)
        logger.info("Wrote tailored TeX %s", output_path)
        return output_path

    def log_usage(self, stats: UsageStats) -> None:
        line = json.dumps(stats.model_dump(mode="json"), default=str)
        current = (
            self.usage_log_path.read_text(encoding="utf-8") if self.usage_log_path.exists() else ""
        )
        self._atomic_write_text(self.usage_log_path, current + line + "\n")
        logger.debug(
            "Logged usage job_hash=%s in=%s out=%s",
            stats.job_hash,
            stats.input_tokens,
            stats.output_tokens,
        )

    def load_usage_logs(self) -> list[UsageStats]:
        if not self.usage_log_path.exists():
            return []
        output: list[UsageStats] = []
        for raw_line in self.usage_log_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                output.append(UsageStats.model_validate(json.loads(raw_line)))
            except Exception:
                continue
        return output
