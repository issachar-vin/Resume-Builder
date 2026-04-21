from __future__ import annotations

import logging
from typing import Any


def log_gemini_text_response(logger: logging.Logger, response: Any, *, operation: str) -> None:
    """Log Gemini `generate_content` outcome: size, token metadata, short preview (for GUI log)."""
    text = ""
    try:
        text = (response.text or "").strip() if response else ""
    except Exception as exc:
        logger.warning("Gemini [%s]: could not read response text: %s", operation, exc)
        return

    preview = text[:500].replace("\n", " ")
    if len(text) > 500:
        preview += " …"

    um = getattr(response, "usage_metadata", None)
    tok_bits: list[str] = []
    if um is not None:
        for label, attr in (
            ("prompt_tok", "prompt_token_count"),
            ("output_tok", "candidates_token_count"),
            ("total_tok", "total_token_count"),
        ):
            v = getattr(um, attr, None)
            if v is not None:
                tok_bits.append(f"{label}={v}")

    logger.info(
        "AI Gemini [%s] response chars=%s %s preview=%r",
        operation,
        len(text),
        " ".join(tok_bits),
        preview,
    )


def log_claude_text_response(
    logger: logging.Logger,
    text: str,
    *,
    operation: str,
    usage: Any | None = None,
) -> None:
    """Log Claude text output summary for the GUI log."""
    preview = text[:500].replace("\n", " ")
    if len(text) > 500:
        preview += " …"
    u = ""
    if usage is not None:
        u = (
            f"in={getattr(usage, 'input_tokens', 0)} out={getattr(usage, 'output_tokens', 0)} "
            f"cache_read={getattr(usage, 'cache_read_input_tokens', 0)} "
            f"cache_create={getattr(usage, 'cache_creation_input_tokens', 0)}"
        )
    logger.info(
        "AI Claude [%s] response chars=%s %s preview=%r",
        operation,
        len(text),
        u,
        preview,
    )
