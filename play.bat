@echo off
REM Starts Clash from the source code.
REM The first time it installs pygame-ce, the only thing Clash needs.

cd /d "%~dp0"
py -3 -m pip install --quiet -r requirements.txt
py -3 clash.py
if errorlevel 1 pause
