@echo off
setlocal

REM Sunday School Photo Organizer - Windows Launcher
REM This launcher keeps the console window open so teachers can read messages.

REM Best-effort: switch to UTF-8 (Windows 10/11 usually OK)
chcp 65001 >nul

set "DIR=%~dp0"
cd /d "%DIR%"

set "EXE=%DIR%SundayPhotoOrganizer.exe"
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
echo.
echo Press any key to exit...
pause >nul
