"""Copy vendor LaTeX files next to generated `.tex` so `pdflatex` works without extra TEXINPUTS."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LATEX_VENDOR_DIR = PROJECT_ROOT / "latex"

# Reference sources + class + images used by template.tex / twentysecondcv (not generated resumes).
_VENDOR_FILES = (
    "twentysecondcv.cls",
    "template.tex",
)


def copy_vendor_latex_assets_to(dest_dir: Path) -> list[Path]:
    """Copy allowlisted files from ``latex/`` into ``dest_dir`` (e.g. ``cache/outputs``)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for name in _VENDOR_FILES:
        src = LATEX_VENDOR_DIR / name
        if not src.is_file():
            logger.debug("LaTeX vendor asset missing, skip: %s", src)
            continue
        dst = dest_dir / name
        shutil.copy2(src, dst)
        copied.append(dst)
    if copied:
        logger.info("Copied %s LaTeX vendor file(s) to %s", len(copied), dest_dir)
    return copied
