@echo off
setlocal

REM Sunday School Photo Organizer - Windows Launcher
REM Keeps the console window open so teachers can read messages.

chcp 65001 >nul

set "DIR=%~dp0"
cd /d "%DIR%"

REM Force work dir to the extracted folder root (so input/output/logs live next to this .bat)
set "SUNDAY_PHOTOS_WORK_DIR=%DIR%"

set "EXE=%DIR%SundayPhotoOrganizer\SundayPhotoOrganizer.exe"
if not exist "%EXE%" set "EXE=%DIR%SundayPhotoOrganizer.exe"
if not exist "%EXE%" set "EXE=%DIR%SundayPhotoOrganizer"

if not exist "%EXE%" (
    echo [ERROR] Cannot find SundayPhotoOrganizer executable in:
    echo   %DIR%
    echo.
    echo Expected file:
    echo   SundayPhotoOrganizer.exe
    echo.
    pause
    exit /b 1
)

"%EXE%"

REM If the program succeeded, open output folder for convenience.
if %errorlevel% EQU 0 (
    if exist "%DIR%output\" (
        start "" "%DIR%output"
    )
)

echo.
echo Press any key to exit...
pause >nul
