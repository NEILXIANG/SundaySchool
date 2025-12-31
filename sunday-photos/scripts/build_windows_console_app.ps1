# Windows packaging script (PowerShell)
# Builds a console onedir app via PyInstaller.
# Note: PyInstaller cannot cross-compile; run this on Windows.

$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

# Prefer workspace .venv (same as tests), else fall back to local venv, else python
$pythonCandidates = @(
  (Join-Path (Resolve-Path "..").Path ".venv\Scripts\python.exe"),
  (Join-Path (Resolve-Path "..").Path ".venv\bin\python"),
  (Join-Path (Get-Location).Path ".venv\Scripts\python.exe"),
  "python"
)

$PYTHON = $null
foreach ($p in $pythonCandidates) {
  if ($p -eq "python") { $PYTHON = $p; break }
  if (Test-Path $p) { $PYTHON = $p; break }
}

Write-Host "Using python: $PYTHON"

# Print python version for easier CI/local diagnostics.
& $PYTHON -V

# Ensure PyInstaller exists
& $PYTHON -m PyInstaller --version | Out-Null

# Preflight: ensure key binary deps are importable in this environment.
# This catches common CI/venv issues before PyInstaller runs.
& $PYTHON -c "import PIL; import cv2; print('Pillow:', PIL.__version__); print('OpenCV:', cv2.__version__)" 

$SPEC_FILE = "SundayPhotoOrganizer.spec"

# Use a project-local cache to avoid flaky global cache issues.
# Prefer PYINSTALLER_CONFIG_DIR (used by PyInstaller for config + cache).
$cacheDir = (Join-Path (Get-Location).Path "build\pyinstaller-cache")
$env:PYINSTALLER_CONFIG_DIR = $cacheDir
$env:PYINSTALLER_CACHEDIR = $cacheDir
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

# Bundle InsightFace model(s) into the packaged artifact for offline deployment.
# Default ON for Windows release packaging.
# Opt out:
#   $env:BUNDLE_INSIGHTFACE_MODELS = "0"
$bundle = $env:BUNDLE_INSIGHTFACE_MODELS
if ([string]::IsNullOrWhiteSpace($bundle)) { $bundle = "1" }

if ($bundle -eq "1") {
  $env:SUNDAY_PHOTOS_BUNDLE_INSIGHTFACE_MODELS = "1"

  $m = $env:SUNDAY_PHOTOS_INSIGHTFACE_MODEL
  if ([string]::IsNullOrWhiteSpace($m)) { $m = "buffalo_l" }
  $env:SUNDAY_PHOTOS_INSIGHTFACE_MODEL = $m

  if ([string]::IsNullOrWhiteSpace($env:SUNDAY_PHOTOS_INSIGHTFACE_HOME)) {
    # Default InsightFace home on Windows.
    $env:SUNDAY_PHOTOS_INSIGHTFACE_HOME = (Join-Path $env:USERPROFILE ".insightface")
  }

  $modelDir = Join-Path $env:SUNDAY_PHOTOS_INSIGHTFACE_HOME (Join-Path "models" $m)
  if (-not (Test-Path $modelDir)) {
    Write-Host "❌ InsightFace 模型目录不存在，无法进行离线模型打包：" -ForegroundColor Red
    Write-Host "- expected: $modelDir" -ForegroundColor Red
    Write-Host "解决方法：先在开发环境运行一次下载模型，或把模型拷贝到上述目录；" -ForegroundColor Yellow
    Write-Host "也可以临时关闭打包模型：set BUNDLE_INSIGHTFACE_MODELS=0" -ForegroundColor Yellow
    exit 1
  }

  Write-Host "Bundling InsightFace model for offline use: $m" -ForegroundColor Cyan
  Write-Host "- home: $($env:SUNDAY_PHOTOS_INSIGHTFACE_HOME)" -ForegroundColor Cyan
}

& $PYTHON -m PyInstaller --clean --noconfirm $SPEC_FILE

$RELEASE_DIR = "release_console"
$APP_NAME = "SundayPhotoOrganizer"

# Ensure the release work dirs are clean (do not ship local photos/logs).
$inputDir = Join-Path $RELEASE_DIR "input"
$outputDir = Join-Path $RELEASE_DIR "output"
$logsDir = Join-Path $RELEASE_DIR "logs"
foreach ($p in @($inputDir, $outputDir, $logsDir)) {
  if (Test-Path $p) {
    Remove-Item -Recurse -Force $p
  }
}

New-Item -ItemType Directory -Force -Path $RELEASE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "input\class_photos") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "input\student_photos") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "output") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "logs") | Out-Null

# Generate Windows launcher into release_console (so the release folder is self-contained).
$launcherBat = Join-Path $RELEASE_DIR "Launch_SundayPhotoOrganizer.bat"
@"
@echo off
setlocal

