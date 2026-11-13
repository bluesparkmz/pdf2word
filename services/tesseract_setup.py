"""Locate Tesseract and configure pytesseract."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytesseract

_RESOLVED_CMD: str | None = None

_WINDOWS_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)

_LINUX_CANDIDATES = (
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
)


def configure_tesseract(explicit_cmd: str | None = None) -> str | None:
    """Set pytesseract command; return resolved path or None."""
    global _RESOLVED_CMD

    if explicit_cmd:
        path = Path(explicit_cmd)
        if path.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(path)
            _RESOLVED_CMD = str(path)
            return _RESOLVED_CMD

    on_path = shutil.which("tesseract")
    if on_path:
        pytesseract.pytesseract.tesseract_cmd = on_path
        _RESOLVED_CMD = on_path
        return _RESOLVED_CMD

    candidates = _WINDOWS_CANDIDATES if sys.platform == "win32" else _LINUX_CANDIDATES
    for item in candidates:
        path = Path(item)
        if path.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(path)
            _RESOLVED_CMD = str(path)
            return _RESOLVED_CMD

    _RESOLVED_CMD = None
    return None


def tesseract_cmd_resolved() -> str | None:
    if _RESOLVED_CMD:
        return _RESOLVED_CMD
    cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
    if cmd and Path(cmd).exists():
        return str(cmd)
    return shutil.which("tesseract")


def tesseract_available() -> bool:
    path = tesseract_cmd_resolved()
    return bool(path and Path(path).exists())


def poppler_path() -> str | None:
    from config import settings

    if settings.poppler_path:
        p = Path(settings.poppler_path)
        if p.is_dir():
            return str(p)
    env = os.environ.get("POPPLER_PATH", "").strip()
    if env and Path(env).is_dir():
        return env
    if sys.platform == "win32":
        for item in (
            r"C:\Program Files\poppler\Library\bin",
            r"C:\poppler\Library\bin",
            r"C:\Program Files\poppler-24.08.0\Library\bin",
        ):
            if Path(item).is_dir():
                return item
    return None
