# Teacher Quickstart Guide (Packaged App / No Python needed)

Audience: teachers using the packaged app by double-clicking; no Python install required.

Goal: minimal steps, minimal confusion.

## Run (macOS)
- Double-click `release_console/启动工具.sh` (recommended).
- Or double-click `release_console/SundayPhotoOrganizer`.

If macOS blocks the first run: System Settings → Privacy & Security → Open Anyway.

## What happens on first run
- The app creates this folder on your Desktop:
  - `Desktop/主日学照片整理/`
- It also creates:
  - `student_photos/` (student reference photos)
  - `class_photos/` (classroom photos)
  - `output/` (organized results)
  - `logs/` (logs for troubleshooting)

## Put photos in the right place
- Student references: `Desktop/主日学照片整理/student_photos/`
  - File names: `Name.jpg` or `Name_2.jpg` (e.g., ZhangSan.jpg, ZhangSan_2.jpg)
- Classroom photos: `Desktop/主日学照片整理/class_photos/`
  - Date subfolders recommended: `2025-12-21/photo.jpg`

## Run again
- Double-click once more to organize.
- When finished, the app opens `output/` automatically.

## Important note (to avoid surprises)
- The app may move photos from `class_photos/` into date folders like `YYYY-MM-DD/`. This is expected (it enables incremental processing).

## Need help?
- Send the newest log file from `Desktop/主日学照片整理/logs/`.

---

Developer note: CLI flags like `--tolerance` are for source/dev workflows. Teachers should use the packaged `SundayPhotoOrganizer` Desktop-folder workflow.
