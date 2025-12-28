# Configuration Guide (config.json)

This project uses `config.json` as the default configuration file.

## 1. Priority / Override Rules

From highest to lowest priority:

1) CLI arguments (e.g., `--input-dir`, `--tolerance`, `--no-parallel`)
2) `config.json`
3) Built-in defaults

Additionally:
- Environment variable `SUNDAY_PHOTOS_NO_PARALLEL=1` (or `true`/`yes`) forces serial mode (useful for troubleshooting or low-memory machines).
- Environment variable `SUNDAY_PHOTOS_PARALLEL=1` can temporarily enable parallel recognition (without editing `config.json`).
- Environment variable `SUNDAY_PHOTOS_FACE_BACKEND=insightface|dlib` switches the face backend (higher priority than config.json).

## 2. Why there are “comment fields” in config.json

Standard JSON does not support `//` or `/* */` comments.

To make the config self-explanatory, this project stores explanations in:
- `_comment`
- `xxx_comment`

The app ignores these fields, and the file remains valid JSON.

## 3. Quick field reference

### 3.1 Paths

- `input_dir`: input root directory (default: `input`)
  - Student reference photos: `{input_dir}/student_photos/`
  - Classroom photos: `{input_dir}/class_photos/`
- `output_dir`: output directory (default: `output`)
- `log_dir`: logs directory (default: `logs`)

Packaged app note:
- In the packaged (double-click) workflow, relative paths are resolved from the runtime **Work folder** (printed as `Work folder:` in the console).

### 3.2 Face matching threshold

- `tolerance`: face matching threshold (0~1, default: `0.6`)
  - Lower = stricter (fewer false positives, more missed matches)
  - Higher = looser (more matches, more false positives)

Practical range: `0.55~0.65`.

Note: Prefer top-level `tolerance`. Older configs may contain `face_recognition.tolerance`; the app keeps backward compatibility (it takes effect when top-level `tolerance` is not explicitly set).

### 3.2.1 Minimum face size (far/small faces)

- `min_face_size`: minimum face size in pixels (approx, default: `50`)
  - Smaller: detects smaller/farther faces, but may increase false detections and runtime
  - Larger: fewer false detections, but may miss far faces

Note: Prefer top-level `min_face_size`. Older configs may contain `face_recognition.min_face_size`; the app keeps backward compatibility (it takes effect when top-level `min_face_size` is not explicitly set).

### 3.3 Face backend (face_backend)

Default backend is **InsightFace (recommended)**. You can also fall back to **dlib/face_recognition** (you must install those dependencies yourself).

- `face_backend.engine`:
  - `insightface` (default): better for complex/multi-person scenes; embeddings are commonly 512-d
  - `dlib`: compatible with the legacy `face_recognition/dlib`; embeddings are commonly 128-d

Priority: if `SUNDAY_PHOTOS_FACE_BACKEND` is set, it overrides `config.json`.

**Important (cache isolation)**: reference encodings are stored under backend/model-specific folders to prevent mixing 128-d and 512-d caches:

- Reference cache: `{log_dir}/reference_encodings/<engine>/<model>/`
- Reference snapshot: `{log_dir}/reference_index/<engine>/<model>.json`

Note: `log_dir` defaults to `logs`. Both source and packaged workflows should keep runtime logs and reference caches under the same `logs/` folder.

### 3.4 Unknown face clustering (v0.4.0)

This feature groups similar *unknown* faces into `Unknown_Person_X` folders, helping teachers manage visitors/parents/new students.

- `unknown_face_clustering.enabled`: enable clustering (default: `true`)
- `unknown_face_clustering.threshold`: clustering threshold (default: `0.45`)
  - Lower = stricter (less false grouping)
  - Higher = looser (more grouping)
- `unknown_face_clustering.min_cluster_size`: minimum cluster size (default: `2`)
  - Only clusters with at least this many photos will produce an `Unknown_Person_X` folder
  - Singletons stay under `output/unknown_photos/YYYY-MM-DD/`

### 3.5 Parallel recognition (parallel_recognition)

Parallel recognition uses multiprocessing to leverage multiple CPU cores. It is most helpful when you have many classroom photos.

Current behavior (more stable and predictable):
- Small batches (photo count < `min_photos`) fall back to serial (less overhead and easier debugging)
- Large batches (photo count ≥ `min_photos`) use multiprocessing
- If parallel recognition fails, it falls back to serial to finish the run

- `parallel_recognition.enabled`: master switch (default: `true`)
- `parallel_recognition.workers`: process count (default: `6`, fixed; only clamped to CPU core count as a safety cap)
- `parallel_recognition.chunk_size`: photos per task batch (default: `12`)
- `parallel_recognition.min_photos`: enable threshold (default: `30`)
  - If classroom photo count < `min_photos`, the app falls back to serial mode for stability.

**Quick Enable Options**:
- **Temporary**: `SUNDAY_PHOTOS_PARALLEL=1 python run.py`
- **Persistent**: Set `parallel_recognition.enabled: true` in `config.json`

Debug tip:
- `SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS=0` forces parallel even for small batches (generally not recommended).

Force serial mode (troubleshooting):
- CLI: `python run.py --no-parallel`
- Env var: `SUNDAY_PHOTOS_NO_PARALLEL=1`

### 3.6 Cache & incremental refresh (force full rerun)

By default, snapshots and caches speed up repeat runs. If you suspect “new photos were not processed” or want a full rerun:
- Remove incremental/cache traces under `output/.state/` (snapshot) and any per-date caches (if present), then run again.
- Or rename/move the specific date folder under `class_photos/` (e.g., `2025-12-21` → `2025-12-21-new`); the app will treat it as new input and fully process it.
Note: Deleting caches does **not** delete original photos; it only forces re-recognition and regenerates outputs/reports.

## 4. Common environment variables (troubleshooting / advanced)

For maintainers/technical helpers. Teachers typically don’t need these.

- `SUNDAY_PHOTOS_WORK_DIR`: force the Work folder root directory (useful for portable deployments)
- `SUNDAY_PHOTOS_DIAG_ENV=1`: enable diagnostic output (prints extra environment/path info)
- `SUNDAY_PHOTOS_QUIET_MODELS=1`: suppress noisy model-loading output (default on; set to `0` to see full output)
- `SUNDAY_PHOTOS_INSIGHTFACE_HOME`: override InsightFace model directory (offline/portable)
- `SUNDAY_PHOTOS_INSIGHTFACE_MODEL`: override InsightFace model name (default: `buffalo_l`)
- `SUNDAY_PHOTOS_NO_PARALLEL=1`: force serial mode
- `SUNDAY_PHOTOS_PARALLEL=1`: force allow parallel mode (still constrained by workers/min_photos)
- `SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS=0`: debug-only; allow parallel even for small batches
