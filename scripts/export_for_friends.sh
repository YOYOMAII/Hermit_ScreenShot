#!/usr/bin/env bash
# Build HermitScreenshot and create the only files you should send to friends.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
RELEASE="$ROOT/releases"
mkdir -p "$RELEASE"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -r requirements-desktop.txt
python scripts/generate_app_icons.py
python -m PyInstaller --noconfirm --clean code_screenshots.spec

rm -rf "$RELEASE/HermitScreenshot.app"
cp "$ROOT/GETTING-STARTED.md" "$RELEASE/GETTING-STARTED.md"
cd "$ROOT/dist"
cp "$ROOT/GETTING-STARTED.md" .
zip -r -y "$RELEASE/HermitScreenshot-Mac.zip" HermitScreenshot.app GETTING-STARTED.md
rm -f GETTING-STARTED.md

cd "$ROOT"
zip -r "$RELEASE/HermitScreenshot-Windows-build.zip" \
  GETTING-STARTED.md \
  app.py app_paths.py code_screenshot.py hermit_smart.py desktop_app.py \
  code_screenshots.spec requirements.txt requirements-desktop.txt \
  hermit-app-icon.jpg \
  templates static scripts packaging/icons \
  -x "*.DS_Store" "packaging/icons/*.iconset/*"

echo ""
echo "Send friends ONLY these files from: $RELEASE"
echo "  Mac users     → HermitScreenshot-Mac.zip"
echo "  Windows users → HermitScreenshot-Windows.zip (ready .exe — see below if missing)"
echo ""
echo "Windows .exe cannot be built on Mac. To create HermitScreenshot-Windows.zip:"
echo "  • On a Windows PC: unzip HermitScreenshot-Windows-build.zip, run scripts\\build_desktop.bat"
echo "  • Or push to GitHub and run Actions → Build Windows app → download artifact"
echo ""
ls -lh "$RELEASE"/*.zip 2>/dev/null || true
