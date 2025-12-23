# Developer & Packaging Guide

For developers and release maintainers: local dev, packaging, and CI workflows.

## Key structure
- Source: `sunday-photos/src/` (entry `src/cli/run.py`, core logic in `src/core/`).
- macOS packaging script: `sunday-photos/scripts/build_mac_app.sh` (console onefile, honors `TARGET_ARCH`).
- Release dir: `sunday-photos/release_console/` (executable `SundayPhotoOrganizer` + launcher + docs).
- Windows output: `sunday-photos/release_console/` (onefile `SundayPhotoOrganizer.exe` + `Launch_SundayPhotoOrganizer.bat`).

## Local dev & test
1) Python 3.14, create venv:
   ```bash
   cd sunday-photos
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2) Run/help:
   ```bash
   python src/cli/run.py --help
   python src/cli/run.py --input-dir input --output-dir output --tolerance 0.6
   ```
3) The app auto-creates `input/class_photos`, `input/student_photos`, `output`, `logs` if missing.

## Local packaging (macOS)
```bash
cd sunday-photos
bash scripts/build_mac_app.sh               # onefile for current arch
TARGET_ARCH=x86_64 bash scripts/build_mac_app.sh
TARGET_ARCH=arm64  bash scripts/build_mac_app.sh
```
Output: `release_console/SundayPhotoOrganizer` (onefile executable).

## Local packaging (Windows)
Run on Windows (PyInstaller cannot cross-compile):
```powershell
cd sunday-photos
powershell -ExecutionPolicy Bypass -File scripts\build_windows_console_app.ps1
```
Output: `release_console/SundayPhotoOrganizer.exe` (onefile executable).

Note: Older builds may have used an onedir layout like `release_console/SundayPhotoOrganizer/SundaySchool`. Current script outputs onefile.

## GitHub Actions
- macOS x86_64: `.github/workflows/macos-x86-build.yml` (runner macos-12, artifact `macos-x86_64`, path `sunday-photos/release_console/`).
- macOS arm64: `.github/workflows/macos-arm-build.yml` (runner macos-14, artifact `macos-arm64`, path same as above).
- Windows x86_64: `.github/workflows/windows-build.yml` (runner windows-latest, artifact `windows-x86_64`, path `sunday-photos/release_console/`).
- Trigger: `workflow_dispatch` (manual “Run workflow” in Actions UI).

## Config & params
- CLI flags (`src/cli/run.py`): `--input-dir`, `--output-dir`, `--tolerance` (default 0.6; lower is stricter).
- Constants: see `src/config.py` / `src/core/config.py`.

## Models & size
- `face_recognition_models` includes ~95MB model; GitHub may warn. Consider Git LFS or runtime download if size matters.
- onedir bundles Python and deps (larger but faster start); onefile is smaller but slower (Windows uses onefile).

## Troubleshooting
- `requirements.txt` missing: ensure working directory is `sunday-photos` (CI already sets this).
- dlib/numpy build errors on Windows: install VC Build Tools or use prebuilt wheels; ensure `cmake` is present (CI installs cmake).
- Instant exit: check photos under `input/class_photos`; inspect `logs/photo_organizer_*.log`.

## Release flow suggestion
1) Verify help/text locally: `python src/cli/run.py --help`.
2) Run Actions: macOS x86_64 / macOS arm64 / Windows build.
3) Download artifacts (`macos-x86_64`, `macos-arm64`, `windows-x86_64`), unzip, ship to users.
4) Ship alongside the Teacher Guide and note which chip each package targets.
