# Teacher Quickstart Guide

Audience: teachers using the packaged app; no Python install required.

## Get the package & folders
- Download the archive for your chip from GitHub Actions: macos-x86_64 (Intel), macos-arm64 (Apple Silicon), windows-x86_64 (Windows).
- Unzip, then go to `release_console/SundayPhotoOrganizer/` (Windows uses the `dist/` directory for the EXE).
- Pre-created folders:
  - `input/student_photos/` student reference photos
  - `input/class_photos/` classroom photos (date subfolders allowed)
  - `output/` organized results
  - `logs/` logs

## Prepare photos
- Student references: `Name.jpg` or `Name_index.jpg`, clear frontal faces (e.g., ZhangSan.jpg, ZhangSan_1.jpg).
- Classroom photos: place in `input/class_photos/`, optional date subfolders like `input/class_photos/2024-12-21/photo.jpg`.

## Run (macOS)
- Double-click `release_console/启动工具.sh` (if blocked, right-click Open, or run `chmod +x release_console/启动工具.sh` in terminal first).
- Or in terminal: `cd release_console/SundayPhotoOrganizer && ./SundaySchool` with optional flags:
  - `--tolerance 0.6` (default 0.6; lower is stricter, try 0.4–0.8)
  - `--input-dir input` / `--output-dir output` to override paths
- Windows: unzip, then double-click `SundaySchool.exe` inside `dist/` (if warning, choose “Run anyway” / allow).

## View results
- After processing, organized photos are in `output/` by student; unrecognized photos are also collected there.
- Logs live in `logs/` for troubleshooting.

## Common issues
- Finishes instantly with no output: ensure jpg/png photos exist under `class_photos`.
- Low accuracy: add more clear frontal references per student, or lower `--tolerance` to 0.5/0.45.
- Permission issues: add execute permission to the binary or script (`chmod +x SundaySchool` or `chmod +x 启动工具.sh`).

## Quick example
1) Place student photos in `input/student_photos/` (ZhangSan.jpg, LiSi.jpg).
2) Put classroom photos into `input/class_photos/2025-12-21/`.
3) Run `./SundaySchool --tolerance 0.55`.
4) Check `output/2025-12-21/` for organized photos by student.
