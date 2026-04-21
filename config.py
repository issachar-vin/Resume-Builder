from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    gemini_api_key: str
    cache_dir: Path
    output_dir: Path
    gemini_model: str = "gemini-2.0-flash"
    claude_model: str = "claude-sonnet-4-6"


def get_settings() -> Settings:
    cache_dir = Path(os.getenv("CACHE_DIR", "./cache")).resolve()
    output_dir = Path(os.getenv("OUTPUT_DIR", str(cache_dir / "outputs"))).resolve()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6").strip()

    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        cache_dir=cache_dir,
        output_dir=output_dir,
        gemini_model=gemini_model,
        claude_model=claude_model,
    )


def ensure_directories(settings: Settings) -> None:
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / "jobs").mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / "tailored").mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / "tailored" / "archive").mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / "logs").mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
