from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from services.ai_log_buffer import AIActivityFilter, AIActivityRingHandler

_CONFIGURED = False


def setup_logging() -> None:
    """
    Configure root logging: human-readable lines to stderr and a rotating file.

    Safe to call multiple times (e.g. Streamlit reruns): handlers are added once per process.

    Environment:
      LOG_LEVEL — DEBUG, INFO, WARNING, ERROR (default INFO)
      LOG_DIR   — directory for log files (default: <CACHE_DIR>/logs)
      LOG_FILE  — full path to main log file (default: <LOG_DIR>/app.log)
      CACHE_DIR — used only to default LOG_DIR when LOG_DIR/LOG_FILE unset
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    cache_dir = Path(os.getenv("CACHE_DIR", "./cache")).resolve()
    log_dir = Path(os.getenv("LOG_DIR", str(cache_dir / "logs"))).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(os.getenv("LOG_FILE", str(log_dir / "app.log"))).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=int(os.getenv("LOG_FILE_MAX_BYTES", str(5 * 1024 * 1024))),
        backupCount=int(os.getenv("LOG_FILE_BACKUP_COUNT", "5")),
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    ai_ring = AIActivityRingHandler(level=level)
    ai_ring.addFilter(AIActivityFilter())
    ai_ring.setFormatter(fmt)
    root.addHandler(ai_ring)

    _quiet_noisy_loggers()

    log = logging.getLogger(__name__)
    log.info("Logging initialized: level=%s, file=%s", level_name, log_path)

    _CONFIGURED = True


def _quiet_noisy_loggers() -> None:
    for name in (
        "httpx",
        "httpcore",
        "urllib3",
        "google.auth",
        "google.api_core",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)
