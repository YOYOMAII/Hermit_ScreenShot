#!/usr/bin/env python3
"""Optional local upload UI for the code screenshot renderer."""

from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from docx.opc.exceptions import PackageNotFoundError
from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from werkzeug.exceptions import InternalServerError, RequestEntityTooLarge

from app_paths import data_root, is_frozen, resource_root
from code_screenshot import MAX_IMAGES, THEMES, main
from hermit_smart import DEFAULT_CAPTION, INSERT_MODES, Figure, build_document, inspect_document


RESOURCE_ROOT = resource_root()
DATA_ROOT = data_root()
OUTPUT_ROOT = DATA_ROOT / "code_screenshots"
SMART_ROOT = DATA_ROOT / "smart_documents"
UPLOAD_LIMIT_MB = 40
KEEP_RESULTS_HOURS = 1
app = Flask(
    __name__,
    template_folder=str(RESOURCE_ROOT / "templates"),
    static_folder=str(RESOURCE_ROOT / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = UPLOAD_LIMIT_MB * 1024 * 1024
BATCH_ID = re.compile(r"[0-9a-f]{12}")
UNSAFE_NAME_CHARACTERS = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|#%]')
WINDOWS_DEVICE_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"] + [f"{kind}{n}" for kind in ("COM", "LPT") for n in range(1, 10)])


def upload_name(filename: str) -> str:
    """Return a storable file name that keeps non-English letters and spaces."""
    name = UNSAFE_NAME_CHARACTERS.sub("_", Path(filename).name).strip(" .")
    if name.split(".")[0].upper() in WINDOWS_DEVICE_NAMES:
        name = f"_{name}"
    return name


def remove_old_results(now: float | None = None) -> None:
    """Delete web results older than the keep time, whether or not they were downloaded.

    Only batch folders named by this app are removed; command-line output that
    shares code_screenshots/ is left alone.
    """
    cutoff = (time.time() if now is None else now) - KEEP_RESULTS_HOURS * 3600
    for root in (OUTPUT_ROOT, SMART_ROOT):
        if not root.is_dir():
            continue
        for folder in root.iterdir():
            try:
                if (BATCH_ID.fullmatch(folder.name) and folder.is_dir()
                        and folder.stat().st_mtime < cutoff):
                    shutil.rmtree(folder, ignore_errors=True)
            except OSError:
                pass


def remove_old_results_forever(interval_seconds: int = 600) -> None:
    while True:
        remove_old_results()
        time.sleep(interval_seconds)


_background_started = False


def start_background_tasks() -> None:
    """Start cleanup thread once (CLI, dev server, or desktop app)."""
    global _background_started
    if _background_started:
        return
    _background_started = True
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    SMART_ROOT.mkdir(parents=True, exist_ok=True)
    remove_old_results()
    threading.Thread(target=remove_old_results_forever, daemon=True).start()


@app.get("/")
def index():
    return render_template("index.html", keep_hours=KEEP_RESULTS_HOURS)


@app.get("/smart")
def smart():
    return render_template("smart.html", default_caption=DEFAULT_CAPTION,
                           keep_hours=KEEP_RESULTS_HOURS)


def page_sort_key(path: Path):
    match = re.fullmatch(r"(.*?)(\d+)", path.stem)
    if match:
        return match.group(1).lower(), int(match.group(2))
    return path.stem.lower(), 0


def integer_option(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(request.form.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name.replace('_', ' ').capitalize()} must be a number.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name.replace('_', ' ').capitalize()} must be {minimum}–{maximum}.")
    return value


@app.post("/api/render")
def render_upload():
    uploads = [file for file in request.files.getlist("files") if file.filename]
    if not uploads:
        return jsonify(error="Choose at least one HTML or CSS file."), 400
    if len(uploads) > 20:
        return jsonify(error="Choose up to 20 files per batch."), 400
    try:
        lines = integer_option("lines", 20, 1, 100)
        font_size = integer_option("font_size", 24, 8, 48)
        width = integer_option("width", 1200, 200, 4000)
        active_line = integer_option("active_line", 0, 0, 1000000)
        theme = request.form.get("theme", "light")
        if theme not in THEMES:
            raise ValueError("Choose a valid theme.")
        name_style = request.form.get("name_style", "simple")
        if name_style not in ("simple", "padded"):
            raise ValueError("Choose a valid naming style.")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    remove_old_results()
    batch = uuid.uuid4().hex[:12]
    destination = OUTPUT_ROOT / batch
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with tempfile.TemporaryDirectory(prefix="code_shots_") as temp:
            paths = []
            used = set()
            for upload in uploads:
                filename = upload_name(upload.filename)
                if not filename or Path(filename).suffix.lower() not in (".html", ".css"):
                    raise ValueError("Only .html and .css files are supported.")
                original_stem = Path(filename).stem
                suffix = Path(filename).suffix.lower()
                safe_name = filename
                duplicate = 2
                while safe_name.lower() in used:
                    safe_name = f"{original_stem}_{duplicate}{suffix}"
                    duplicate += 1
                used.add(safe_name.lower())
                path = Path(temp) / safe_name
                upload.save(path)
                paths.append(path)

            arguments = [str(path) for path in paths] + [
                "--output", str(destination), "--lines", str(lines),
                "--font-size", str(font_size), "--width", str(width),
                "--theme", theme, "--name-style", name_style,
                "--active-line", str(active_line),
            ]
            main(arguments)

        images = sorted(destination.glob("*.png"), key=page_sort_key)
        archive = destination / "screenshots.zip"
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            for path in images:
                bundle.write(path, path.name)
        return jsonify(
            batch=batch,
            images=[{"name": path.name, "url": f"/api/files/{batch}/{quote(path.name)}"}
                    for path in images],
            zip_url=f"/api/files/{batch}/screenshots.zip",
            folder=str(destination),
        )
    except (OSError, ValueError) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        return jsonify(error=str(exc)), 400
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


@app.get("/api/files/<batch>/<name>")
def generated_file(batch: str, name: str):
    if not BATCH_ID.fullmatch(batch):
        abort(404)
    if not (name.endswith(".png") or name == "screenshots.zip"):
        abort(404)
    return send_from_directory(OUTPUT_ROOT / batch, name, as_attachment=name.endswith(".zip"))


def smart_source():
    """Return (path or upload stream, display name) for the Word document to edit."""
    doc_id = request.form.get("doc_id", "").strip()
    if doc_id:
        folder = SMART_ROOT / doc_id
        if not BATCH_ID.fullmatch(doc_id) or not (folder / "document.docx").is_file():
            raise ValueError("That document is no longer available. Upload the .docx again.")
        name_file = folder / "name.txt"
        name = name_file.read_text(encoding="utf-8") if name_file.is_file() else "document.docx"
        return folder / "document.docx", name
    upload = request.files.get("docx")
    if not upload or not upload.filename:
        raise ValueError("Choose a Word (.docx) document.")
    if Path(upload.filename).suffix.lower() != ".docx":
        raise ValueError("Only Word .docx documents are supported.")
    name = upload_name(upload.filename)
    if Path(name).suffix.lower() != ".docx":
        name = "document.docx"
    # Python 3.9's SpooledTemporaryFile lacks seekable(), which zipfile needs.
    return io.BytesIO(upload.read()), name


@app.post("/api/smart/inspect")
def smart_inspect():
    try:
        source, name = smart_source()
        info = inspect_document(source)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except (BadZipFile, KeyError, PackageNotFoundError):
        return jsonify(error="Could not read this Word document."), 400
    return jsonify(name=name, **info)


@app.post("/api/smart/build")
def smart_build():
    uploads = [file for file in request.files.getlist("files") if file.filename]
    try:
        if not uploads:
            raise ValueError("Choose at least one HTML or CSS file.")
        if len(uploads) > 20:
            raise ValueError("Choose up to 20 code files at a time.")
        source, name = smart_source()
        lines = integer_option("lines", 20, 1, 100)
        font_size = integer_option("font_size", 24, 8, 48)
        width = integer_option("width", 1200, 200, 4000)
        after_page = integer_option("after_page", 0, 0, 100000)
        start_figure = None
        if request.form.get("start_figure", "").strip():
            start_figure = integer_option("start_figure", 1, 1, 100000)
        theme = request.form.get("theme", "light")
        if theme not in THEMES:
            raise ValueError("Choose a valid theme.")
        insert_mode = request.form.get("insert_mode", "continue")
        if insert_mode not in INSERT_MODES:
            raise ValueError("Choose a valid insert position.")
        caption_template = request.form.get("caption_template", "").strip() or DEFAULT_CAPTION
        if len(caption_template) > 200:
            raise ValueError("Caption template must be 200 characters or fewer.")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    remove_old_results()
    doc_id = uuid.uuid4().hex[:12]
    destination = SMART_ROOT / doc_id
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with tempfile.TemporaryDirectory(prefix="hermit_smart_") as temp:
            figures = []
            for file_no, upload in enumerate(uploads, start=1):
                display = Path(upload.filename).name
                suffix = Path(display).suffix.lower()
                if suffix not in (".html", ".css"):
                    raise ValueError("Only .html and .css code files are supported.")
                work = Path(temp) / str(file_no)
                (work / "images").mkdir(parents=True)
                path = work / (upload_name(display) or f"file{suffix}")
                upload.save(path)
                main([str(path), "--output", str(work / "images"), "--lines", str(lines),
                      "--font-size", str(font_size), "--width", str(width), "--theme", theme,
                      "--fit-width"], max_images=MAX_IMAGES - len(figures))
                images = sorted((work / "images").glob("*.png"), key=page_sort_key)
                figures += [Figure(image, Path(display).stem, suffix, file_no, part)
                            for part, image in enumerate(images, start=1)]

            placed = build_document(source, figures, destination / "document.docx",
                                    insert_mode=insert_mode, after_page=after_page,
                                    start_figure=start_figure, caption_template=caption_template)
            for figure, item in zip(figures, placed):
                shutil.copyfile(figure.image, destination / f"fig{item['n']}.png")
                item["image_url"] = f"/api/smart/files/{doc_id}/fig{item['n']}.png"
        (destination / "name.txt").write_text(name, encoding="utf-8")
        info = inspect_document(destination / "document.docx")
        return jsonify(
            doc_id=doc_id,
            name=name,
            download_url=f"/api/smart/files/{doc_id}/document.docx",
            figures=placed,
            next_figure=info["next_figure"],
            total_figures=info["figures"],
            pages_estimate=info["pages_estimate"],
            folder=str(destination),
        )
    except (BadZipFile, KeyError, PackageNotFoundError):
        shutil.rmtree(destination, ignore_errors=True)
        return jsonify(error="Could not read this Word document."), 400
    except (OSError, ValueError) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        return jsonify(error=str(exc)), 400
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


@app.get("/api/smart/files/<doc_id>/<name>")
def smart_file(doc_id: str, name: str):
    if not BATCH_ID.fullmatch(doc_id):
        abort(404)
    folder = SMART_ROOT / doc_id
    if name == "document.docx":
        name_file = folder / "name.txt"
        download = name_file.read_text(encoding="utf-8") if name_file.is_file() else name
        return send_from_directory(folder, name, as_attachment=True, download_name=download)
    if not re.fullmatch(r"fig\d+\.png", name):
        abort(404)
    return send_from_directory(folder, name)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return jsonify(error=f"Upload is too large. The limit is {UPLOAD_LIMIT_MB} MB per upload."), 413


@app.errorhandler(InternalServerError)
def internal_error(_error):
    hint = "try a simpler file."
    if not is_frozen():
        hint = ("Check the terminal running app.py for details, or " + hint)
    return jsonify(error=f"Something went wrong while processing these files. {hint}"), 500


if __name__ == "__main__":
    # HERMIT_DEBUG=1 turns on auto-reload and the interactive debugger for development.
    debug = os.environ.get("HERMIT_DEBUG") == "1"
    port = int(os.environ.get("PORT", "5000"))
    # Reload templates/CSS on refresh even when HERMIT_DEBUG is off (no process reloader).
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    start_background_tasks()
    print(f"Open http://127.0.0.1:{port} in your browser")
    print(f"Generated files are deleted automatically after {KEEP_RESULTS_HOURS} hour(s).")
    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=debug)
