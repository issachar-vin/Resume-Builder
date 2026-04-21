from __future__ import annotations

import logging
import threading
from collections import deque

# Logger name tails for the Streamlit "AI Logs" panel (prefix match, e.g. ``services.*``).
_AI_MODULE_TAILS: frozenset[str] = frozenset(
    {
        "latex_parser",
        "job_scraper",
        "resume_writer",
        "gemini_retry",
        "gemini_models",
    }
)


def _logger_matches_ai_panel(name: str) -> bool:
    """True for service AI modules and Streamlit GUI pages (parse button, etc.)."""
    if name.startswith("GUI."):
        return True
    tail = name.rsplit(".", 1)[-1]
    return tail in _AI_MODULE_TAILS


_MAX_LINES = 800
_lines: deque[str] = deque(maxlen=_MAX_LINES)
_lock = threading.Lock()


class AIActivityFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return _logger_matches_ai_panel(record.name)


class AIActivityRingHandler(logging.Handler):
    """Keeps recent formatted log lines for the Streamlit AI Logs page."""

    def __init__(self, level: int = logging.DEBUG) -> None:
        super().__init__(level)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
            with _lock:
                _lines.append(line)
        except Exception:
            self.handleError(record)


def get_ai_log_lines(limit: int = 400) -> list[str]:
    with _lock:
        return list(_lines)[-limit:]


def clear_ai_log_buffer() -> None:
    with _lock:
        _lines.clear()
