from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
    source: Literal["url", "manual"] = Field(
        default="url",
        description="url: text from HTTP fetch; manual: user pasted the posting (same listing URL).",
    )


class UsageStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    timestamp: datetime
    company: str = ""
    job_hash: str = ""
