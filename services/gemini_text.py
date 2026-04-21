"""Helpers for normalizing Gemini (and similar) text outputs before JSON/Markdown parsing."""

from __future__ import annotations


def strip_llm_code_fence(text: str) -> str:
    """
    Remove optional `` ```lang ... ``` `` wrappers from model output.

    Handles ``json``, ``markdown``, bare fences, single-line and multi-line blocks.
    """
    s = text.strip()
    if not s.startswith("```"):
        return s
    s = s[3:].lstrip()
    for lang in ("json", "markdown"):
        if s.startswith(lang):
            s = s[len(lang) :].lstrip()
            break
    if s.startswith("\n"):
        s = s[1:]
    s = s.rstrip()
    if s.endswith("```"):
        s = s[:-3].rstrip()
    return s
