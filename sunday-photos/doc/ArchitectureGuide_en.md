# Developer Architecture Guide

For code contributors and maintainers: deep dive into project architecture, core module principles, and best practices.

---

## I. Overall Architecture

### 1.1 Layered Design

```
┌─────────────────────────────────┐
│  CLI Entry (src/cli/run.py)     │
│  + Shim Layer (src/*.py)        │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  ServiceContainer               │
│  (Dependency Injection)         │
│  - StudentManager               │
│  - FaceRecognizer               │
│  - FileOrganizer                │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  Core Modules (src/core/)       │
│  - main.py (orchestration)      │
│  - face_recognizer.py           │
│  - student_manager.py           │
│  - file_organizer.py            │
│  - config_loader.py             │
│  - incremental_state.py         │
│  - recognition_cache.py         │
│  - parallel_recognizer.py       │
└─────────────────────────────────┘
```

### 1.3 Runtime sequence (with fallback paths)

```
CLI/run.py
  → ServiceContainer.build()
  → SimplePhotoOrganizer.run()
    → initialize()
      → StudentManager.load_students()
      → FaceRecognizer.load_reference_encodings()
      → FileOrganizer.prepare_output()
    → scan_input_directory()
      → organize_input_by_date()          # failure → warn, continue
      → load_snapshot()                   # failure → empty snapshot
      → compute_incremental_plan()
    → process_photos()
      → load_date_cache()                 # corrupted → ignore
      → parallel_or_serial_recognize()
        parallel failure → fallback to serial (log reason)
      → UnknownClustering.run()
      → save_date_cache_atomic()
    → organize_output()
      → FileOrganizer.move_and_copy()     # per-file failure → warn+skip
      → create_summary_report()
    → save_snapshot()
```

### 1.2 Key Design Principles

**Dependency Injection (DI)**
- `ServiceContainer` manages core component lifecycles
- Facilitates mocking in unit tests
- Avoids hard-coded coupling between modules

**Shim Layer**
- `src/*.py` provides backward-compatible API
- Internally delegates to `src/core/` implementations
- Shields legacy code from refactoring

**Transparent Caching**
- Recognition results cached by date in `output/.state/`
- Auto-invalidates on parameter changes (params_fingerprint)
- Silent fallback on cache corruption

**Incremental Processing**
- Snapshots track `input/class_photos` per-date folder state
- Only processes new/changed dates, skips processed
- Auto-syncs deleted dates to cleanup outputs

---

## II. Core Module Details

### 2.1 ServiceContainer (Dependency Injection)

