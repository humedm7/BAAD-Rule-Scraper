@echo off
setlocal EnableExtensions

rem BAAD Current Rules downloader - no PowerShell required.
rem Existing unrelated files in DEST are preserved.

set "DOWNLOAD_URL=https://github.com/humedm7/BAAD-Rule-Scraper/releases/download/baad-current/BAAD_Current_Rules.zip"
rem The rules folder is three levels above windows_downloader.
for %%I in ("%~dp0..\..\..") do set "DEST=%%~fI"
set "WORK=%TEMP%\BAAD-Rules-%RANDOM%-%RANDOM%"
set "ZIP=%WORK%\BAAD_Current_Rules.zip"
set "SOURCE=%WORK%\BAAD_Current_Rules"

echo.
echo Downloading the latest BAAD rules...
mkdir "%WORK%" >nul 2>&1

curl.exe -L --fail --retry 3 --retry-delay 3 ^
  --output "%ZIP%" ^
  "%DOWNLOAD_URL%"

if errorlevel 1 (
    echo.
    echo ERROR: GitHub download failed.
    echo Open this page in your browser and download the release manually:
    echo https://github.com/humedm7/BAAD-Rule-Scraper/releases/tag/baad-current
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

if not exist "%SOURCE%\Current Rules\" if exist "%SOURCE%\All Rules\" (
    move /y "%SOURCE%\All Rules" "%SOURCE%\Current Rules" >nul
)

if not exist "%SOURCE%\Current Rules\" (
    echo.
    echo ERROR: The ZIP did not contain the expected BAAD_Current_Rules folder.
    rmdir /s /q "%WORK%" >nul 2>&1
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

set "NEW_PDF_NAMING="
if exist "%SOURCE%\Current Rules\Reg-*.pdf" set "NEW_PDF_NAMING=1"
set "NEW_BAAD_OUTPUTS="
if exist "%SOURCE%\BAAD Current Rules Combined.pdf" if exist "%SOURCE%\BAAD Current Rules Index.xlsx" set "NEW_BAAD_OUTPUTS=1"

if not exist "%DEST%\" mkdir "%DEST%"

echo Updating:
echo %DEST%
robocopy "%SOURCE%" "%DEST%" /E /R:2 /W:3 /NFL /NDL /NJH /NJS
set "COPY_RESULT=%ERRORLEVEL%"

if %COPY_RESULT% GEQ 8 (
    rmdir /s /q "%WORK%" >nul 2>&1
    echo.
    echo ERROR: Windows could not update the destination folder.
    if /i not "%~1"=="/quiet" pause
    exit /b %COPY_RESULT%
)

rem Remove obsolete current-folder names only after the new Reg-* set was
rem successfully copied. Archive files and unrelated files are preserved.
if defined NEW_PDF_NAMING (
    del /q "%DEST%\Current Rules\RG????.pdf" >nul 2>&1
)

rem Remove obsolete top-level BAAQMD outputs only after both replacement BAAD
rem outputs were successfully copied.
if defined NEW_BAAD_OUTPUTS (
    del /q "%DEST%\BAAQMD Current Rules Combined.pdf" >nul 2>&1
    del /q "%DEST%\BAAQMD Current Rules Index.xlsx" >nul 2>&1
    del /q "%DEST%\BAAQMD_All_Current_Rules_Combined.pdf" >nul 2>&1
    del /q "%DEST%\BAAQMD_Current_Rules_Index.csv" >nul 2>&1
)

rmdir /s /q "%WORK%" >nul 2>&1

echo.
echo Finished successfully.
echo The latest individual PDFs, Excel index, and combined PDF are in:
echo %DEST%
if /i not "%~1"=="/quiet" pause
exit /b 0
