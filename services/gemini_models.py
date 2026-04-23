from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

import google.generativeai as genai
from google.generativeai.types import model_types

logger = logging.getLogger(__name__)

_GEMINI_DOCS = "https://ai.google.dev/gemini-api/docs/models"
_GEMINI_RATE_LIMITS = "https://ai.google.dev/gemini-api/docs/rate-limits"
_AI_STUDIO_USAGE = "https://aistudio.google.com/usage"
_AI_DEV_RATE = "https://ai.dev/rate-limit"


@dataclass
class GeminiModelRow:
    """One row from `genai.list_models()` (Google’s `v1beta` models list) for display / picking.

    The API returns **model capabilities** (token limits, supported methods, defaults).
    It does **not** include your remaining free-tier budget or per-minute *consumption*;
    for that, use the official usage / Cloud Console links in Settings.

    `raw` is the full `Model` as a dict (SDK `asdict`, same as the API response) for
    `st.json` and debugging.
    """

    api_name: str
    """Full resource name, e.g. `models/gemini-1.5-flash`."""

    short_id: str
    """Value to use in `GEMINI_MODEL` / `GenerativeModel(...)`, e.g. `gemini-1.5-flash`."""

    display_name: str
    description: str
    version: str
    base_model_id: str
    input_token_limit: int
    output_token_limit: int
    supported_generation_methods: tuple[str, ...]
    supports_generate_content: bool
    temperature: float | None
    max_temperature: float | None
    top_p: float | None
    top_k: int | None
    raw: dict[str, Any]


def gemini_help_links() -> dict[str, str]:
    """Official URLs (labels → URL) for model docs, rate limits, and usage UIs."""
    return {
        "Model reference (all models)": _GEMINI_DOCS,
        "Rate limits (docs)": _GEMINI_RATE_LIMITS,
        "View usage in Google AI Studio": _AI_STUDIO_USAGE,
        "ai.dev / rate limit": _AI_DEV_RATE,
    }


def _row_from_sdk_model(m: model_types.Model) -> GeminiModelRow:
    methods = tuple(m.supported_generation_methods or [])
    api_name = m.name or ""
    short_id = api_name.removeprefix("models/") if api_name.startswith("models/") else api_name
    raw: dict[str, Any] = asdict(m)
    return GeminiModelRow(
        api_name=api_name,
        short_id=short_id,
        display_name=str(m.display_name or ""),
        description=str(m.description or "")[:2000],
        version=str(m.version or ""),
        base_model_id=str(m.base_model_id or ""),
        input_token_limit=int(m.input_token_limit or 0),
        output_token_limit=int(m.output_token_limit or 0),
        supported_generation_methods=methods,
        supports_generate_content="generateContent" in methods,
        temperature=m.temperature,
        max_temperature=m.max_temperature,
        top_p=m.top_p,
        top_k=m.top_k,
        raw=raw,
    )


def list_available_gemini_models(api_key: str) -> list[GeminiModelRow]:
    """
    Ask Google's API which models this API key may use.

    Uses `google.generativeai.list_models()` (GET .../v1beta/models) — the same metadata
    Google documents for `Model` (limits, `supportedGenerationMethods`, defaults). This
    does not include per-project **quota used**; see `gemini_help_links()`.
    """
    if not api_key.strip():
        raise ValueError("GEMINI_API_KEY is empty; cannot list models.")

    genai.configure(api_key=api_key.strip())
    rows: list[GeminiModelRow] = []
    logger.info("Calling genai.list_models()")

    for m in genai.list_models():
        if not isinstance(m, model_types.Model):
            logger.warning("Unexpected type from list_models: %r", type(m))
            continue
        rows.append(_row_from_sdk_model(m))

    out = sorted(rows, key=lambda r: r.short_id.lower())
    gen = sum(1 for r in out if r.supports_generate_content)
    logger.info("list_models: total=%s with_generateContent=%s", len(out), gen)
    return out