**Location**: [src/core/main.py](src/core/main.py#L47-L77)

**Responsibilities**:
- Centrally creates and holds core component instances
- Avoids circular dependencies
- Enables test-time mocking

**Usage Example**:
```python
from src.core.main import ServiceContainer

container = ServiceContainer(
    input_dir="input",
    output_dir="output",
    classroom_dir="input/class_photos"
)

# Retrieve components
student_mgr = container.get_student_manager()
recognizer = container.get_face_recognizer()

# Pass to main orchestrator
organizer = SimplePhotoOrganizer(service_container=container)
```

**Design Highlights**:
- Lazy initialization: components created on first `get_*()` call
- Singleton behavior: the same container returns the same instance
- Isolation: different containers are independent

---

### 2.2 Incremental Processing (incremental_state)

**Location**: [src/core/incremental_state.py](src/core/incremental_state.py)

**Snapshot Structure**:
```json
{
  "version": 1,
  "generated_at": "2024-01-15T10:30:00",
  "dates": {
    "2024-01-01": {
      "files": [
        {"path": "IMG_001.jpg", "size": 123456, "mtime": 1704067200},
        {"path": "IMG_002.jpg", "size": 234567, "mtime": 1704067300}
      ]
    }
  }
}
```

**Core Functions**:
- `build_class_photos_snapshot(dir)`: Build current snapshot
- `load_snapshot(output_dir)`: Load historical snapshot
- `save_snapshot(output_dir, snapshot)`: Save snapshot
- `compute_incremental_plan(prev, curr)`: Compute delta plan

**Incremental Plan Result**:
```python
@dataclass
class IncrementalPlan:
    changed_dates: Set[str]   # Dates to reprocess
    deleted_dates: Set[str]   # Dates to cleanup
    snapshot: Dict            # New snapshot
```

**Workflow**:
1. Load historical snapshot (None on first run)
2. Build current snapshot
3. Compute incremental plan
4. Main process only handles `changed_dates`
5. Cleanup outputs for `deleted_dates`
6. Save new snapshot

**Design Considerations**:
- Zero-byte files auto-ignored (`is_supported_nonempty_image_path`)
- Records relative path, size, mtime (seconds) for cross-platform stability
- System files auto-excluded (`.DS_Store`, `Thumbs.db`)

---

### 2.3 Recognition Result Cache (recognition_cache)

**Location**: [src/core/recognition_cache.py](src/core/recognition_cache.py)

**Caching Strategy**:
- **Sharding**: Per-date (YYYY-MM-DD) file storage
- **Key**: `rel_path + size + mtime`
- **Value**: Full `FaceRecognizer.recognize_faces()` return
- **Invalidation**: Entire cache invalidates on `params_fingerprint` change

**Cache Structure**:
```json
{
  "version": 1,
  "date": "2024-01-01",
  "params_fingerprint": "sha256:abc123...",
  "entries": {
    "IMG_001.jpg|123456|1704067200": {
      "status": "success",
      "recognized_students": ["Alice", "Bob"],
      "total_faces": 2
    }
  }
}
```

**Core Functions**:
- `load_date_cache(output_dir, date)`: Load date-specific cache
- `save_date_cache_atomic(output_dir, date, cache)`: Atomic save
- `compute_params_fingerprint(params)`: Compute parameter hash

**Usage Example**:
```python
from src.core.recognition_cache import (
    load_date_cache,
    save_date_cache_atomic,
    compute_params_fingerprint
)

params = {"tolerance": 0.6, "min_face_size": 50}
fingerprint = compute_params_fingerprint(params)

cache = load_date_cache(output_dir, "2024-01-01")

# Check fingerprint match
if cache.get("params_fingerprint") != fingerprint:
    cache = {"version": 1, "date": "2024-01-01", 
             "params_fingerprint": fingerprint, "entries": {}}

# Query cache
key = f"{rel_path}|{size}|{mtime}"
if key in cache["entries"]:
    result = cache["entries"][key]
else:
    result = recognizer.recognize_faces(photo_path, return_details=True)
    cache["entries"][key] = result

save_date_cache_atomic(output_dir, "2024-01-01", cache)
```

**Fault Tolerance**:
- Returns empty cache on JSON corruption, no exceptions
- Atomic write (tmp → rename) prevents write interruptions
- Silent fallback to live recognition on cache miss

---

### 2.4 Controlled Parallel Recognition (parallel_recognizer)

**Location**: [src/core/parallel_recognizer.py](src/core/parallel_recognizer.py)

**Decision Logic** (predictable; no “smart scaling”):
1. **Force disable**: `SUNDAY_PHOTOS_NO_PARALLEL=1` → serial
2. **Force enable**: `SUNDAY_PHOTOS_PARALLEL=1` → allow parallel (still constrained by `min_photos/workers`; you can override threshold via `SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS`)
3. **Config file**: `config.json` → `parallel_recognition.enabled/min_photos/workers/chunk_size`
  - Defaults: `enabled=true`, `workers=6`, `min_photos=30`
  - `workers` is capped at CPU cores
4. **Hints**: when `enabled=false` and the batch is large (e.g. ≥50), the program logs a suggestion to enable parallel; it does not prompt interactively

**Core Functions**:
- `init_worker()`: Child process initializer (caches known encodings)
- `recognize_one(image_path)`: Recognize single photo in child process
- `_truthy_env(name, default)`: Parse env var to boolean

**Usage Example**:
```python
from multiprocessing import Pool
from src.core.parallel_recognizer import init_worker, recognize_one

# Prepare params
known_encodings = [...]
known_names = ["Alice", "Bob"]
tolerance = 0.6
min_face_size = 50

# Create process pool
with Pool(
    processes=4,
    initializer=init_worker,
    initargs=(known_encodings, known_names, tolerance, min_face_size)
) as pool:
    results = pool.map(recognize_one, photo_paths, chunksize=12)

# Results format: [(path1, details1), (path2, details2), ...]
```

**Optimization Points**:
- `initializer` caches read-only data in child processes, avoids repeated transfers
- `chunksize` balances task dispatch overhead vs load balancing
- Auto-fallback to serial on exceptions (try-except wrapper)

**Performance Data**:
- Small batch (< 30 photos): Serial faster (avoids process spawn overhead)
- Medium batch (30-100 photos): Parallel often helps noticeably (varies by hardware/data)
- Large batch (100+ photos): Parallel often helps more (varies by hardware/data)

### 2.5 Error semantics (cross-module conventions)

- **Input/Output errors**: missing directory, no write permission → raise to CLI; CLI shows user-friendly message; log fatal error.
- **Per-file/per-date faults**: corrupted image, broken daily snapshot → log warning, skip file/date, continue others.
- **Parallel failure**: auto downgrade to serial; log fallback reason (OOM/timeout/worker error); do not abort.
- **Cache/snapshot corruption**: ignore and rebuild empty structures; log warning.
- **Upstream dependency errors** (face_recognition/dlib): log error, continue other photos; mark the photo as unrecognized if needed.
- **Logging requirements**: every error should include module/function, affected path (if any), and a next-step hint.

---

### 2.6 Config Loader (config_loader)

**Location**: [src/core/config_loader.py](src/core/config_loader.py)

**Priority**:
```
Environment Variable (SUNDAY_PHOTOS_NO_PARALLEL) 
  ↓
Environment Variable (SUNDAY_PHOTOS_PARALLEL)
  ↓
config.json
  ↓
DEFAULT_CONFIG (src/core/config.py)
```

**Core Methods**:
- `load_config()`: Load config with env var overrides
- `get(key, default)`: Retrieve config value
- `save_config()`: Save configuration
- `update(key, value)`: Update configuration

**Usage Example**:
```python
from src.core.config_loader import ConfigLoader

loader = ConfigLoader()
tolerance = loader.get("tolerance", 0.6)

# Update config
loader.update("tolerance", 0.5)
loader.save_config()

# Path resolution
input_dir = loader.resolve_path("input_dir")
```

**Special Handling**:
- Parallel recognition config merging (env vars prioritized)
- Auto path resolution (relative → absolute)
- Missing keys fallback to defaults

---

## III. Development Best Practices

### 3.1 Unit Testing Standards

**Test File Naming**:
- Complete tests: `test_<module>_complete.py`
- Integration: `test_<feature>_integration.py`
- Edge cases: `test_<module>_edge_cases.py`

**Test Class Organization**:
```python
class TestModuleName:
    """Module functionality tests"""
    
    def test_basic_functionality(self):
        """Basic function should work"""
        pass
    
    def test_edge_case_empty_input(self):
        """Empty input should return default"""
        pass
    
    def test_error_handling(self):
        """Errors should be caught properly"""
        pass
```

**Mocking Usage**:
```python
from unittest.mock import patch, MagicMock

@patch('face_recognition.load_image_file')
def test_with_mock(mock_load):
    mock_load.return_value = MagicMock()
    # Test code
```

---

### 3.2 Logging Standards (See Task 4 for unification)

**Level Definitions**:
- **DEBUG**: Detailed debugging info (face positions, encoding distances)
- **INFO**: Key workflow milestones (start recognition, finish organizing)
- **WARNING**: Recoverable exceptions (missing reference photos, small faces)
- **ERROR**: User-facing errors (file corruption, permission denied)

**Format Standards**:
```python
logger.info("[Step 1/4] Initializing system components...")
logger.info(f"✓ Processing {count} photos this run")
logger.warning(f"Warning: {n} students missing reference photos")
logger.error(f"Input directory not found: {path}")
logger.debug(f"Recognized: {photo} -> {names}")
```

---

### 3.3 Error Handling Principles

**Layered Handling**:
1. **Bottom**: Specific exceptions (FileNotFoundError, ValueError)
2. **Middle**: Business exceptions (StudentPhotosLayoutError)
3. **Top**: Unified catch, log, friendly message

**Example**:
```python
try:
    result = recognizer.recognize_faces(photo_path)
except FileNotFoundError:
    logger.error(f"File not found: {photo_path}")
    return {"status": "file_not_found"}
except Exception as e:
    logger.error(f"Recognition failed: {photo_path}, error: {e}")
    return {"status": "error", "message": str(e)}
```

**User-Friendly Messages**:
- Avoid technical jargon ("dlib assertion failed" → "Face detection failed")
- Provide actionable advice ("Please check if photo is corrupted")
- Log detailed info for troubleshooting

---

## IV. Architecture Decision Records (ADR)

### ADR-001: Why Dependency Injection Container?

**Context**: Complex module dependencies, hard to mock in tests

**Decision**: Introduce `ServiceContainer` for unified component management

**Pros**:
- Test-time mock substitution
- Avoids circular dependencies
- Single responsibility (creation vs usage separation)

**Cons**:
- Adds abstraction layer
- Beginners may be unfamiliar with DI pattern

**Conclusion**: Benefits outweigh costs, adopt DI container

---

### ADR-002: Why Shard Cache by Date?

**Context**: Single-file cache bloats with photo accumulation

**Decision**: Shard by date (YYYY-MM-DD)

**Pros**:
- Auto-cleanup cache when date deleted
- Smaller individual cache files, faster I/O
- Aligns with incremental processing strategy

**Cons**:
- Multiple cache files to manage
- Manual cleanup for expired dates

**Conclusion**: Sharding better for long-term use

---

### ADR-003: Why Enable Parallel by Default?

**Context**: Teachers frequently process mid/large batches; parallelism reduces wall-clock time on multi-core CPUs

**Decision**: Default `enabled: true` with conservative defaults (`workers=6`, `min_photos=30`) and simple force-disable env var

**Pros**:
- Faster by default on common multi-core machines
- Predictable behavior (no auto-scaling; fixed default workers)
- Easy troubleshooting: `SUNDAY_PHOTOS_NO_PARALLEL=1`

**Cons**:
- On low-memory machines, parallel mode may be less stable; users may need to force serial

**Conclusion**: Better teacher experience by default, while keeping a one-line escape hatch for stability

---

## V. Common Development Tasks

### 5.1 Add New Config Option

1. Add default in [src/core/config.py](src/core/config.py)
2. Update `DEFAULT_CONFIG` dict
3. Handle special logic in `config_loader.py` (if any)
4. Update [doc/CONFIG_en.md](doc/CONFIG_en.md)
5. Add unit tests to `test_config_loader_complete.py`

### 5.2 Optimize Recognition Algorithm

1. Modify [src/core/face_recognizer.py](src/core/face_recognizer.py)
2. Update `params_fingerprint` computation (if params change)
3. Run full test suite for compatibility
4. Update performance metrics in docs

### 5.3 Add New Cache Strategy

1. Reference `recognition_cache.py` interface design
2. Implement load/save/compute_key methods
3. Integrate into main workflow `main.py`
4. Add unit and integration tests
5. Update architecture docs

---

## VI. Performance Optimization Guide

### 6.1 Recognition Performance

**Bottlenecks**:
- Embedding extraction / face encoding (backend-dependent: InsightFace inference or dlib/face_recognition encoding)
- Distance computation + best-match selection against the known reference set

**Optimization Directions**:
- Enable parallel recognition (often faster on multi-core CPUs; varies)
- Downscale reference photo size (faster encoding)
- Reduce `tolerance` to decrease comparisons

### 6.2 Memory Optimization

**Considerations**:
- Avoid loading all photos at once
- Release numpy arrays promptly
- Limit parallel workers (≤ CPU cores)

**Example**:
```python
# Avoid
all_images = [load_image(p) for p in paths]  # High memory usage

# Recommended
for path in paths:
    image = load_image(path)
    process(image)
    del image  # Release promptly
```

### 6.3 Disk I/O Optimization

**Strategies**:
- Use cache to reduce duplicate recognition
- Batch writes (`shutil.copy2` faster than multiple small writes)
- Atomic writes prevent corruption (tmp → rename)

---

## VII. Debugging Tips

### 7.1 Enable Verbose Logging

```bash
# Method 1: Environment variable
export LOG_LEVEL=DEBUG
python src/cli/run.py

# Method 2: Code modification
logger.setLevel(logging.DEBUG)
```

### 7.2 Test Individual Modules

```bash
# Test config loader
python3 -m pytest tests/test_config_loader_complete.py -v

# Test recognizer
python3 -m pytest tests/test_face_recognizer_extra.py -v

# Test incremental processing
python3 -m pytest tests/test_incremental_state_complete.py -v
```

### 7.3 Print Intermediate Results

```python
# Add debug prints in face_recognizer.py
def recognize_faces(self, photo_path):
    encodings = face_recognition.face_encodings(image)
    print(f"DEBUG: Detected {len(encodings)} faces")  # Temporary debug
    ...
```

---

## VIII. Contribution Workflow

1. **Fork** project to personal repo
2. **Create branch**: `git checkout -b feature/new-feature`
3. **Develop**: Write code + unit tests
4. **Test**: `python3 -m pytest -v`
5. **Commit**: Clear commit message
6. **Pull Request**: Describe changes & motivation
7. **Code Review**: Respond to feedback, revise
8. **Merge**: Maintainer merges after approval

---

## IX. References

- [face_recognition docs](https://face-recognition.readthedocs.io/)
- [dlib performance optimization](http://dlib.net/optimization.html)
- [PyInstaller packaging guide](https://pyinstaller.org/en/stable/)
- [Python concurrent programming](https://docs.python.org/3/library/multiprocessing.html)

---

**Update Log**:
- 2024-01-15: Initial version covering core architecture & module details
