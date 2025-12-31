# Configuration Reference (SSOT)

**Version**: v1.4.0  
**Last updated**: 2025-12-31

This document is the Single Source of Truth (SSOT) for configuration of the Sunday School Photo Organizer (sunday-photos):

- What settings actually take effect
- Precedence rules
- Copy/paste examples for common maintainer workflows

> Teacher default principle: teachers should not need to edit config. Configuration is for maintainers / technical helpers.

---

## 0) One sentence first: what is the “Work folder”?

- The **Work folder** is the root directory where the app reads/writes: `input/`, `output/`, `logs/`, and `config.json`.
- In packaged runs, the app prefers “next to the executable”. If that folder is not writable, it falls back to Desktop/Home and prints: `Work folder: ...` (that printed line is the source of truth).
- Maintainers can **force** the Work folder via env var: `SUNDAY_PHOTOS_WORK_DIR=/path/to/work`.

---

## 1) Config sources & precedence (authoritative)

Precedence order (high → low):

1. **CLI args**: e.g. `--input-dir --output-dir --tolerance --no-parallel`
2. **Environment variables**: only a small set of runtime toggles is supported (see Section 3)
3. **Config file (`config.json`)**: by default under the Work folder root
4. **Hardcoded defaults**: see `src/core/config.py`

Important: not every config key has an environment-variable equivalent. Only selected toggles are overridable via env vars.

---

## 2) `config.json` fields (actually read by the app)

> The project allows `_comment` / `*_comment` fields in `config.json` for human notes; the app ignores these fields.

### 2.1 Paths

| JSON key | CLI arg | Default | Meaning |
| :--- | :--- | :--- | :--- |
| `input_dir` | `--input-dir` | `input` | Input root (must contain `student_photos/` and `class_photos/`). |
| `output_dir` | `--output-dir` | `output` | Output root (student/date hierarchy + reports + `.state/`). |
| `log_dir` | N/A | `logs` | Log root (reference caches + indexes also live here). |

Tip: paths can be relative (to the Work folder) or absolute.

### 2.2 Threshold & minimum face size

| JSON key | CLI arg | Default | Meaning |
| :--- | :--- | :--- | :--- |
| `tolerance` | `--tolerance` | `0.6` | Matching threshold (lower = stricter). Teachers should not tune this; maintainers may temporarily adjust during debugging. |
| `min_face_size` | N/A | `50` | Minimum face size (approx pixels). Too high may miss faces; too low may add false detections. |

Compatibility (historical fields):

- `face_recognition.tolerance` / `face_recognition.min_face_size` are still supported.
- The app promotes `face_recognition.*` to top-level **only when** the top-level field is not explicitly set.

### 2.3 Face backend

| JSON key | Default | Meaning |
| :--- | :--- | :--- |
| `face_backend.engine` | `insightface` | Allowed: `insightface` (default/recommended), `dlib` (optional; requires `requirements-dlib.txt`). |

Note: env var `SUNDAY_PHOTOS_FACE_BACKEND` takes precedence over `config.json`.

### 2.4 Parallel recognition

| JSON key | Default | Meaning |
| :--- | :--- | :--- |
| `parallel_recognition.enabled` | `true` | Whether parallel is allowed (the app still checks thresholds before actually parallelizing). |
| `parallel_recognition.workers` | `6` | Worker process count. Project policy is “stability first”; it does not auto-scale upward by default. |
| `parallel_recognition.chunk_size` | `12` | Photos per task chunk. |
| `parallel_recognition.min_photos` | `30` | Parallel is attempted only if photos-to-process ≥ this threshold. |

Env vars can force enable/disable parallel (see Section 3). CLI `--no-parallel` also forces disable.

### 2.5 Unknown face clustering

| JSON key | Default | Meaning |
| :--- | :--- | :--- |
| `unknown_face_clustering.enabled` | `true` | Enable unknown-face clustering. |
| `unknown_face_clustering.threshold` | `0.45` | Clustering threshold (recommended stricter than `tolerance`). |
| `unknown_face_clustering.min_cluster_size` | `2` | Only create `Unknown_Person_X/` if cluster size ≥ this value. |

---

## 3) Environment variables (only those that actually work)

> These are for maintainers / troubleshooting. Do not require teachers to set env vars.

| Env var | Example | Purpose |
| :--- | :--- | :--- |
| `SUNDAY_PHOTOS_WORK_DIR` | `/Users/teacher/Desktop/SundayPhotoOrganizer` | Force Work folder root (portable demo / permission constraints). |
| `SUNDAY_PHOTOS_FACE_BACKEND` | `insightface` / `dlib` | Override backend selection (higher priority than `config.json`). |
| `SUNDAY_PHOTOS_NO_PARALLEL` | `1` | Force serial mode (debugging / low-memory). |
| `SUNDAY_PHOTOS_PARALLEL` | `1` | Force parallel mode (still subject to workers ≥ 2). |
| `SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS` | `0` | Override the “min photos to parallelize” threshold. |
| `SUNDAY_PHOTOS_DIAG_ENV` | `1` | Print extra diagnostics (CI/debug). |
| `SUNDAY_PHOTOS_PRINT_DIAG` | `1` | Print diagnostics summary in some launchers/HUD. |
| `SUNDAY_PHOTOS_TEACHER_MODE` | `1` | Teacher mode (less noisy behavior/output). |
| `SUNDAY_PHOTOS_INSIGHTFACE_HOME` | `/path/to/.insightface` | Set InsightFace model home (offline/portable deploy). |
| `SUNDAY_PHOTOS_INSIGHTFACE_MODEL` | `buffalo_l` | Set InsightFace model name (default `buffalo_l`). |
| `SUNDAY_PHOTOS_QUIET_MODELS` | `1` | Quieter model-loading logs. |

---

## 4) Copy/paste examples

### 4.1 Source run: specify input/output

```bash
python src/cli/run.py --input-dir input --output-dir output
```

### 4.2 Debug: force serial (avoid multiprocessing issues)

macOS/Linux:

```bash
SUNDAY_PHOTOS_NO_PARALLEL=1 python src/cli/run.py
```

Windows PowerShell:

```powershell
$env:SUNDAY_PHOTOS_NO_PARALLEL = "1"
python src\cli\run.py
```

### 4.3 Switch to dlib backend (maintainers only)

```bash
SUNDAY_PHOTOS_FACE_BACKEND=dlib python src/cli/run.py
```

### 4.4 Offline/portable: set Work folder + InsightFace home

```bash
SUNDAY_PHOTOS_WORK_DIR=/path/to/work \
SUNDAY_PHOTOS_INSIGHTFACE_HOME=/path/to/insightface_home \
python src/cli/run.py
```

---

## 5) Related docs

- Teacher quick start: `doc/TeacherQuickStart.md` / `doc/TeacherQuickStart_en.md`
- Teacher guide: `doc/TeacherGuide.md` / `doc/TeacherGuide_en.md`
- Testing guide: `doc/TESTING.md` / `doc/TESTING_en.md`
- Developer & packaging: `doc/DeveloperGuide.md` / `doc/DeveloperGuide_en.md`
