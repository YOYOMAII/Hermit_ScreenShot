"""Native save dialog for desktop (pywebview) — browser blob downloads do not work there."""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path


class DesktopBridge:
    def __init__(self, port: int) -> None:
        self._port = port

    def save_download(self, url_path: str, suggested_name: str = "download") -> dict:
        """Fetch a same-origin app URL and write it to a path the user picks."""
        import webview

        if not isinstance(url_path, str) or not url_path.startswith("/"):
            return {"ok": False, "error": "Invalid download path."}
        if not webview.windows:
            return {"ok": False, "error": "Desktop window is not ready."}

        name = (suggested_name or "download").strip() or "download"
        if name.lower().endswith(".docx"):
            file_types = ("Word document (*.docx)", "All files (*.*)")
        elif name.lower().endswith(".zip"):
            file_types = ("ZIP archive (*.zip)", "All files (*.*)")
        elif name.lower().endswith(".png"):
            file_types = ("PNG image (*.png)", "All files (*.*)")
        else:
            file_types = ("All files (*.*)",)

        chosen = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=name,
            file_types=file_types,
        )
        if not chosen:
            return {"ok": False, "cancelled": True}
        save_path = chosen[0] if isinstance(chosen, (tuple, list)) else chosen

        full_url = f"http://127.0.0.1:{self._port}{url_path}"
        try:
            with urllib.request.urlopen(full_url, timeout=120) as response:
                data = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"ok": False, "error": f"Could not read file from app: {exc}"}

        try:
            Path(save_path).write_bytes(data)
        except OSError as exc:
            return {"ok": False, "error": f"Could not write file: {exc}"}

        return {"ok": True, "path": str(save_path)}
