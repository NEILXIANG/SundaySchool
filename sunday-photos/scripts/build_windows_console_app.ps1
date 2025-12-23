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

Write-Host "Release prepared: $RELEASE_DIR"
Write-Host "- Executable: $dstExe"
Write-Host "- Windows launcher: $RELEASE_DIR\Launch_SundayPhotoOrganizer.bat"
