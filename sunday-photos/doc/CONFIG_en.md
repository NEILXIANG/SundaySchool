# Configuration Guide (config.json)

This project uses `config.json` as the default configuration file.

## 1. Priority / Override Rules

From highest to lowest priority:

1) CLI arguments (e.g., `--input-dir`, `--tolerance`, `--no-parallel`)
2) `config.json`
3) Built-in defaults

Additionally:
- Environment variable `SUNDAY_PHOTOS_NO_PARALLEL=1` (or `true`/`yes`) forces serial mode (useful for troubleshooting or low-memory machines).

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

### 3.3 Unknown face clustering (v0.4.0)

This feature groups similar *unknown* faces into `Unknown_Person_X` folders, helping teachers manage visitors/parents/new students.

- `unknown_face_clustering.enabled`: enable clustering (default: `true`)
- `unknown_face_clustering.threshold`: clustering threshold (default: `0.45`)
  - Lower = stricter (less false grouping)
  - Higher = looser (more grouping)
- `unknown_face_clustering.min_cluster_size`: minimum cluster size (default: `2`)
  - Only clusters with at least this many photos will produce an `Unknown_Person_X` folder
  - Singletons stay under `output/unknown_photos/YYYY-MM-DD/`

### 3.4 Parallel recognition (parallel_recognition)

Parallel recognition uses multiprocessing to leverage multiple CPU cores. It is most helpful when you have many classroom photos.

**Note**: Parallel recognition is **disabled by default** to ensure compatibility with low-memory machines and provide the most stable experience out-of-the-box. You can enable it when processing large batches of photos.

**Smart Decision**: The program automatically selects the optimal mode:
- When photos to recognize ≥ 50 and parallel is disabled, it will suggest enabling parallel mode with estimated time savings
- When photo count < `min_photos`, it automatically uses serial mode (more stable for small batches)
- If parallel recognition fails, it automatically falls back to serial mode to ensure the process continues

- `parallel_recognition.enabled`: master switch (default: `false`)
- `parallel_recognition.workers`: process count (default: `4`)
- `parallel_recognition.chunk_size`: photos per task batch (default: `12`)
- `parallel_recognition.min_photos`: enable threshold (default: `30`)
  - If classroom photo count < `min_photos`, the app falls back to serial mode for stability.

**Quick Enable Options**:
- **Temporary**: `SUNDAY_PHOTOS_PARALLEL=1 python run.py`
- **Persistent**: Set `parallel_recognition.enabled: true` in `config.json`

Force serial mode (troubleshooting):
- CLI: `python run.py --no-parallel`
- Env var: `SUNDAY_PHOTOS_NO_PARALLEL=1`

### 3.5 Cache & incremental refresh (force full rerun)

By default, snapshots and caches speed up repeat runs. If you suspect “new photos were not processed” or want a full rerun:
- Remove incremental/cache traces under `output/.state/` (snapshot) and any per-date caches (if present), then run again.
- Or rename/move the specific date folder under `class_photos/` (e.g., `2025-12-21` → `2025-12-21-new`); the app will treat it as new input and fully process it.
Note: Deleting caches does **not** delete original photos; it only forces re-recognition and regenerates outputs/reports.
