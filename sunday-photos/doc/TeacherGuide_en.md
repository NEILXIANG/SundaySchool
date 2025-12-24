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
- The app creates the following folders next to the executable (same directory):
  - `input/` (where teachers put photos)
    - `input/student_photos/` (student reference photos)
    - `input/class_photos/` (classroom photos)
  - `output/` (organized results)
  - `logs/` (logs for troubleshooting)

If the app directory is not writable, it automatically falls back to Desktop (or Home) and prints the actual `Work folder` path.
The `Work folder:` line in the console output is the source of truth.

## Put photos in the right place
- Student references: `input/student_photos/`
  - Folder-only (single supported layout): `input/student_photos/<student_name>/...` (filenames can be anything)
  - Examples: `input/student_photos/Alice/ref_01.jpg`, `input/student_photos/Bob/img_0001.png`
- Classroom photos: `input/class_photos/`
  - Date subfolders recommended: `2025-12-21/photo.jpg`

## Run again
- Double-click once more to organize.
- When finished, the app opens `output/` automatically.

## Important note (to avoid surprises)
- The app may move photos from `class_photos/` into date folders like `YYYY-MM-DD/`. This is expected (it enables incremental processing).

## Need help?
- Send the newest log file from `logs/` (next to the executable; or under the fallback `Work folder`).

## FAQ

**Q: How do I force a full rerun if new photos seem unprocessed?**

Easiest: rename the date folder in `class_photos/` (e.g., `2025-12-21` → `2025-12-21-new`), then run again. The app will treat it as new input and fully process it.

Thorough (optional): delete `output/.state/` and any per-date caches (if present) under `output/`, then run again. Original photos are untouched; only recognition is redone.

---

Developer note: CLI flags like `--tolerance` are for source/dev workflows. Teachers should use the packaged `SundayPhotoOrganizer` same-folder (input/output/logs) workflow.
