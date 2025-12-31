# Product Requirements Document (PRD)

**Project**: Sunday School Photo Organizer (Sunday Photos Organizer)
**Version**: 1.3.0
**Last updated**: 2025-12-31

---

## 1. Overview
### Goals
- Automatically classify classroom photos by student via face recognition.
- Organize outputs by date and student name.
- Provide configurable paths and tolerance (advanced users).
- Cluster similar unknown faces into `Unknown_Person_X` groups (v0.4.0).

### Users
- Sunday school teachers / activity organizers.
- Teachers and staff needing batch photo organization.

---

## 2. Functional Requirements
### Core Features
| Module              | Description |
|---------------------|-------------|
| Face Recognition    | Default: **InsightFace** (CPU) for face detection/embeddings; optional fallback: `face_recognition/dlib` via config/env. |
| File Organizer      | Store photos by student name and date. |
| Config Management   | Load paths, tolerance, and params from `config.json`. |
| Logging             | Record run status and errors; filter by level (DEBUG/INFO/ERROR). |

### CLI
```
python run.py \
  --input-dir "input" \    # default input directory
  --output-dir "output" \   # default output directory
  --tolerance 0.6           # face recognition tolerance (0~1, default 0.6)

# troubleshooting
python run.py --no-parallel  # force serial mode

# switch backend (advanced)
SUNDAY_PHOTOS_FACE_BACKEND=insightface python run.py  # default
SUNDAY_PHOTOS_FACE_BACKEND=dlib python run.py        # optional
```

---

## 3. Non-Functional Requirements
### Performance
- Typical runs complete within minutes for common batch sizes; performance depends on hardware, photo resolution, and image quality.
- Support concurrent/parallel processing for large batches when helpful; fall back to serial mode on failure.

### Compatibility
- OS: Windows/macOS/Linux.
- Python: >= 3.7.

### Security
- Validate required fields and ranges in `config.json`.
- Logs must not store face encoding data.

---

## 4. Data Requirements
### Input
```
input/
├── student_photos/      # Folder-only: student_photos/<student_name>/... (filenames can be anything)
└── class_photos/        # Classroom photos; date subfolders recommended (e.g., 2025-12-21/xxx.jpg)
```
Formats: .jpg / .png. No per-photo size limit (very large images may use more memory; the program will warn/skip if resources are insufficient).
Reference photos: up to 5 per student (recommended 2–5 clear photos).

### Output
```
output/
├── ZhangSan/
│   ├── 2025-12-21/
│   └── 2025-12-28/
└── LiSi/
    └── 2025-12-21/

output/
└── unknown_photos/
  ├── Unknown_Person_1/2025-12-21/
  └── 2025-12-21/
```

---

## 5. Config Requirements
### config.json
```json
{
  "input_dir": "input",
  "output_dir": "output",
  "log_dir": "logs",
  "tolerance": 0.6,
  "min_face_size": 50,
  "unknown_face_clustering": {
    "enabled": true,
    "threshold": 0.45,
    "min_cluster_size": 2
  },
  "parallel_recognition": {
    "enabled": true,
    "workers": 6,
    "chunk_size": 12,
    "min_photos": 30
  },
  "face_backend": {
    "engine": "insightface"
  }
}
```

### Dependencies (see requirements.txt)
- insightface
- onnxruntime
- opencv-python-headless
- Pillow
- numpy
- tqdm

---

## 6. Testing
- Primary test runner: `pytest -q`.
- Release acceptance (packaged artifacts required): `REQUIRE_PACKAGED_ARTIFACTS=1 python -m pytest -q`.

---

## 7. Deliverables

### 7.1 Source Repository
- Implementation: `src/` (core modules + CLI).
- Tests: `tests/`.
- Docs: `doc/` (PRD / guides / checklists).

### 7.2 Packaged Artifacts
- macOS teacher app (.app): `release_mac_app/SundayPhotoOrganizer.app`.
- macOS console bundle (onedir): `release_console/SundayPhotoOrganizer/SundayPhotoOrganizer` (built per target arch: x86_64 / arm64).
- Windows console bundle (onedir): `release_console/SundayPhotoOrganizer/SundayPhotoOrganizer.exe`.

### 7.3 User Docs
- Teacher guide: `doc/TeacherGuide.md` (ZH) + `doc/TeacherGuide_en.md` (EN).
- Config reference (SSOT): `doc/CONFIG_REFERENCE.md` (ZH) + `doc/CONFIG_REFERENCE_en.md` (EN).
- requests

Optional (only if you select `dlib` backend):
- face_recognition
- dlib

---

## 6. Testing Requirements
### Scenarios
| Type            | Description |
|-----------------|-------------|
| Unit Tests      | Core logic of face recognition and file organizer. |
| Integration     | Realistic directory layout; verify correct output grouping. |
| Performance     | Time/memory on 100+ photos. |

### Test Data
- Sample photos under `tests/data/student_photos/` and `tests/data/class_photos/`.

---

## 7. Deliverables
1. Code repo with full impl, tests, and docs.
2. Executable script(s): `run.py` (packaging/cleanup scripts maintained separately).
3. Docs: README (quick start), usage guides, PRD (this doc).

---

## 8. Risks & Constraints
- Face recognition accuracy depends on high-quality reference photos.
- Memory/CPU load for large batches; optimize as needed.
