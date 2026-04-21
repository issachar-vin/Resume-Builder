"""Paths and UI presets shared by the Streamlit package."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"

DEFAULT_GEMINI_PRESETS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]
DEFAULT_CLAUDE_PRESETS = [
    "claude-sonnet-4-6",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
]
