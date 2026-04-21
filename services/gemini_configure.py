"""Single place to configure the Google Generative AI client."""

from __future__ import annotations

import google.generativeai as genai


def configure_gemini(api_key: str) -> None:
    """Idempotent: configures ``genai`` when a non-empty API key is present."""
    if api_key:
        genai.configure(api_key=api_key)
