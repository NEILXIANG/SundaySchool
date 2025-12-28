# Teacher Guide (Packaged App / No Python needed)

**Version**: v0.4.0  
**Last updated**: 2025-12-26

Audience: teachers who use the packaged app by double-clicking. No Python installation required.

Goal: minimal steps, minimal confusion.

Remember just one thing:
Put photos into the `input/` folder next to the app, then run it again.

If you want the shortest “just follow the steps” doc, use:
- `doc/TeacherQuickStart_en.md`

---

## 3 steps to finish

### Step 1: First run (auto-creates folders)

**macOS**:
- (Recommended) Double-click `SundayPhotoOrganizer.app`
- Or double-click `启动工具.sh`

**Windows**:
- Double-click `Launch_SundayPhotoOrganizer.bat` (recommended)
- Or double-click `SundayPhotoOrganizer.exe`

> macOS security prompt: System Settings → Privacy & Security → Open Anyway

What happens on first run:
- The program creates (next to the executable): `input/` (photos), `output/` (results), `logs/` (logs)
- If not writable, it falls back to Desktop (or Home) and prints `Work folder:` in the console (source of truth).

### Step 2: Put photos in the right place

**Student reference photos (must follow this layout)**:
- Put photos under: `input/student_photos/<student_name>/*.jpg|png...`
- One folder per student; filenames do not matter
- See `doc/TeacherQuickStart_en.md` for examples/screenshots

**Classroom photos**:
- Location: `input/class_photos/`
- Date subfolders are recommended: `2025-12-21/group_photo.jpg`
- You may also put photos directly under `class_photos/` (the app will organize them by date automatically)

### Step 3: Run again

- Double-click the same entrypoint again
- The app will recognize and organize photos
- When finished, it opens `output/` automatically

---

## Output structure

After finishing, `output/` typically looks like:

```
output/
├── Alice/
│   ├── 2025-12-21/
│   └── 2025-12-28/
├── Bob/
│   └── 2025-12-21/
├── unknown_photos/
│   ├── Unknown_Person_1/       # similar unknown faces grouped together
│   │   └── 2025-12-21/
│   └── 2025-12-21/             # single-appearance unknown faces
└── 20251221_143052_整理报告.txt
```

New in v0.4.0: Unknown-face clustering
- Similar unknown faces are grouped into `Unknown_Person_1`, `Unknown_Person_2`, ...
- This helps you spot recurring visitors/parents/new students

---

## Important notes (to avoid surprises)

### Will photos be moved?

Yes (this is expected):
- Photos directly under `class_photos/` may be moved into `YYYY-MM-DD/` folders.
- This enables incremental processing and makes browsing easier.

### Do I need to re-put photos every time?

No:
- The second run is usually faster.
- The app only processes new/changed dates (“incremental processing”).

---

## FAQ

### Q1: The program finishes immediately and there is no output

Most common reason: no photos under `student_photos/` or `class_photos/`.

Fix:
1. Check that each student has a folder under `student_photos/`
2. Check there are photos under `class_photos/`
3. Run again

### Q2: Recognition is inaccurate

Don’t tune parameters. Just do these 3 steps:

1) Add 2–3 clearer reference photos for that student (frontal, sharp, not blocked)
2) Don’t use group photos as reference photos
3) Use clearer classroom photos when possible (better lighting, larger faces)

### Q3: What is Unknown_Person_X?

It is the unknown-face clustering feature:
- `Unknown_Person_1` = the first cluster of similar unknown faces
- Useful for recurring visitors/parents, and for discovering new students

How to handle:
1) Check photos under `Unknown_Person_X`
2) If it’s a new student, pick 2–3 clear photos and put them into `student_photos/<student_name>/`, then run again

### Q4: How do I force a full rerun?

Easiest:
- Rename the date folder under `class_photos/` (e.g., `2025-12-21` → `2025-12-21-new`), then run again.

More thorough (optional):
- Delete `output/.state/` (incremental records) and any per-date caches, then run again.
- Original photos are not deleted; the app only re-runs recognition and regenerates results.

### Q5: The program errors out — what should I send for help?

Please send:
1) The newest log file under `logs/` (if the app fell back, use the `Work folder:` path printed in the console)
2) A short description + screenshot of the error (if any)
