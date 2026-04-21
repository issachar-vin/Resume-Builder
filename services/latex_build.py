"""Run ``pdflatex`` on a saved ``.tex`` file (optional; TeX installation required)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from services.latex_assets import LATEX_VENDOR_DIR

logger = logging.getLogger(__name__)

# Common macOS MacTeX location when not on PATH
_MAC_TEX_BIN = Path("/Library/TeX/texbin/pdflatex")


def find_pdflatex() -> str | None:
    w = shutil.which("pdflatex")
    if w:
        return w
    if _MAC_TEX_BIN.is_file():
        return str(_MAC_TEX_BIN)
    return None


def build_pdf(tex_path: Path, *, timeout_s: int = 120) -> Path | None:
    """
    Run ``pdflatex`` twice in ``tex_path``'s directory. Returns path to ``.pdf`` if produced.

    ``TEXINPUTS`` prepends the output directory (vendor files copied there) and repo ``latex/``.
    """
    pdflatex = find_pdflatex()
    if not pdflatex:
        logger.warning("pdflatex not found; install MacTeX/TeX Live or add texbin to PATH")
        return None

    tex_path = tex_path.resolve()
    if not tex_path.is_file():
        logger.error("TeX file missing: %s", tex_path)
        return None

    workdir = tex_path.parent
    base_name = tex_path.name
    sep = os.pathsep
    texinputs_prefix = f"{workdir}{sep}{LATEX_VENDOR_DIR.resolve()}{sep}"

    env = os.environ.copy()
    env["TEXINPUTS"] = texinputs_prefix + env.get("TEXINPUTS", "")
    env["PATH"] = str(Path(pdflatex).parent) + sep + env.get("PATH", "")

    cmd = [pdflatex, "-interaction=nonstopmode", base_name]
    last_stderr = ""
    for _ in range(2):
        try:
            proc = subprocess.run(
                cmd,
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            logger.exception("pdflatex timed out for %s", tex_path)
            return None
        last_stderr = (proc.stderr or "") + (proc.stdout or "")
        if proc.returncode != 0:
            logger.warning(
                "pdflatex returned %s for %s (last output tail): %s",
                proc.returncode,
                tex_path,
                last_stderr[-1500:],
            )

    pdf = tex_path.with_suffix(".pdf")
    if pdf.is_file():
        logger.info("PDF built: %s", pdf)
        return pdf.resolve()

    logger.warning("pdflatex ran but no PDF at %s", pdf)
    return None
