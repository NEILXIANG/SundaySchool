# Teacher Quick Start (macOS / Windows)

This guide is for teachers: no technical background required.

## What you need

- Student reference photos (to recognize each student)
- Class/event photos (the photos to organize)

## 3 steps (the only steps you need)

### Step 1: Unzip
1. Download the zip file you received
2. Unzip it to Desktop (recommended)

(Screenshot placeholder: a folder appears on Desktop after unzipping)

### Step 2: Put photos into input
Open the unzipped folder and locate:
- `input/student_photos/`: put **student reference photos** (one folder per student; 1–5 per student; clear frontal face works best)
- `input/class_photos/`: put **class/event photos** (all photos you want to organize)

Tip (to avoid surprises):
- Date subfolders are recommended (e.g. `input/class_photos/2025-12-25/...`).
- If you put photos directly under `class_photos/`, the app will auto-sort them into date folders. If there is a filename conflict, it auto-renames (e.g. `photo.jpg` → `photo_001.jpg`) to avoid overwriting.

Examples (your filenames can be different):
- `input/student_photos/Alice/Alice_1.jpg`
- `input/student_photos/Alice/Alice_2.jpg`
- `input/student_photos/Bob/Bob_1.jpg`
- `input/class_photos/2025-12-25_Christmas_Event_001.jpg`
- `input/class_photos/2025-12-25_Christmas_Event_002.jpg`

(Screenshot placeholder: input folder contains student_photos and class_photos)

### Step 3: Run (single entrypoint)
Inside the unzipped folder, run:

- macOS: double-click `SundayPhotoOrganizer.app` (recommended) or `启动工具.sh`
- Windows: double-click `Launch_SundayPhotoOrganizer.bat`

While running: a black window shows progress. **Do not close it**.

(Screenshot placeholder: console window showing progress)

## Where are the results?

- Results: `output/`
- Logs: `logs/`

In `output/`, you typically see:
- `output/<student>/YYYY-MM-DD/`: that student’s photos for that date
- `output/unknown_photos/`: not matched to known students (can also include no-face / error; the report separates counts)
- `output/*_整理报告.txt`: run report with statistics (timestamped filename)

More docs (usually not needed):
- Full teacher guide: `doc/TeacherGuide_en.md`
- Configuration & advanced options (SSOT): `doc/CONFIG_REFERENCE.md` (or the archived pointer `doc/CONFIG_en.md`)

(Screenshot placeholder: output folder contains organized results)

## Common issues

### 1) macOS says it "can’t be opened" / "developer cannot be verified"
This is a macOS security prompt.

Option A (recommended):
1. Click Cancel
2. Open System Settings → Privacy & Security
3. Find the blocked app message
4. Click “Open Anyway”
5. Go back and open it again

(Screenshot placeholder: Privacy & Security page with “Open Anyway”)

Option B:
1. Right click `SundayPhotoOrganizer.app` → Open
2. Confirm Open again

(Screenshot placeholder: right-click menu → Open)

### 2) Window closes immediately / nothing happens
1. Ensure photos are inside `input/student_photos/` and `input/class_photos/`
2. Ensure you are launching the entrypoint (macOS: `SundayPhotoOrganizer.app` or `启动工具.sh`; Windows: the `.bat`)
3. If still stuck: send the entire `logs/` folder to the maintainer

## If something goes wrong, send these two things

1. The whole `logs/` folder
2. A screenshot of the error (if any)

---

One-line summary:
- “Unzip → put photos into input → run → check output; if error, send logs.”
