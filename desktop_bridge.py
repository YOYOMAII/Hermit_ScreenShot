"""Desktop (pywebview) file saving — browser downloads do not work inside the app window.

Files go straight into the user's Downloads folder. A native Save dialog is not used:
on macOS it never appears while the window is in full screen.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

_UNSAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def downloads_folder() -> Path:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            import uuid

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE * 8)]

            folder_id = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}")
            guid = GUID.from_buffer_copy(folder_id.bytes_le)
            path_ptr = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None,
                                                          ctypes.byref(path_ptr)) == 0:
                found = Path(path_ptr.value)
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
                if found.is_dir():
                    return found
        except Exception:
            pass
    folder = Path.home() / "Downloads"
    return folder if folder.is_dir() else Path.home()


def safe_file_name(name: str) -> str:
    cleaned = _UNSAFE_NAME.sub("_", Path(name or "").name).strip(" .")
    return cleaned or "download"


def unique_path(folder: Path, name: str) -> Path:
    candidate = folder / name
    stem, suffix = Path(name).stem, Path(name).suffix
    number = 1
    while candidate.exists():
        candidate = folder / f"{stem} ({number}){suffix}"
        number += 1
    return candidate


class DesktopBridge:
    def __init__(self, port: int, folder: Path | None = None) -> None:
        self._port = port
        self._folder = folder
        self._saved: set[str] = set()

    def save_download(self, url_path: str, suggested_name: str = "download") -> dict:
        """Fetch a same-origin app URL and save it as a new file in Downloads."""
        if not isinstance(url_path, str) or not url_path.startswith("/") or url_path.startswith("//"):
            return {"ok": False, "error": "Invalid download path."}

        full_url = f"http://127.0.0.1:{self._port}{url_path}"
        try:
            with urllib.request.urlopen(full_url, timeout=120) as response:
                data = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {"ok": False, "error": "This file has expired. Build the document again."}
            return {"ok": False, "error": f"Could not read file from app (HTTP {exc.code})."}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"ok": False, "error": f"Could not read file from app: {exc}"}
        if not data:
            return {"ok": False, "error": "The file was empty. Build the document again."}

        folder = self._folder or downloads_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = unique_path(folder, safe_file_name(suggested_name))
            fd, temp_name = tempfile.mkstemp(dir=folder, prefix=".hermit-", suffix=".part")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                os.replace(temp_name, target)
            except BaseException:
                Path(temp_name).unlink(missing_ok=True)
                raise
        except OSError as exc:
            return {"ok": False, "error": f"Could not save to {folder}: {exc}"}

        self._saved.add(str(target))
        return {
            "ok": True,
            "path": str(target),
            "name": target.name,
            "folder": folder.name or str(folder),
            "platform": sys.platform,
        }

    def open_file(self, path: str) -> dict:
        return self._launch(path, reveal=False)

    def show_in_folder(self, path: str) -> dict:
        return self._launch(path, reveal=True)

    def _launch(self, path: str, reveal: bool) -> dict:
        if path not in self._saved or not Path(path).is_file():
            return {"ok": False, "error": "That file is no longer there."}
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path] if reveal else ["open", path])
            elif sys.platform == "win32":
                if reveal:
                    subprocess.Popen(["explorer", f"/select,{path}"])
                else:
                    os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(Path(path).parent) if reveal else path])
        except OSError as exc:
            return {"ok": False, "error": f"Could not open: {exc}"}
        return {"ok": True}
