@echo off
REM Builds Clash.exe (one file, no console window) in the "dist" folder.
REM It installs pygame-ce and PyInstaller first if they are missing.

cd /d "%~dp0"
py -3 -m pip install --quiet -r requirements.txt pyinstaller
py -3 -m PyInstaller --onefile --windowed --clean --name Clash clash.py
echo.
echo Done. The game is in dist\Clash.exe
pause
