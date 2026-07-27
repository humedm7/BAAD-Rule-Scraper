@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0download_latest_rules.ps1"
if errorlevel 1 (
    echo.
    echo The download failed. Review the message above.
    pause
)
