@echo off
setlocal EnableExtensions

rem This small launcher refreshes the real downloader from GitHub each run.
set "SCRIPT_DIR=%~dp0"
set "REMOTE_URL=https://raw.githubusercontent.com/humedm7/BAAQMD-Rule-Scraper/main/windows_downloader/download_latest_rules.cmd"
set "LOCAL_SCRIPT=%SCRIPT_DIR%download_latest_rules.cmd"
set "NEW_SCRIPT=%SCRIPT_DIR%download_latest_rules.new.cmd"

curl.exe -L --fail --retry 2 --retry-delay 2 ^
  --output "%NEW_SCRIPT%" ^
  "%REMOTE_URL%"

if not errorlevel 1 (
    move /y "%NEW_SCRIPT%" "%LOCAL_SCRIPT%" >nul
) else (
    del /q "%NEW_SCRIPT%" >nul 2>&1
    echo Could not check GitHub for a newer downloader. Using the local copy.
)

if not exist "%LOCAL_SCRIPT%" (
    echo ERROR: No local downloader is available.
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

call "%LOCAL_SCRIPT%" %*
exit /b %ERRORLEVEL%
