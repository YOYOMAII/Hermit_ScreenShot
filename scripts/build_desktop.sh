#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -r requirements-desktop.txt
python -m PyInstaller --noconfirm --clean code_screenshots.spec

echo ""
echo "Done. Share this folder with Mac users:"
echo "  dist/CodeScreenshots.app"
echo ""
echo "They may need: right-click the app → Open (first time only, unsigned build)."
