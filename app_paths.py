"""Paths for development vs PyInstaller desktop builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_SUPPORT_NAME = "HermitCodeScreenshots"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def resource_root() -> Path:
    """Read-only bundle root (templates, static) or project folder in dev."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def data_root() -> Path:
    """Writable folder for uploads, screenshots, and Word output."""
    if is_frozen():
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / APP_SUPPORT_NAME
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home())) / APP_SUPPORT_NAME
        else:
            base = Path.home() / ".local" / "share" / APP_SUPPORT_NAME
        base.mkdir(parents=True, exist_ok=True)
        return base
    return Path(__file__).resolve().parent
