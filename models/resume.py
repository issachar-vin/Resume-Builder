from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ExperienceEntry(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: str
    location: str = ""
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str
    degree: str
    year: str

    @model_validator(mode="before")
    @classmethod
    def graduation_date_to_year(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if not (data.get("year") or "").strip():
            alt = data.get("graduation_date") or data.get("end_date") or data.get("graduation")
            if alt is not None:
                data = {**data, "year": str(alt).strip()}
        return data


class ResumeData(BaseModel):
    full_name: str
    contact_line: str
    summary: str
    experiences: list[ExperienceEntry] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    education: list[EducationEntry] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills_to_lists(cls, v: Any) -> dict[str, list[str]]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            return {}
        out: dict[str, list[str]] = {}
        for key, val in v.items():
            if isinstance(val, str):
                parts = [x.strip() for x in val.replace(";", ",").split(",")]
                out[str(key)] = [p for p in parts if p]
            elif isinstance(val, list):
                out[str(key)] = [str(x).strip() for x in val if str(x).strip()]
            else:
                out[str(key)] = []
        return out
