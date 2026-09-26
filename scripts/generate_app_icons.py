#!/usr/bin/env python3
"""Build macOS .icns and Windows .ico from static/hermit-icon.jpg."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "static" / "hermit-icon.jpg"
OUT = ROOT / "packaging" / "icons"
ICONSET = OUT / "HermitScreenshot.iconset"
ICNS = OUT / "HermitScreenshot.icns"
ICO = OUT / "HermitScreenshot.ico"

ICONSET_SIZES = (16, 32, 128, 256, 512)


def write_iconset(source: Image.Image) -> None:
    if ICONSET.is_dir():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir(parents=True)
    for size in ICONSET_SIZES:
        for scale, suffix in ((1, ""), (2, "@2x")):
            edge = size * scale
            resized = source.resize((edge, edge), Image.Resampling.LANCZOS)
            resized.save(ICONSET / f"icon_{size}x{size}{suffix}.png", format="PNG")


def write_icns() -> None:
    write_iconset(Image.open(SOURCE).convert("RGBA"))
    if sys.platform == "darwin":
        subprocess.run(
            ["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)],
            check=True,
        )
    else:
        print("Skipping .icns (iconutil is macOS-only). Build .icns on a Mac before shipping.")


def write_ico() -> None:
    source = Image.open(SOURCE).convert("RGBA")
    ICO.parent.mkdir(parents=True, exist_ok=True)
    source.save(
        ICO,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source icon: {SOURCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    write_ico()
    write_icns()
    if ICONSET.is_dir():
        shutil.rmtree(ICONSET)
    print(f"Wrote {ICO}")
    if ICNS.is_file():
        print(f"Wrote {ICNS}")


if __name__ == "__main__":
    main()
