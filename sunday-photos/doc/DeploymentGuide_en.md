# 🎓 Sunday School Photo Organizer - Deployment Guide (Console Edition)

## 📦 Deliverables
Console/CLI distribution only, located under `release_console/`:
1. **SundayPhotoOrganizer** (executable, already chmod +x)
2. **启动工具.sh** (launcher script; double-click or run via terminal)
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
Desktop/主日学照片整理/
├── student_photos/            # Reference photos (e.g., 张三.jpg)
├── class_photos/              # Classroom photos (e.g., 2024-12-21/group.jpg)
├── output/                    # Results (student/date/group_103045.jpg)
└── logs/                      # Runtime logs (safe to clear)
```

### 📥 Input examples (source mode)
```
input/
├── student_photos/
│   ├── 张三.jpg
│   ├── 张三_2.jpg
│   └── LiSi.png
└── class_photos/
    ├── 2024-12-21/
    │   ├── 活动合影.jpg
    │   └── 游戏时间.png
    └── 2024-12-28/
        └── 小组讨论.jpg
```

### 📤 Output example (organized)
```
output/
├── 张三/
│   ├── 2024-12-21/
│   │   ├── 活动合影_103045.jpg
│   │   └── 游戏时间_104823.jpg
│   └── 2024-12-28/
│       └── 小组讨论_101010.jpg
├── 李四/
│   └── 2024-12-21/
│       └── 活动合影_103045.jpg
└── 未知照片/
    └── 2024-12-21/
        └── 模糊照片_105632.jpg
```

## 🚀 Teacher Workflow
- release_console/: packaged deliverables (exe + launcher + guides)
- Desktop/主日学照片整理/ (auto-created on first run):
  - student_photos/: reference photos named `Name` or `Name_index` (张三.jpg, 张三_2.jpg, LiSi.png)
  - class_photos/: classroom photos; date subfolders recommended (2024-12-21/photo.jpg)
  - output/: organized results (student → date)
  - logs/: run logs

### Input rules (source run scenario)
- Default input root: `input/`
- Reference photos: put in `input/student_photos/`
  - Naming: `Name` or `Name_index` (index optional, starts at 1), Chinese/English supported
  - Examples: 张三.jpg, 张三_2.jpg, LiSi.jpg
- Classroom photos: put in `input/class_photos/`; date subfolders recommended
  - Example: `input/class_photos/2024-12-21/活动合影.jpg`
  - Without subfolders also works; program will group by detected date
- Output: written to `output/`, organized by student → date; reports generated

## ▶️ Launch Methods
- Double-click executable: `release_console/SundayPhotoOrganizer`
- Terminal: `./release_console/SundayPhotoOrganizer`
- Launcher script: double-click or run `./release_console/启动工具.sh`

Note: Older builds may have used an onedir layout like `release_console/SundayPhotoOrganizer/SundaySchool`. Current releases use onefile: `release_console/SundayPhotoOrganizer`.

macOS first-run gatekeeper: if blocked, go to System Settings → Privacy & Security → "Open Anyway".

## 🧪 Validation
- Console packaging acceptance: `tests/test_console_app.py`, `tests/test_packaged_app.py`
- Full regression: `python run_all_tests.py`

## 💡 Tips
- Accuracy improves with 2–3 clear frontal reference photos per student.
- If the terminal says photos are missing, check folder names and file naming.
- Safe to rerun multiple times; it will continue organizing newly added photos.

## 🔧 Edge Cases
- Handles empty folders and duplicate photos to keep runs stable.

## 🔨 Modular Updates
- Core gained `config` submodule; UI gained `validators` and `guides` submodules for maintainability.
