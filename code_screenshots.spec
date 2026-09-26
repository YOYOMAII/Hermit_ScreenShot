# PyInstaller spec — run: pyinstaller code_screenshots.spec
# Build on macOS for Mac friends, on Windows for Windows friends.
#
# Do not use collect_all(pygments|webview): it copies hundreds of .py files into
# _internal, which looks like shipping source code to end users.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
root = Path(SPECPATH)
icon_dir = root / "packaging" / "icons"
if sys.platform == "darwin":
    app_icon = icon_dir / "HermitScreenshot.icns"
elif sys.platform == "win32":
    app_icon = icon_dir / "HermitScreenshot.ico"
else:
    app_icon = icon_dir / "HermitScreenshot.ico"

datas = [
    (str(root / "templates"), "templates"),
    (str(root / "static"), "static"),
]
# pywebview JS assets only (no loose .py trees).
datas += collect_data_files("webview", include_py_files=False)

binaries = []
hiddenimports = [
    "app",
    "app_paths",
    "desktop_bridge",
    "code_screenshot",
    "hermit_smart",
    "docx",
    "PIL",
    "PIL._imaging",
    "flask",
    "werkzeug",
    "webview",
    "pygments",
    "pygments.lexers",
    "pygments.lexers.html",
    "pygments.lexers.css",
    "pygments.formatters",
    "pygments.styles",
]

if sys.platform == "darwin":
    hiddenimports.append("webview.platforms.cocoa")
elif sys.platform == "win32":
    hiddenimports += [
        "webview.platforms.edgechromium",
        "webview.platforms.mshtml",
        "clr_loader",
        "pythonnet",
    ]

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

icon_arg = str(app_icon) if app_icon.is_file() else None

if sys.platform == "win32":
    # Single .exe for friends — no _internal folder full of library .py files.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="HermitScreenshot",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_arg,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="HermitScreenshot",
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
        icon=icon_arg,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="HermitScreenshot",
    )

    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name="HermitScreenshot.app",
            icon=icon_arg,
            bundle_identifier="com.hermit.hermitscreenshot",
        )
