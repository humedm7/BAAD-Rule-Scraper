@echo off
setlocal EnableExtensions

rem BAAQMD Current Rules downloader - no PowerShell required.
rem Keep DEST dedicated to these files because ROBOCOPY mirrors the folder.

set "DOWNLOAD_URL=https://github.com/humedm7/BAAQMD-Rule-Scraper/releases/download/baaqmd-current/BAAQMD_Current_Rules.zip"
set "DEST=U:\Department\Technical\EA\Air\EOL\BAAQMD Current Rules"
set "WORK=%TEMP%\BAAQMD-Rules-%RANDOM%-%RANDOM%"
set "ZIP=%WORK%\BAAQMD_Current_Rules.zip"
set "SOURCE=%WORK%\BAAQMD_Current_Rules"

echo.
echo Downloading the latest BAAQMD rules...
mkdir "%WORK%" >nul 2>&1

curl.exe -L --fail --retry 3 --retry-delay 3 ^
  --output "%ZIP%" ^
  "%DOWNLOAD_URL%"

if errorlevel 1 (
    echo.
    echo ERROR: GitHub download failed.
    echo Open this page in your browser and download the release manually:
    echo https://github.com/humedm7/BAAQMD-Rule-Scraper/releases/tag/baaqmd-current
    rmdir /s /q "%WORK%" >nul 2>&1
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

echo Extracting the downloaded collection...
tar.exe -xf "%ZIP%" -C "%WORK%"

if errorlevel 1 (
    echo.
    echo ERROR: Windows could not extract the downloaded ZIP.
    rmdir /s /q "%WORK%" >nul 2>&1
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

if not exist "%SOURCE%\Rules\" (
    echo.
    echo ERROR: The ZIP did not contain the expected BAAQMD_Current_Rules folder.
    rmdir /s /q "%WORK%" >nul 2>&1
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

if not exist "%DEST%\" mkdir "%DEST%"

echo Updating:
echo %DEST%
robocopy "%SOURCE%" "%DEST%" /MIR /R:2 /W:3 /NFL /NDL /NJH /NJS
set "COPY_RESULT=%ERRORLEVEL%"

rmdir /s /q "%WORK%" >nul 2>&1

if %COPY_RESULT% GEQ 8 (
    echo.
    echo ERROR: Windows could not update the destination folder.
    if /i not "%~1"=="/quiet" pause
    exit /b %COPY_RESULT%
)

echo.
echo Finished successfully.
echo The latest individual PDFs, CSV, and combined PDF are in:
echo %DEST%
if /i not "%~1"=="/quiet" pause
exit /b 0
