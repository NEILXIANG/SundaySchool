# Developer & Packaging Guide

**Version**: v0.4.0  
**Last updated**: 2025-12-31

For developers and release maintainers: local dev, packaging, and CI workflows.

Release flow (sequence diagram + inputs/outputs):
- `doc/ReleaseFlow_en.md`
- `doc/ReleaseFlow.md`

Teacher-facing quick start (included in release bundles):
- `doc/TeacherQuickStart.md`
- `doc/TeacherQuickStart_en.md`

## Key structure
- Source: `sunday-photos/src/` (entry `src/cli/run.py`, core logic in `src/core/`).
- macOS packaging script: `sunday-photos/scripts/build_mac_app.sh` (console onedir, honors `TARGET_ARCH`).
- macOS teacher-friendly wrapper: `sunday-photos/scripts/build_mac_teacher_app.sh` (produces `release_mac_app/SundayPhotoOrganizer.app`).
- Release dir: `sunday-photos/release_console/` (onedir folder `SundayPhotoOrganizer/` + launchers + docs).

## Local dev & test
1) Python 3.7+ (recommended), create venv:
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
bash scripts/build_mac_app.sh               # onedir for current arch
TARGET_ARCH=x86_64 bash scripts/build_mac_app.sh
TARGET_ARCH=arm64  bash scripts/build_mac_app.sh
```
Output: `release_console/SundayPhotoOrganizer/` (onedir folder).

If you only changed docs/launchers and want to refresh `release_console/` without re-running PyInstaller:
```bash
SKIP_PYINSTALLER=1 bash scripts/build_mac_app.sh
```

## Local packaging (Windows)
Run on Windows (PyInstaller cannot cross-compile):
```powershell
cd sunday-photos
powershell -ExecutionPolicy Bypass -File scripts\build_windows_console_app.ps1
```
Output: `release_console/SundayPhotoOrganizer/` (onedir bundle).

Windows executable: `release_console/SundayPhotoOrganizer/SundayPhotoOrganizer.exe`.

Note: Current releases use an onedir layout; the launchers are the recommended entry points.

## GitHub Actions
- macOS universal bundle (arm64 + x86_64): `.github/workflows/macos-universal-bundle.yml` (manual trigger, artifact `macos-universal`).
   - Unzips to `release_console_universal/` exposing a single entrypoint `SundayPhotoOrganizer`.
      - Arch binaries are under `release_console_universal/bin/` (`SundayPhotoOrganizer-arm64`, `SundayPhotoOrganizer-x86_64`).
- Windows x86_64: `.github/workflows/windows-build.yml` (runner windows-latest, artifact `windows-x86_64`, path `sunday-photos/release_console/`).
- Trigger: `workflow_dispatch` (manual “Run workflow” in Actions UI).

## Config & params
- CLI flags (`src/cli/run.py`): `--input-dir`, `--output-dir`, `--tolerance` (default 0.6; lower is stricter).
- Constants: see `src/config.py` / `src/core/config.py`.

## Models & size
- Default backend is InsightFace. The first run may download models into `~/.insightface/` (or `SUNDAY_PHOTOS_INSIGHTFACE_HOME`). For offline deployments, pre-download and ship the model folder.
- onedir bundles Python and deps (larger but faster start). This project uses onedir for both macOS and Windows releases.

## Troubleshooting
- `requirements.txt` missing: ensure working directory is `sunday-photos` (CI already sets this).
- Optional dlib backend: if you choose `SUNDAY_PHOTOS_FACE_BACKEND=dlib`, you may hit dlib build errors on Windows. Install VC Build Tools or use prebuilt wheels; ensure `cmake` is present.
- Instant exit: check photos under `input/class_photos`; inspect `logs/photo_organizer_*.log`.

## Release flow suggestion
1) Verify help/text locally: `python src/cli/run.py --help`.
2) Run Actions: macOS universal bundle / Windows build.
3) Download artifacts (`macos-universal`, `windows-x86_64`), unzip, ship to users.
4) Ship alongside the Teacher Guide.

## Orchestration & Error Semantics

### Runtime flow (with fallbacks)
```
User → CLI/run.py
    → ServiceContainer.build()
    → SimplePhotoOrganizer.run()
       → initialize()
          → StudentManager.load_students()
          → FaceRecognizer.load_reference_encodings()
          → FileOrganizer.prepare_output()
       → scan_input_directory()
          → organize_input_by_date()   # failure → warn and continue other dates
          → load_snapshot()             # failure → use empty snapshot
          → compute_incremental_plan()
       → process_photos()
          → load_date_cache()           # corrupted → ignore cache
          → parallel_or_serial_recognize()
               parallel failure → auto fallback to serial
          → UnknownClustering.run()
          → save_date_cache_atomic()
       → organize_output()
          → FileOrganizer.move_and_copy()  # per-file failure → warn and skip
          → create_summary_report()
       → save_snapshot()
```

### Cross-module error semantics
- Recoverable (single image/date issues): log warning/error, skip that file/date, continue main flow.
- Non-recoverable (input missing, no write permission): raise to CLI; CLI prints teacher-friendly message.
- Parallel failure: auto downgrade to serial, no fatal error; log fallback reason.
- Cache/snapshot corruption: ignore and rebuild empty cache/snapshot; log warning.
- Logging: include location (module/function), affected path (if any), and next-step suggestion.
