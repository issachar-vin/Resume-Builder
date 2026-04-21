from __future__ import annotations

import logging
from dataclasses import dataclass

import google.generativeai as genai

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeminiModelRow:
    """One row from `genai.list_models()` for display / picking GEMINI_MODEL."""

    api_name: str
    """Full resource name, e.g. `models/gemini-1.5-flash`."""

    short_id: str
    """Value to use in `GEMINI_MODEL` / `GenerativeModel(...)`, e.g. `gemini-1.5-flash`."""

    display_name: str
    description: str
    supports_generate_content: bool


def list_available_gemini_models(api_key: str) -> list[GeminiModelRow]:
    """
    Ask Google's API which models this API key may use.

    Uses `google.generativeai.list_models()` (authenticated with your key). Only models
    that advertise `generateContent` are marked as suitable for this app.
    """
    if not api_key.strip():
        raise ValueError("GEMINI_API_KEY is empty; cannot list models.")

    genai.configure(api_key=api_key.strip())
    rows: list[GeminiModelRow] = []
    logger.info("Calling genai.list_models()")

    for m in genai.list_models():
        methods = list(getattr(m, "supported_generation_methods", None) or [])
        api_name = getattr(m, "name", "") or ""
        short_id = api_name.removeprefix("models/") if api_name.startswith("models/") else api_name
        rows.append(
            GeminiModelRow(
                api_name=api_name,
                short_id=short_id,
                display_name=str(getattr(m, "display_name", "") or ""),
                description=str(getattr(m, "description", "") or "")[:500],
                supports_generate_content="generateContent" in methods,
            )
        )

    out = sorted(rows, key=lambda r: r.short_id.lower())
    gen = sum(1 for r in out if r.supports_generate_content)
    logger.info("list_models: total=%s with_generateContent=%s", len(out), gen)
    return out
