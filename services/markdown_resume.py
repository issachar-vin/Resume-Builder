"""Parse resume.md-shaped Markdown (including tailored copies) into LaTeX-friendly structures."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from models.resume import EducationEntry, ExperienceEntry

logger = logging.getLogger(__name__)

EM_DASH = "\u2014"
EN_DASH = "\u2013"


@dataclass
class ParsedResumeForTex:
    """Structured resume derived from Markdown (Gap Flags stripped before parse for LaTeX)."""

    full_name: str
    contact_line_raw: str
    summary: str
    experiences: list[ExperienceEntry] = field(default_factory=list)
    skills: dict[str, list[str]] = field(default_factory=dict)
    education: list[EducationEntry] = field(default_factory=list)


def latex_escape(s: str) -> str:
    """Escape text for LaTeX inside \\resumeItem{...} etc."""
    if not s:
        return ""
    out = (
        s.replace("\\", r"\textbackslash{}")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("$", r"\$")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("^", r"\textasciicircum{}")
        .replace("~", r"\textasciitilde{}")
    )
    return out


def format_contact_for_latex(contact_line: str) -> str:
    """Turn `phone | email | linkedin | github` into LaTeX with \\href where useful."""
    if not contact_line.strip():
        return ""
    parts = [p.strip() for p in contact_line.split("|") if p.strip()]
    blocks: list[str] = []
    for p in parts:
        esc = latex_escape(p)
        if "@" in p and " " not in p and "." in p:
            blocks.append(rf"\href{{mailto:{p}}}{{\underline{{{esc}}}}}")
        elif p.startswith("http://") or p.startswith("https://"):
            blocks.append(rf"\href{{{p}}}{{\underline{{{esc}}}}}")
        elif "linkedin.com" in p or "github.com" in p:
            url = p if p.startswith("http") else f"https://{p}"
            blocks.append(rf"\href{{{url}}}{{\underline{{{esc}}}}}")
        else:
            blocks.append(esc)
    return r" $|$ ".join(blocks)


def _split_company_title(line: str) -> tuple[str, str]:
    """`### Company — Title` → (company, title)."""
    s = line.strip()
    if s.startswith("### "):
        s = s[4:].strip()
    for sep in (f" {EM_DASH} ", f" {EN_DASH} ", " — ", " – ", " - "):
        if sep in s:
            a, b = s.split(sep, 1)
            return a.strip(), b.strip()
    return s, ""


def _parse_date_line(line: str) -> tuple[str, str]:
    """`*May 2025 – May 2026*` → start, end."""
    s = line.strip().strip("*").strip()
    for sep in (f" {EN_DASH} ", f" {EM_DASH} ", " – ", " — ", " - ", " -- "):
        if sep in s:
            a, b = s.split(sep, 1)
            return a.strip(), b.strip()
    return s, ""


def _parse_skills_line(line: str) -> tuple[str, list[str]] | None:
    m = re.match(r"^\*\*(.+?)\*\*:\s*(.+)\s*$", line.strip())
    if not m:
        return None
    cat = m.group(1).strip()
    raw = m.group(2).strip()
    items = [x.strip() for x in re.split(r",|;", raw) if x.strip()]
    return cat, items


def strip_gap_flags_section(md: str) -> str:
    """Strip ``## Gap Flags`` and everything after (tailoring meta; omit from exported PDF)."""
    lines = md.splitlines()
    out: list[str] = []
    for line in lines:
        if line.strip().casefold() == "## gap flags":
            break
        out.append(line)
    text = "\n".join(out).rstrip()
    return text + "\n" if text else ""


def parse_resume_markdown(md: str) -> ParsedResumeForTex:
    """Parse Markdown shaped like `services/latex_parser._resume_to_markdown` output."""
    text = md.strip()
    if not text:
        raise ValueError("empty markdown")

    lines = text.splitlines()
    idx = 0
    if not lines[0].startswith("# "):
        raise ValueError("first line must be '# Full Name'")
    full_name = lines[0][2:].strip()
    if not full_name:
        raise ValueError("missing full name")

    idx = 1
    contact = lines[idx].strip() if idx < len(lines) else ""
    idx += 1

    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    sections: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current, buf
        if current is not None:
            sections[current] = buf[:]
        buf = []

    while idx < len(lines):
        line = lines[idx]
        if line.startswith("## "):
            flush()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
        idx += 1
    flush()

    summary = " ".join(s.strip() for s in sections.get("Summary", []) if s.strip()).strip()
    if not summary:
        raise ValueError("missing ## Summary")

    experiences: list[ExperienceEntry] = []
    exp_lines = sections.get("Experience", [])
    i = 0
    while i < len(exp_lines):
        row = exp_lines[i].rstrip()
        if row.startswith("### "):
            company, title = _split_company_title(row)
            i += 1
            start_d, end_d = "", ""
            if i < len(exp_lines) and exp_lines[i].strip().startswith("*"):
                start_d, end_d = _parse_date_line(exp_lines[i])
                i += 1
            bullets: list[str] = []
            while i < len(exp_lines):
                bl = exp_lines[i]
                if bl.startswith("### "):
                    break
                if bl.strip().startswith("- "):
                    bullets.append(bl.strip()[2:].strip())
                i += 1
            experiences.append(
                ExperienceEntry(
                    company=company or "Unknown",
                    title=title or "Role",
                    start_date=start_d or "",
                    end_date=end_d or "",
                    bullets=bullets,
                )
            )
            continue
        i += 1

    if not experiences:
        raise ValueError("no experience blocks (### under ## Experience)")

    skills: dict[str, list[str]] = {}
    for sl in sections.get("Skills", []):
        parsed = _parse_skills_line(sl)
        if parsed:
            skills[parsed[0]] = parsed[1]

    education: list[EducationEntry] = []
    edu_lines = sections.get("Education", [])
    j = 0
    while j < len(edu_lines):
        row = edu_lines[j].rstrip()
        if row.startswith("### "):
            institution, degree = _split_company_title(row)
            j += 1
            year = ""
            if j < len(edu_lines) and edu_lines[j].strip().startswith("*"):
                year = edu_lines[j].strip().strip("*").strip()
                j += 1
            education.append(
                EducationEntry(
                    institution=institution or "School",
                    degree=degree or "",
                    year=year or "",
                )
            )
            continue
        j += 1

    return ParsedResumeForTex(
        full_name=full_name,
        contact_line_raw=contact,
        summary=summary,
        experiences=experiences,
        skills=skills,
        education=education,
    )
