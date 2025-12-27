# Project Health Check Report (Sunday School Photo Organizer / sunday-photos)

Updated: 2025-12-26

## 1. Summary (TL;DR)
- The codebase runs and tests are green; both source-mode and packaged-artifact validation pass.
- Face backend switching is supported: **InsightFace (default)** and **dlib/face_recognition (optional)**, with **backend-isolated caches** to prevent 128-d / 512-d mixing.
- Parallel strategy is **controlled and predictable**: parallel is enabled by default, default `workers=6`, `min_photos=30`, and there is no “smart auto-scaling”.
- Documentation has been aligned with the current implementation (backend/parallel/cache/packaging), and bilingual docs were corrected where needed.

## 2. Validation Results (Automated)
- Source mode: `pytest -q` passed (example: `198 passed, 6 skipped`).
- Packaged mode: macOS onefile console artifact was built; `REQUIRE_PACKAGED_ARTIFACTS=1 pytest -q` passed (example: `198 passed, 6 skipped`).

Recommended “release acceptance” steps:
- Build: `bash scripts/build_mac_app.sh`
- Validate packaged artifacts: `REQUIRE_PACKAGED_ARTIFACTS=1 python -m pytest -q`

## 3. Core Modules Review (Responsibilities)
- `src/core/main.py`
  - Orchestrates the pipeline: input scan → incremental cache hit → recognize misses (serial/parallel) → file operations + reports.
  - Parallel decision is driven by `parallel_recognition` (enabled/min_photos/workers) plus env overrides.
- `src/core/face_recognizer.py`
  - Face backend abstraction / compat layer:
    - Default InsightFace (embeddings commonly 512-d)
    - Optional dlib/face_recognition (embeddings commonly 128-d)
  - Key points:
    - **Backend selection priority**: `SUNDAY_PHOTOS_FACE_BACKEND` env var > `config.json` (`face_backend.engine`).
    - **Cache isolation**: reference encodings + snapshots are stored per `engine/model` to avoid cross-backend contamination.
    - **Snapshot compatibility**: snapshots carry `engine/model/embedding_dim` metadata and invalidate incompatible historical caches.
- `src/core/parallel_recognizer.py`
  - Parallelizes recognition only (spawn workers, initializer caches read-only reference data, streams results via `imap_unordered`).
  - Supports `SUNDAY_PHOTOS_NO_PARALLEL=1` to force serial; main pipeline falls back to serial if parallel fails.
- `src/core/config_loader.py` / `src/core/config.py`
  - Centralizes defaults and override rules; parallel defaults live in `DEFAULT_PARALLEL_RECOGNITION`.

## 4. Logic Risks & Reasonableness
### 4.1 Mis-assignment risk in multi-person photos (expected behavior)
- Symptom: multiple faces in one photo may map to the same student if multiple distances are below the tolerance.
- Cause: nearest-neighbor + tolerance can collide in crowded/occluded/angled scenes.
- Recommendations (without changing product requirements):
  - Teacher-side: provide 2–5 clear reference photos per student.
  - Engineering-side (future): introduce stricter assignment constraints (policy change required).

### 4.2 Cache consistency risk (addressed)
- Prior issue: mixing historical 128-d caches with 512-d embeddings caused shape mismatch crashes.
- Current mitigation: backend-isolated caches + snapshot metadata validation + safe guard on distance computation.

### 4.3 Packaging & offline deployments (important)
- InsightFace may download models on first run into a local cache (commonly `~/.insightface/`). Offline deployments should pre-download and ship the model folder.
- You can configure the cache location via environment variables (see CONFIG/DeveloperGuide).

## 5. Documentation Alignment (Code vs Docs)
Aligned points:
- Face backend: InsightFace default, optional dlib/face_recognition; switching via env/config; cache isolation paths.
- Parallel: enabled by default, default workers=6, no smart scaling; troubleshooting via `SUNDAY_PHOTOS_NO_PARALLEL=1`.
- Packaged teacher workflow: `release_console/` with same-folder input/output/logs; unwritable folder fallback to Desktop/Home and `Work folder:` is the source of truth.

## 6. Cleanup & Artifact Management
Completed safe cleanup (does not delete real input photos):
- Removed generated build/caches/intermediate artifacts under `sunday-photos/` (e.g., `build/`, `dist/`, `output/`, `logs/`, `.pytest_cache/`, `__pycache__/`, `.debug_work/`).
- Removed repo-root runtime logs and a temporary scratch file.

Optional (requires your confirmation):
- Remove legacy virtualenv folder `sunday-photos/.venv310/` if it is no longer used: `bash scripts/clean_generated_artifacts.sh --venv --yes`.

## 7. Recommended Next Improvements (Priority)
- P0 (operations): add a standard offline-deployment playbook for InsightFace model pre-download/shipping.
- P1 (accuracy UX): define and implement a stricter multi-face assignment policy (requires product decision).
- P2 (maintainability): refactor parallel-decision/logging blocks in `main.py` into small helpers (no behavior change).
