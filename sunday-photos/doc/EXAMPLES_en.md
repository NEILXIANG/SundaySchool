# Examples & Best Practices (SSOT)

**Version**: v0.4.0  
**Last Updated**: 2026-01-02

This document is the Single Source of Truth for all examples, configurations, and directory structures. Other documents should reference here instead of duplicating content.

---

## Table of Contents

1. [input Directory Structure](#1-input-directory-structure)
2. [output Directory Structure](#2-output-directory-structure)
3. [Configuration File Examples](#3-configuration-file-examples)
4. [Command Line Examples](#4-command-line-examples)
5. [Environment Variable Examples](#5-environment-variable-examples)

---

## 1. input Directory Structure

### 1.1 Standard Structure (Recommended)

```
input/
├── student_photos/                   # Student reference photos (required: one folder per student)
│   ├── Alice/                        # Student name as folder name
│   │   ├── ref_01.jpg                # Reference photo 1
│   │   ├── ref_02.jpg                # Reference photo 2
│   │   └── ref_03.png                # PNG also supported
│   ├── Bob/
│   │   ├── photo_001.jpg
│   │   └── photo_002.jpg
│   └── John/
│       └── ref_01.jpg
└── class_photos/                     # Classroom photos (recommend date subdirectories)
    ├── 2026-01-01/                   # Date subdirectory (recommended format)
    │   ├── classroom_photo_001.jpg
    │   ├── classroom_photo_002.jpg
    │   └── group_activity.png
    ├── 2026-01-02/
    │   └── more_photos.jpg
    └── loose_photo.jpg               # Can also place directly (auto-organized by date)
```

**Notes**:
- ✅ Student names can be in Chinese or English
- ✅ 2-5 clear frontal reference photos per student recommended
- ✅ Recommend `YYYY-MM-DD` or `YYYY_MM_DD` for date subdirectories
- ✅ Program auto-analyzes dates if not in subdirectories
- ✅ Supported formats: jpg, jpeg, png, bmp, tiff, webp

### 1.2 Supported Date Formats

Program auto-recognizes these date formats and organizes classroom photos accordingly:

| Format | Example | Support |
|--------|---------|---------|
| ISO standard | `2026-01-02/` | ✅ Recommended |
| Underscore | `2026_01_02/` | ✅ Supported |
| Dot separated | `2026.01.02/` | ✅ Supported |
| Chinese date | `2026年1月2日/` | ✅ Supported |
| Filename date | `photo_20260102.jpg` | ✅ Auto-extracted |
| English month | `2026-Jan-02/` | ✅ Supported |

---

## 2. output Directory Structure

### 2.1 Standard Output (After Processing)

```
output/
├── Alice/                             # All photos for student Alice
│   ├── 2026-01-01/                    # Date 1
│   │   ├── classroom_photo_001.jpg
│   │   └── classroom_photo_002.jpg
│   └── 2026-01-02/                    # Date 2
│       └── group_activity.png
├── Bob/
│   └── 2026-01-01/
│       └── classroom_photo_001.jpg
├── Unknown_Person_1/                  # Auto-clustered similar unknown faces
│   └── 2026-01-01/
│       ├── photo_034.jpg
│       └── photo_045.jpg
├── Unknown_Person_2/
│   └── 2026-01-01/
│       └── visitor_photo.jpg
├── unknown_photos/                    # Single-appearance unknown faces
│   └── 2026-01-01/
│       └── single_unknown_face.jpg
├── no_face_photos/                    # Photos with no detected faces
│   └── 2026-01-01/
│       └── landscape_photo.jpg
├── error_photos/                      # Photos with processing errors
│   └── 2026-01-01/
│       └── corrupted_image.jpg
└── 20260102_Report.txt                # Organization report (timestamp to avoid overwrite)
```

**Notes**:
- Format: `<student_name>/<date>/<photo>`
- Timestamped report: `YYYYMMDD_Report.txt`
- `Unknown_Person_X`: Auto-clustered unknown faces (X ≥ 1)
- `unknown_photos`: Single unclusterable faces
- `no_face_photos`: Photos with no face detected
- `error_photos`: Photos with processing errors

### 2.2 Cache Directory (Hidden)

```
output/
└── .state/                            # Hidden state directory
    ├── class_photos_snapshot.json     # Snapshot (for incremental processing)
    └── recognition_cache_by_date/    # Recognition cache (by date)
        ├── 2026-01-01.json
        └── 2026-01-02.json

  ### 2.3 Two-student mini sample (input/output)

  Input example:

  ```
  input/
  ├── student_photos/
  │   ├── Alice/
  │   │   ├── a1.jpg
  │   │   └── a2.jpg
  │   └── Bob/
  │       ├── b1.jpg
  │       └── b2.jpg
  └── class_photos/
    └── 2026-01-02/
      ├── c1.jpg
      └── c2.jpg
  ```

  Expected output (with unknown clustering):

  ```
  output/
  ├── Alice/2026-01-02/...
  ├── Bob/2026-01-02/...
  ├── unknown_photos/2026-01-02/Unknown_Person_1/...
  ├── no_face_photos/2026-01-02/...   # may be absent
  ├── error_photos/2026-01-02/...     # may be absent
  ├── 20260102_整理报告.txt
  └── 20260102_智能分析报告.txt
  ```

  Notes:
  - `Unknown_Person_X` are clustered similar unknown faces; single-appearance unknowns stay under `unknown_photos/<date>/`.
  - Report files carry a timestamp to avoid overwrite; they list unknown/no-face/error counts separately.
```

---

## 3. Configuration File Examples

### 3.0 Minimal usable config.json (copy/paste)

```
{
  "input_dir": "input",
  "output_dir": "output",
  "log_dir": "logs",
  "tolerance": 0.6,
  "min_face_size": 50,
  "parallel_recognition": {
    "enabled": true,
    "workers": 6,
    "chunk_size": 12,
    "min_photos": 30
  },
  "unknown_face_clustering": {
    "enabled": true,
    "threshold": 0.45,
    "min_cluster_size": 2
  },
  "class_photos_dir": "class_photos",
  "student_photos_dir": "student_photos"
}
```

### 3.1 Advanced configs

### 3.1 Minimal Configuration (config.json)

```json
{
  "_comment": "Minimal config: only change what you need",
  "input_dir": "input",
  "output_dir": "output",
  "log_dir": "logs",
  "tolerance": 0.6
}
```

This covers most scenarios.

### 3.2 Full Configuration (config.json)

```json
{
  "_comment_1": "Paths",
  "input_dir": "input",
  "output_dir": "output",
  "log_dir": "logs",
  "class_photos_dir": "class_photos",
  "student_photos_dir": "student_photos",

  "_comment_2": "Recognition",
  "tolerance": 0.6,
  "min_face_size": 50,

  "_comment_3": "Face backend",
  "face_backend": {
    "engine": "insightface"
  },

  "_comment_4": "Parallel recognition",
  "parallel_recognition": {
    "enabled": true,
    "workers": 6,
    "chunk_size": 12,
    "min_photos": 30
  },

  "_comment_5": "Unknown face clustering (v0.4.0+)",
  "unknown_face_clustering": {
    "enabled": true,
    "threshold": 0.45,
    "min_cluster_size": 2
  }
}
```

### 3.3 Scenario Configs

#### Scenario A: High Recognition Requirement (Strict)

```json
{
  "tolerance": 0.55,
  "unknown_face_clustering": {
    "threshold": 0.40
  }
}
```

#### Scenario B: Loose Recognition (Allow Errors)

```json
{
  "tolerance": 0.65,
  "unknown_face_clustering": {
    "threshold": 0.50
  }
}
```

#### Scenario C: Disable Unknown Face Clustering

```json
{
  "unknown_face_clustering": {
    "enabled": false
  }
}
```

#### Scenario D: Use dlib Backend (Instead of InsightFace)

```json
{
  "face_backend": {
    "engine": "dlib"
  }
}
```

#### Scenario E: Disable Parallel Processing (Debug)

```json
{
  "parallel_recognition": {
    "enabled": false
  }
}
```

---

## 4. Command Line Examples

### 4.1 Basic Run

```bash
# Use default config
python src/cli/run.py

# Use config.json in specified work directory
cd /Users/teacher/Desktop/SundayPhotoOrganizer
python /path/to/src/cli/run.py
```

### 4.2 CLI Parameter Overrides

```bash
# Specify input/output directories
python src/cli/run.py --input-dir /custom/input --output-dir /custom/output

# Specify recognition threshold
python src/cli/run.py --tolerance 0.55

# Disable parallel processing (debugging)
python src/cli/run.py --no-parallel

# Show help
python src/cli/run.py --help
```

### 4.3 Run from Source

```bash
# Clone and enter project
git clone <repo-url> sunday-photos
cd sunday-photos

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python src/cli/run.py
```

---

## 5. Environment Variable Examples

### 5.1 Force Work Folder Location (Portable/Offline)

```bash
# macOS/Linux
export SUNDAY_PHOTOS_WORK_DIR=/Volumes/USB_Drive/SundayPhotos
python src/cli/run.py

# Windows (PowerShell)
$env:SUNDAY_PHOTOS_WORK_DIR = "D:\SundayPhotos"
python src\cli\run.py
```

### 5.2 Switch Face Recognition Backend

```bash
# macOS/Linux use dlib
export SUNDAY_PHOTOS_FACE_BACKEND=dlib
python src/cli/run.py

# Windows (PowerShell) use InsightFace
$env:SUNDAY_PHOTOS_FACE_BACKEND = "insightface"
python src\cli\run.py
```

### 5.3 Disable Parallel Processing (Debug/Low Memory)

```bash
# macOS/Linux
export SUNDAY_PHOTOS_NO_PARALLEL=1
python src/cli/run.py

# Windows (PowerShell)
$env:SUNDAY_PHOTOS_NO_PARALLEL = "1"
python src\cli\run.py
```

### 5.4 Enable Diagnostic Output

```bash
# macOS/Linux
export SUNDAY_PHOTOS_DIAG_ENV=1
python src/cli/run.py

# Windows (PowerShell)
$env:SUNDAY_PHOTOS_DIAG_ENV = "1"
python src\cli\run.py
```

### 5.5 Combined: Offline + dlib + Diagnostics

```bash
# macOS/Linux
export SUNDAY_PHOTOS_WORK_DIR=/mnt/usb/work
export SUNDAY_PHOTOS_FACE_BACKEND=dlib
export SUNDAY_PHOTOS_DIAG_ENV=1
python src/cli/run.py

# Windows (PowerShell)
$env:SUNDAY_PHOTOS_WORK_DIR = "D:\offline_work"
$env:SUNDAY_PHOTOS_FACE_BACKEND = "dlib"
$env:SUNDAY_PHOTOS_DIAG_ENV = "1"
python src\cli\run.py
```

---

## Related Documentation

- Complete configuration reference: [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md)
- Teacher quick start: [TeacherQuickStart_en.md](TeacherQuickStart_en.md)
- Developer guide: [DeveloperGuide_en.md](DeveloperGuide_en.md)
- Runtime health check: [HealthCheck_Runtime_en.md](HealthCheck_Runtime_en.md)
- Release acceptance: [HealthCheck_Release_en.md](HealthCheck_Release_en.md)
