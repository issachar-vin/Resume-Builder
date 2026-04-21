from __future__ import annotations

import logging
import re
import time
from typing import Any

from services.ai_api_log import log_gemini_text_response

logger = logging.getLogger(__name__)

try:
    from google.api_core import exceptions as google_api_exceptions
except ImportError:  # pragma: no cover
    google_api_exceptions = None  # type: ignore[assignment]


def generate_content_with_retry(
    model: Any,
    parts: list[Any],
    *,
    max_attempts: int = 5,
    operation: str = "generate_content",
) -> Any:
    """
    Call model.generate_content(parts) with retries on rate limits / quota (429).

    Free-tier limits are per model; switching GEMINI_MODEL may help. Persistent
    quota errors require billing or waiting (see Google Cloud / AI Studio docs).
    """
    delay = 2.0
    last_exc: BaseException | None = None
    model_id = (
        getattr(model, "model_name", None)
        or getattr(model, "_model_id", None)
        or type(model).__name__
    )
    logger.info(
        "AI Gemini [%s] request model=%s parts=%s (max_attempts=%s)",
        operation,
        model_id,
        len(parts),
        max_attempts,
    )

    for attempt in range(max_attempts):
        try:
            logger.debug("Gemini generate_content attempt %s/%s", attempt + 1, max_attempts)
            resp = model.generate_content(parts)
            log_gemini_text_response(logger, resp, operation=operation)
            return resp
        except BaseException as exc:
            last_exc = exc
            if not _is_retryable_gemini_error(exc):
                logger.error("Gemini generate_content failed (non-retryable): %s", exc)
                raise
            if attempt >= max_attempts - 1:
                logger.error("Gemini generate_content exhausted retries: %s", exc)
                break
            wait = _retry_wait_seconds(exc, fallback=delay)
            logger.warning(
                "Gemini rate limited/quota (attempt %s/%s); sleeping %.1fs: %s",
                attempt + 1,
                max_attempts,
                wait,
                exc,
            )
            delay = min(delay * 2.0, 120.0)
            time.sleep(wait)

    raise RuntimeError(
        "Gemini API rate limit or quota exceeded (HTTP 429). Options: wait and retry; set "
        "GEMINI_MODEL to another model with quota (e.g. gemini-1.5-flash); enable billing for "
        "your Google AI project; check usage at https://ai.dev/rate-limit and "
        "https://ai.google.dev/gemini-api/docs/rate-limits"
    ) from last_exc


def _is_retryable_gemini_error(exc: BaseException) -> bool:
    if google_api_exceptions and isinstance(exc, google_api_exceptions.ResourceExhausted):
        return True
    msg = str(exc).lower()
    return "429" in str(exc) or "resource exhausted" in msg or "quota" in msg or "rate limit" in msg


def _retry_wait_seconds(exc: BaseException, *, fallback: float) -> float:
    m = re.search(r"retry(?: in| after)?[:\s]+([0-9.]+)\s*s", str(exc), re.I)
    if m:
        return min(float(m.group(1)) + 0.5, 90.0)
    return min(fallback, 60.0)
