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

### 3.2 Face matching threshold

- `tolerance`: face matching threshold (0~1, default: `0.6`)
  - Lower = stricter (fewer false positives, more missed matches)
  - Higher = looser (more matches, more false positives)

Practical range: `0.55~0.65`.

### 3.3 Parallel recognition (parallel_recognition)

Parallel recognition uses multiprocessing to leverage multiple CPU cores. It is most helpful when you have many classroom photos.

- `parallel_recognition.enabled`: master switch (default: `true`)
- `parallel_recognition.workers`: process count (default: `4`)
- `parallel_recognition.chunk_size`: photos per task batch (default: `12`)
- `parallel_recognition.min_photos`: enable threshold (default: `30`)
  - If classroom photo count < `min_photos`, the app falls back to serial mode for stability.

Force serial mode (troubleshooting):
- CLI: `python run.py --no-parallel`
- Env var: `SUNDAY_PHOTOS_NO_PARALLEL=1`