REM Sunday School Photo Organizer - Windows Launcher
REM Keeps the console window open so teachers can read messages.

chcp 65001 >nul

set "DIR=%~dp0"
cd /d "%DIR%"

REM Force work dir to the extracted folder root (so input/output/logs live next to this .bat)
set "SUNDAY_PHOTOS_WORK_DIR=%DIR%"

REM Teacher mode: suppress internal core logs in console (still writes to logs/)
set "SUNDAY_PHOTOS_TEACHER_MODE=1"

REM Default: disable console animations (spinner/pulse). Some consoles render \r poorly and will spam lines.
set "SUNDAY_PHOTOS_NO_ANIMATION=1"

REM Teacher-friendly pacing: tiny pause after critical messages (ms). Allow override.
if "%SUNDAY_PHOTOS_UI_PAUSE_MS%"=="" set "SUNDAY_PHOTOS_UI_PAUSE_MS=200"

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
"@ | Set-Content -Encoding ASCII $launcherBat

# Remove stale config.json (may contain dev absolute paths). The packaged launcher will generate a correct one.
$staleConfig = Join-Path $RELEASE_DIR "config.json"
if (Test-Path $staleConfig) {
  Remove-Item -Force $staleConfig
}

# Placeholders to guide teachers
@"
请把“学生参考照”放到这个文件夹里（用于识别每位学生）。

建议：每位学生 1~5 张，清晰正脸、光线充足、不要过度美颜。
示例文件名：张三_1.jpg、张三_2.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\student_photos\把学生参考照放这里.md")

@"
请把“课堂/活动照片（需要整理的照片）”放到这个文件夹里。

示例文件名：2025-12-25_活动_001.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\class_photos\把课堂照片放这里.md")

@"
Put student reference photos here (used to recognize each student).

Tip: 1–5 photos per student; clear frontal face works best.
Example: Alice_1.jpg, Alice_2.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\student_photos\PUT_STUDENT_PHOTOS_HERE.md")

@"
Put class/event photos to be organized here.

Example: 2025-12-25_Event_001.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\class_photos\PUT_CLASS_PHOTOS_HERE.md")

# Remove legacy .txt placeholders (always keep only .md).
$legacyPlaceholders = @(
  (Join-Path $RELEASE_DIR "input\student_photos\把学生参考照放这里.txt"),
  (Join-Path $RELEASE_DIR "input\class_photos\把课堂照片放这里.txt"),
  (Join-Path $RELEASE_DIR "input\student_photos\PUT_STUDENT_PHOTOS_HERE.txt"),
  (Join-Path $RELEASE_DIR "input\class_photos\PUT_CLASS_PHOTOS_HERE.txt")
)
foreach ($p in $legacyPlaceholders) {
  if (Test-Path $p) { Remove-Item -Force $p }
}

$srcDir = Join-Path "dist" $APP_NAME
if (-not (Test-Path $srcDir)) {
  throw "Build succeeded but onedir output not found under dist/$APP_NAME/."
}

$dstDir = Join-Path $RELEASE_DIR $APP_NAME
if (Test-Path $dstDir) {
  Remove-Item -Recurse -Force $dstDir
}
Copy-Item -Recurse -Force $srcDir $dstDir

$dstExe = Join-Path $dstDir ("$APP_NAME.exe")
if (-not (Test-Path $dstExe)) {
  # Fallback if produced without .exe (uncommon on Windows, but keep it safe)
  $dstExe = Join-Path $dstDir $APP_NAME
}
if (-not (Test-Path $dstExe)) {
  throw "Release copied, but executable not found under $dstDir."
}

# Copy teacher quick start docs into release_console (refresh on each build)
$docRoot = Join-Path (Get-Location).Path "doc"
if (Test-Path $docRoot) {
  $pairs = @(
    @{ Src = (Join-Path $docRoot "TeacherQuickStart.md");     Dst = (Join-Path $RELEASE_DIR "老师快速开始.md") },
    @{ Src = (Join-Path $docRoot "TeacherQuickStart_en.md");  Dst = (Join-Path $RELEASE_DIR "QuickStart_EN.md") },
  )
  foreach ($p in $pairs) {
    if (Test-Path $p.Src) {
      Copy-Item -Force $p.Src $p.Dst
    }
  }

    # Teacher docs: always keep only .md (remove any .txt if present).
    $txtDocs = @(
      (Join-Path $RELEASE_DIR "老师快速开始.txt"),
      (Join-Path $RELEASE_DIR "QuickStart_EN.txt")
    )
    foreach ($t in $txtDocs) {
      if (Test-Path $t) { Remove-Item -Force $t }
    }
}

Write-Host "Release prepared: $RELEASE_DIR"
Write-Host "- Executable: $dstExe"
Write-Host "- Windows launcher: $RELEASE_DIR\Launch_SundayPhotoOrganizer.bat"
