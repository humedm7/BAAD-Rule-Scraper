@echo off
setlocal EnableExtensions

rem This small launcher refreshes the real downloader from GitHub each run.
set "SCRIPT_DIR=%~dp0"
set "REMOTE_URL=https://raw.githubusercontent.com/humedm7/BAAD-Rule-Scraper/main/windows_downloader/download_latest_rules.cmd"
set "LOCAL_SCRIPT=%SCRIPT_DIR%download_latest_rules.cmd"
set "NEW_SCRIPT=%SCRIPT_DIR%download_latest_rules.new.cmd"
set "LOG_DIR=%SCRIPT_DIR%logs"
set "LOG_FILE=%LOG_DIR%\BAAD_Update.log"

if not exist "%LOG_DIR%\" mkdir "%LOG_DIR%" >nul 2>&1

if /i "%~1"=="/quiet" (
    call :run_update /quiet >> "%LOG_FILE%" 2>&1
) else (
    call :run_update
)
set "RESULT=%ERRORLEVEL%"

if "%RESULT%"=="0" (
    call :write_log "SUCCESS"
) else (
    call :write_log "FAILED with exit code %RESULT%"
    msg.exe %USERNAME% /time:120 "BAAD Current Rules update failed. See %LOG_FILE%." >nul 2>&1
)

exit /b %RESULT%

:run_update
call :write_log "Starting update"

curl.exe -L --fail --retry 2 --retry-delay 2 ^
  --output "%NEW_SCRIPT%" ^
  "%REMOTE_URL%"

if not errorlevel 1 (
    move /y "%NEW_SCRIPT%" "%LOCAL_SCRIPT%" >nul
    call :write_log "Downloaded the current GitHub downloader"
) else (
    del /q "%NEW_SCRIPT%" >nul 2>&1
    echo Could not check GitHub for a newer downloader. Using the local copy.
    call :write_log "Could not refresh from GitHub; using the local downloader"
)

if not exist "%LOCAL_SCRIPT%" (
    echo ERROR: No local downloader is available.
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

call "%LOCAL_SCRIPT%" %*
exit /b %ERRORLEVEL%

:write_log
>> "%LOG_FILE%" echo [%date% %time%] %~1
exit /b 0
