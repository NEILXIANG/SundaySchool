# Windows packaging script (PowerShell)
# Builds a console one-file executable via PyInstaller.
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

# Ensure PyInstaller exists
& $PYTHON -m PyInstaller --version | Out-Null

$SPEC_FILE = "SundayPhotoOrganizer.spec"

& $PYTHON -m PyInstaller --clean --noconfirm $SPEC_FILE

$RELEASE_DIR = "release_console"
$APP_NAME = "SundayPhotoOrganizer"

New-Item -ItemType Directory -Force -Path $RELEASE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "input\class_photos") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "input\student_photos") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "output") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RELEASE_DIR "logs") | Out-Null

# Placeholders to guide teachers
@"
请把“学生参考照”放到这个文件夹里（用于识别每位学生）。

建议：每位学生 1~5 张，清晰正脸、光线充足、不要过度美颜。
示例文件名：张三_1.jpg、张三_2.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\student_photos\把学生参考照放这里.txt")

@"
请把“课堂/活动照片（需要整理的照片）”放到这个文件夹里。

示例文件名：2025-12-25_活动_001.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\class_photos\把课堂照片放这里.txt")

@"
Put student reference photos here (used to recognize each student).

Tip: 1–5 photos per student; clear frontal face works best.
Example: Alice_1.jpg, Alice_2.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\student_photos\PUT_STUDENT_PHOTOS_HERE.txt")

@"
Put class/event photos to be organized here.

Example: 2025-12-25_Event_001.jpg
"@ | Set-Content -Encoding UTF8 (Join-Path $RELEASE_DIR "input\class_photos\PUT_CLASS_PHOTOS_HERE.txt")

$srcExe = Join-Path "dist" ("$APP_NAME.exe")
if (-not (Test-Path $srcExe)) {
  # Some environments may produce no .exe suffix; try fallback
  $srcExe = Join-Path "dist" $APP_NAME
}
if (-not (Test-Path $srcExe)) {
  throw "Build succeeded but executable not found under dist/."
}

$dstExe = Join-Path $RELEASE_DIR (Split-Path $srcExe -Leaf)
Copy-Item -Force $srcExe $dstExe

# Copy teacher quick start docs into release_console (refresh on each build)
$docRoot = Join-Path (Get-Location).Path "doc"
if (Test-Path $docRoot) {
  $pairs = @(
    @{ Src = (Join-Path $docRoot "TeacherQuickStart.md");     Dst = (Join-Path $RELEASE_DIR "老师快速开始.md") },
    @{ Src = (Join-Path $docRoot "TeacherQuickStart.txt");    Dst = (Join-Path $RELEASE_DIR "老师快速开始.txt") },
    @{ Src = (Join-Path $docRoot "TeacherQuickStart_en.md");  Dst = (Join-Path $RELEASE_DIR "QuickStart_EN.md") },
    @{ Src = (Join-Path $docRoot "TeacherQuickStart_en.txt"); Dst = (Join-Path $RELEASE_DIR "QuickStart_EN.txt") }
  )
  foreach ($p in $pairs) {
    if (Test-Path $p.Src) {
      Copy-Item -Force $p.Src $p.Dst
    }
  }
}

Write-Host "Release prepared: $RELEASE_DIR"
Write-Host "- Executable: $dstExe"
Write-Host "- Windows launcher: $RELEASE_DIR\Launch_SundayPhotoOrganizer.bat"
