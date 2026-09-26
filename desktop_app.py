#!/usr/bin/env python3
"""Desktop entry: local server + native window (or browser fallback)."""

from __future__ import annotations

import multiprocessing
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(port: int, seconds: float = 45.0) -> None:
    url = f"http://127.0.0.1:{port}/"
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.1)
    raise RuntimeError("The app server did not start. Try running from Terminal for errors.")


def run_desktop() -> None:
    port = pick_port()
    from app import app, start_background_tasks

    start_background_tasks()

    def serve() -> None:
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)

    threading.Thread(target=serve, daemon=True).start()
    wait_for_server(port)
    url = f"http://127.0.0.1:{port}/"

    try:
        import webview

        from desktop_bridge import DesktopBridge

        webview.settings["ALLOW_DOWNLOADS"] = True
        bridge = DesktopBridge(port)
        window = webview.create_window(
            "Hermit",
            url,
            width=1120,
            height=820,
            min_size=(800, 600),
            js_api=bridge,
        )
        webview.start()
    except Exception:
        print(f"Opening in your browser: {url}")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


def main() -> None:
    multiprocessing.freeze_support()
    run_desktop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc, file=sys.stderr)
        if sys.platform == "win32":
            input("Press Enter to close…")
        raise SystemExit(1) from exc
