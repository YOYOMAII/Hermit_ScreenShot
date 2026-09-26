@echo off
setlocal
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements-desktop.txt
python scripts\generate_app_icons.py
python -m PyInstaller --noconfirm --clean code_screenshots.spec

if not exist releases mkdir releases
copy /Y GETTING-STARTED.md dist\HermitScreenshot\ >nul
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; if (Test-Path 'releases\HermitScreenshot-Windows.zip') { Remove-Item 'releases\HermitScreenshot-Windows.zip' -Force }; Compress-Archive -Path 'dist\HermitScreenshot','GETTING-STARTED.md' -DestinationPath 'releases\HermitScreenshot-Windows.zip' -Force"

echo.
echo Done. Send Windows friends this zip (easy — no Python needed):
echo   releases\HermitScreenshot-Windows.zip
echo   Unzip, then run HermitScreenshot\HermitScreenshot.exe
echo.
echo Or run locally without zipping:
echo   dist\HermitScreenshot\HermitScreenshot.exe
echo   (keep the whole HermitScreenshot folder together)
pause
