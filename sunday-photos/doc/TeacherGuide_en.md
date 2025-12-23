# Teacher Quickstart Guide (Packaged App / No Python needed)

Audience: teachers using the packaged app by double-clicking; no Python install required.

Goal: minimal steps, minimal confusion.

## Run (macOS)
- Double-click `release_console/启动工具.sh` (recommended).
- Or double-click `release_console/SundayPhotoOrganizer`.

If macOS blocks the first run: System Settings → Privacy & Security → Open Anyway.

## Run (Windows)
- Double-click `release_console/Launch_SundayPhotoOrganizer.bat` (recommended; keeps the window open).
- Or double-click `release_console/SundayPhotoOrganizer.exe`.

## What happens on first run
- The app creates this folder on your Desktop:
  - `Desktop/SundaySchoolPhotoOrganizer/`
- It also creates:
  - `student_photos/` (student reference photos)
  - `class_photos/` (classroom photos)
  - `output/` (organized results)
  - `logs/` (logs for troubleshooting)

## Put photos in the right place
- Student references: `Desktop/SundaySchoolPhotoOrganizer/student_photos/`
  - Folder-only (single supported layout): `student_photos/<student_name>/...` (filenames can be anything)
  - Examples: `student_photos/Alice/ref_01.jpg`, `student_photos/Bob/img_0001.png`
- Classroom photos: `Desktop/SundaySchoolPhotoOrganizer/class_photos/`
  - Date subfolders recommended: `2025-12-21/photo.jpg`

## Run again
- Double-click once more to organize.
- When finished, the app opens `output/` automatically.

## Important note (to avoid surprises)
- The app may move photos from `class_photos/` into date folders like `YYYY-MM-DD/`. This is expected (it enables incremental processing).

## Need help?
- Send the newest log file from `Desktop/SundaySchoolPhotoOrganizer/logs/`.

---

Developer note: CLI flags like `--tolerance` are for source/dev workflows. Teachers should use the packaged `SundayPhotoOrganizer` Desktop-folder workflow.
