# PyInstaller spec — run: pyinstaller code_screenshots.spec
# Build on macOS for Mac friends, on Windows for Windows friends.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
root = Path(SPECPATH)

datas = [
    (str(root / "templates"), "templates"),
    (str(root / "static"), "static"),
]
binaries = []
hiddenimports = [
    "app",
    "app_paths",
    "code_screenshot",
    "hermit_smart",
    "docx",
    "PIL",
    "PIL._imaging",
    "flask",
    "werkzeug",
    "webview",
]

for package in ("pygments", "webview"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ["desktop_app.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CodeScreenshots",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CodeScreenshots",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="CodeScreenshots.app",
        icon=None,
        bundle_identifier="com.hermit.codescreenshots",
    )
