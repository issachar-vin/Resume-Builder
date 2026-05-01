from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Sentinel URL / cache identity for “no job posting” (not written to disk as a normal job scrape).
BASE_RESUME_JOB_URL = "resume://base"


class JobData(BaseModel):
    title: str = ""
    company: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    seniority_level: str = ""
    key_themes: list[str] = Field(default_factory=list)


class JobCacheEntry(BaseModel):
    url: str
    hash: str
    cached_at: datetime
    raw_text_length: int
    summary: JobData
    source: Literal["url", "manual", "base"] = Field(
        default="url",
        description="url: HTTP fetch; manual: pasted posting; base: no job, use resume only.",
    )


class UsageStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    timestamp: datetime
    company: str = ""
    job_hash: str = ""
