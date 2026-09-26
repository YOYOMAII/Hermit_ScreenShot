@echo off
setlocal
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements-desktop.txt
python -m PyInstaller --noconfirm --clean code_screenshots.spec

echo.
echo Done. Zip and share this folder with Windows users:
echo   dist\CodeScreenshots\
echo.
echo They run CodeScreenshots.exe inside that folder (keep the whole folder together).
pause
