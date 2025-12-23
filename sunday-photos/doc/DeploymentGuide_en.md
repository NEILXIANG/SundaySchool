# 🎓 Sunday School Photo Organizer - Deployment Guide (Console Edition)

## 📦 Deliverables
Console/CLI distribution only, located under `release_console/`:
1. **SundayPhotoOrganizer** (macOS executable, already chmod +x)
2. **SundayPhotoOrganizer.exe** (Windows executable)
3. **启动工具.sh** (macOS launcher script; double-click or run via terminal)
4. **Launch_SundayPhotoOrganizer.bat** (Windows launcher; double-click)
3. **使用说明.txt** (Chinese user guide)
4. **USAGE_EN.txt** (English user guide)

Keep these files together when distributing to teachers.

## 📂 Directory Overview (source tree)
```
sunday-photos/
├── release_console/           # Packaged deliverables
├── input/                     # Source-mode input: student_photos/, class_photos/
├── output/                    # Source-mode output: student/date hierarchy
├── logs/                      # Source-mode logs
├── src/                       # Core, CLI entry, UI helpers, scripts
├── tests/                     # Automated tests (packaging + teacher-friendly)
├── doc/                       # Docs (structure, testing report, deployment, etc.)
├── run.py                     # Top-level entry script
├── run_all_tests.py           # Full test runner
└── requirements.txt           # Dependencies
```

Runtime folders created automatically (Desktop):
```
Desktop/SundaySchoolPhotoOrganizer/
├── student_photos/            # Reference photos (folder-only: student_photos/<student_name>/...)
├── class_photos/              # Classroom photos (e.g., 2024-12-21/group.jpg)
├── output/                    # Results (student/date/group_103045.jpg)
└── logs/                      # Runtime logs (safe to clear)
```

### 📥 Input examples (source mode)
```
input/
├── student_photos/
│   ├── Alice/
│   │   ├── ref_01.jpg
│   │   └── ref_02.png
│   └── Bob/
│       └── img_0001.jpg
└── class_photos/
    ├── 2024-12-21/
  │   ├── group_photo.jpg
    │   └── game_time.png
    └── 2024-12-28/
        └── discussion.jpg
```

### 📤 Output example (organized)
```
output/
├── Alice/
│   ├── 2024-12-21/
│   │   ├── group_photo_103045.jpg
│   │   └── game_time_104823.jpg
│   └── 2024-12-28/
│       └── discussion_101010.jpg
├── Bob/
│   └── 2024-12-21/
│       └── group_photo_103045.jpg
└── unknown_photos/
    └── 2024-12-21/
    └── blurry_105632.jpg
```

## 🚀 Teacher Workflow
- release_console/: packaged deliverables (exe + launcher + guides)
- Desktop/SundaySchoolPhotoOrganizer/ (auto-created on first run):
  - student_photos/: folder-only reference photos: `student_photos/<student_name>/...` (filenames can be anything)
  - class_photos/: classroom photos; date subfolders recommended (2024-12-21/photo.jpg)
  - output/: organized results (student → date)
  - logs/: run logs

### Input rules (source run scenario)
- Default input root: `input/`
- Reference photos: put in `input/student_photos/`
  - Folder-only: create one folder per student: `input/student_photos/<student_name>/`
  - Put that student's reference photos inside (filenames can be anything)
  - Up to 5 reference photos per student will be used (recommended 2–5 clear photos)
  - Examples: input/student_photos/Alice/ref_01.jpg, input/student_photos/Bob/img_0001.jpg
- Classroom photos: put in `input/class_photos/`; date subfolders recommended
  - Example: `input/class_photos/2024-12-21/group_photo.jpg`
  - Without subfolders also works; program will group by detected date
- Output: written to `output/`, organized by student → date; reports generated

## ▶️ Launch Methods
- macOS: double-click `release_console/SundayPhotoOrganizer` or `release_console/启动工具.sh`
- macOS terminal: `./release_console/SundayPhotoOrganizer` (after chmod +x if needed)
- Windows: double-click `release_console/SundayPhotoOrganizer.exe` or `release_console/Launch_SundayPhotoOrganizer.bat`

Note: Older builds may have used an onedir layout like `release_console/SundayPhotoOrganizer/SundaySchool`. Current releases use onefile: `release_console/SundayPhotoOrganizer`.

macOS first-run gatekeeper: if blocked, go to System Settings → Privacy & Security → "Open Anyway".

## 🧪 Validation
- Console packaging acceptance: `tests/test_console_app.py`, `tests/test_packaged_app.py`
- Full regression: `python run_all_tests.py`

## 💡 Tips
- Accuracy improves with 2–5 clear reference photos per student.
- If the terminal says photos are missing, check folder names and file naming.
- Safe to rerun multiple times; it will continue organizing newly added photos.

## 🔧 Edge Cases
- Handles empty folders and duplicate photos to keep runs stable.

## 🔨 Modular Updates
- Core gained `config` submodule; UI gained `validators` and `guides` submodules for maintainability.
