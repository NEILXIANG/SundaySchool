# Project Health Check Checklist

**Last updated**: 2025-12-27

Purpose: a runnable checklist for release-time / regression-time sanity checks.

Note: for the narrative “health check report”, see `doc/HealthCheckReport.md` / `doc/HealthCheckReport_en.md`.

---

## 1) Doc consistency (must)

- Entrypoint naming is consistent: `SundayPhotoOrganizer` (macOS app + console onedir + Windows onedir)
- Teacher input layout is single and consistent: `input/student_photos/<student_name>/*.jpg|png...`
  - Disallow images directly under `student_photos/`
  - Disallow deeper nested folders under each student folder
- The “auto move into date folders” explanation exists: photos under `class_photos/` root may be moved into `YYYY-MM-DD/`
- The “3-step accuracy fix” is consistent: only suggest better/more reference photos and clearer classroom photos; do not ask teachers to tune parameters

Suggested spot checks:
- `doc/TeacherQuickStart.md` / `doc/TeacherQuickStart_en.md`
- `doc/TeacherGuide.md` / `doc/TeacherGuide_en.md`
- `doc/CONFIG.md` / `doc/CONFIG_en.md`

---

## 2) Packaging artifacts & layout (must)

- onedir bundle exists: `release_console/SundayPhotoOrganizer/`
  - macOS binary: `release_console/SundayPhotoOrganizer/SundayPhotoOrganizer`
  - Windows binary: `release_console/SundayPhotoOrganizer/SundayPhotoOrganizer.exe`
- macOS teacher-friendly wrapper exists (if applicable): `release_mac_app/SundayPhotoOrganizer.app`
- Release bundle follows md-only for documentation files; runtime-generated `.txt` reports are not part of this rule

---

## 3) Work folder & permissions (must)

- Default Work folder: creates `input/ output/ logs/` next to the executable
- If not writable: falls back to Desktop/Home and prints `Work folder:` in console (source of truth)
- Env override works: `SUNDAY_PHOTOS_WORK_DIR` forces the Work folder root (portable/demo)

---

## 4) Cache & incremental (recommended)

- Incremental snapshot: `output/.state/class_photos_snapshot.json`
- Per-date recognition cache: `output/.state/recognition_cache_by_date/YYYY-MM-DD.json`
- Reference cache & snapshot live under `log_dir` (default `logs/`):
  - `{log_dir}/reference_encodings/<engine>/<model>/*.npy`
  - `{log_dir}/reference_index/<engine>/<model>.json`

---

## 5) Parallel & troubleshooting (recommended)

- Parallel policy: only parallelize when thresholds are met; on parallel failure it automatically falls back to serial
- Troubleshooting flags work:
  - Force serial: `SUNDAY_PHOTOS_NO_PARALLEL=1`
  - Diagnostics: `SUNDAY_PHOTOS_DIAG_ENV=1`

---

## 6) Acceptance commands (recommended)

- Dev mode: `pytest -q`
- Release strict mode (requires packaged artifacts): `REQUIRE_PACKAGED_ARTIFACTS=1 pytest -q`
