# Logging Standards Guide

Unified logging standards to ensure clear, consistent, and easily debuggable log messages.

**Version**: v0.4.0  
**Last updated**: 2025-12-31

---

## I. Log Level Definitions

### 1.1 DEBUG (Debugging)

**Purpose**: Detailed debugging information for developers only

**Use Cases**:
- Recognition result details (face positions, encoding distances)
- Cache hit/miss details
- File path resolution process
- Loop internal state
- Function parameters & return values

**Examples**:
```python
logger.debug(f"Recognized: {os.path.basename(photo_path)} -> {student_names}")
logger.debug(f"No faces: {os.path.basename(photo_path)}")
logger.debug(f"Copy photo: {source_path} -> {target_path}")
logger.debug(f"No faces detected in image: {image_path}")
logger.debug(f"Persist encoding failed (session continues): {e}")
```

**Notes**:
- Not output to console by default (requires LOG_LEVEL=DEBUG)
- May contain sensitive path information
- Avoid overuse (impacts performance)

---

### 1.2 INFO (Information)

**Purpose**: Key workflow milestones and normal status, user-facing

**Use Cases**:
- Program start/end banners
- Step progress hints ([Step 1/4])
- Operation completion confirmations (✓ markers)
- Statistics (processed count, success count)
- Performance hints & suggestions
- Config load success

**Examples**:
```python
logger.info("=====================================")
logger.info("Sunday School Photo Organizer (Folder Mode)")
logger.info("[Step 1/4] Initializing system components...")
logger.info("✓ System initialization complete")
logger.info(f"✓ Processing {len(photo_files)} photos this run")
logger.info(f"Successfully loaded {len(self.students_data)} students")
logger.info("💡 Performance tip: Detected %d photos, consider enabling parallel recognition", photo_count)
logger.info(f"Total time: {int(minutes)}m {int(seconds)}s")
```

**Format Standards**:
- Step hints: `[Step X/Y] Processing...`
- Completion: `✓ Operation description completed`
- Statistics: `Metric: Value Unit`
- Tips: `💡/ℹ️  Suggestion content`

**User-Friendly Principles**:
- Use clear descriptions
- Avoid technical jargon
- Provide actionable advice
- Data easy to understand

---

### 1.3 WARNING (Warning)

**Purpose**: Recoverable exceptions or situations needing user attention

**Use Cases**:
- Missing reference photos
- Face too small to recognize
- File corruption but can continue
- Empty file read attempt
- Parallel recognition failure fallback to serial
- Config exception using defaults

**Examples**:
```python
logger.warning(f"Warning: {len(missing_photos)} students missing reference photos")
logger.warning(f"Student {student_name} has no reference photo")
logger.warning(f"No faces detected in photo: {photo_path}")
logger.warning(f"student_photos directory not found: {self.students_photos_dir}")
logger.warning(f"Parallel recognition failed, falling back to serial: {str(e)}")
logger.warning("⚠️ Input directory empty or not found, please check input/student_photos")
```

**Format Standards**:
- Prefix with `Warning:` / `⚠️`
- Clear problem description
- Explain impact scope
- Prompt user to check paths

**Handling Principles**:
- Don't interrupt program execution
- Log details for troubleshooting
- Provide solution suggestions when appropriate

---

### 1.4 ERROR (Error)

**Purpose**: User-facing errors that may affect results

**Use Cases**:
- Input directory not found
- Insufficient file permissions
- Photo load failure
- Copy operation failure
- Serious recognition error
- Config file corruption

**Examples**:
```python
logger.error(f"Input directory not found: {self.photos_dir}")
logger.error(f"Copy photo failed: {photo_path} -> {student_dir}")
logger.error(f"Load student {student_name} photo {photo_path} failed: {str(e)}")
logger.error(f"Recognition error: {os.path.basename(photo_path)} - {msg}")
logger.error(f"New photo not found: {new_photo_path}")
```

**Format Standards**:
- Clearly state error type
- Include relevant path/filename
- Attach exception info
- Avoid overly technical terms

**User-Friendly Translation**:
```python
# Avoid
logger.error(f"dlib assertion failed: {e}")

# Recommended
logger.error(f"Face detection failed: {photo_path}, please check if photo is corrupted")
```

---

### 1.5 CRITICAL (Critical)

**Purpose**: Fatal errors preventing program continuation

**Use Cases**:
- Core dependency library missing
- Out of memory
- Database connection failure (if applicable)
- System resource exhaustion

**Note**: Rarely used in current project, most errors are recoverable

**Examples**:
```python
logger.critical("Cannot load face_recognition library, program cannot continue")
logger.critical("Insufficient disk space, cannot save output files")
```

---

## II. Log Format Standards

### 2.1 Basic Format

**Configuration**:
```python
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Output Example**:
```
2024-01-15 10:30:45 - main - INFO - [Step 1/4] Initializing system components...
2024-01-15 10:30:46 - student_manager - WARNING - Warning: 2 students missing reference photos
```

### 2.2 Special Markers

**Progress Steps**:
```python
logger.info("[Step 1/4] Initializing system components...")
logger.info("[Step 2/4] Scanning input directory...")
logger.info("[Step 3/4] Performing face recognition...")
logger.info("[Step 4/4] Organizing photos...")
```

**Completion Confirmations**:
```python
logger.info("✓ System initialization complete")
logger.info("✓ Photo organization complete")
logger.info("✓ Processing 50 photos this run")
```

**Tips**:
```python
logger.info("💡 Performance tip: Consider enabling parallel recognition for faster processing")
logger.info("ℹ️  Photo count < parallel threshold, using serial mode")
logger.warning("⚠️ Input directory empty or not found")
```

**Banners**:
```python
logger.info("=====================================")
logger.info("Sunday School Photo Organizer")
logger.info("=====================================")
```

---

## III. Modular Logging Practices

### 3.1 Get Logger

**Recommended**:
```python
import logging

logger = logging.getLogger(__name__)
```

**Avoid**:
```python
# Don't use root logger
logger = logging.getLogger()

# Don't hardcode module name
logger = logging.getLogger("face_recognizer")
```

### 3.2 Logger Naming Convention

- `src.core.main` → Main workflow logs
- `src.core.face_recognizer` → Recognition module logs
- `src.core.student_manager` → Student management logs
- `src.core.file_organizer` → File organization logs

### 3.3 Log Config Initialization

**Location**: [src/core/utils.py](src/core/utils.py)

**Usage**:
```python
from src.core.utils import setup_logger

logger = setup_logger("main", log_dir="logs")
```

---

## IV. Exception Logging Standards

### 4.1 Record Stack Traces

**Recommended**:
```python
try:
    result = process_photo(path)
except Exception as e:
    logger.error(f"Photo processing failed: {path}", exc_info=True)
    # Or
    logger.debug("Detailed stack trace", exc_info=True)
```

**Avoid**:
```python
# Don't swallow exceptions
try:
    process_photo(path)
except Exception:
    pass  # ❌ Silent failure

# Don't just print exception object
except Exception as e:
    logger.error(e)  # ❌ Lacks context
```

### 4.2 Layered Handling

**Bottom Layer**: Log detailed stack (DEBUG)
```python
except FileNotFoundError as e:
    logger.debug(f"File read failed: {path}", exc_info=True)
    return None
```

**Middle Layer**: Log business errors (WARNING/ERROR)
```python
except StudentPhotosLayoutError as e:
    logger.warning(f"Student photo directory structure abnormal: {e}")
    return default_value
```

**Top Layer**: User-friendly messages (ERROR)
```python
except Exception as e:
    logger.error(f"Photo organization failed, please check input directory: {input_dir}")
    sys.exit(1)
```

---

## V. Performance & Debugging

### 5.1 Conditional Logging

**Avoid Over-Computation**:
```python
# Recommended
if logger.isEnabledFor(logging.DEBUG):
    expensive_debug_info = compute_detailed_stats()
    logger.debug(f"Detailed stats: {expensive_debug_info}")

# Avoid
logger.debug(f"Detailed stats: {compute_detailed_stats()}")  # Computes even if not logged
```

### 5.2 Batch Operation Logging

**Careful with INFO in Loops**:
```python
# Avoid
for photo in photos:
    logger.info(f"Processing photo: {photo}")  # ❌ Excessive output

# Recommended
for photo in photos:
    logger.debug(f"Processing photo: {photo}")  # ✓ DEBUG level

logger.info(f"✓ Processed {len(photos)} photos")  # ✓ Summary
```

### 5.3 Debug Switches

**Environment Variable Control**:
```bash
export LOG_LEVEL=DEBUG
python src/cli/run.py
```

**Code Control**:
```python
if os.environ.get("DEBUG_MODE") == "1":
    logger.setLevel(logging.DEBUG)
```

---

## VI. Log File Management

### 6.1 Log Rotation Config

**Current Configuration**:
```python
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

**Rotation Strategy**:
- Single file max 10MB
- Keep latest 5 backups
- Auto-delete expired logs

### 6.2 Log File Naming

**Format**: `photo_organizer_YYYYMMDD.log`

**Examples**:
```
logs/photo_organizer_20240115.log
logs/photo_organizer_20240115.log.1
logs/photo_organizer_20240115.log.2
```

---

## VII. Code Review Checklist

### 7.1 Log Level Check

- [ ] INFO for key workflow, not inside loops
- [ ] WARNING for recoverable exceptions
- [ ] ERROR for user-facing issues
- [ ] DEBUG for detailed debugging
- [ ] Avoid INFO in loops

### 7.2 User-Friendly Check

- [ ] Clear descriptions
- [ ] Avoid technical jargon
- [ ] Use relative paths for display
- [ ] Error messages include solutions

### 7.3 Performance Check

- [ ] Heavy computations use isEnabledFor
- [ ] Loops use DEBUG
- [ ] Batch operations use summary logs

### 7.4 Exception Handling Check

- [ ] Critical exceptions log stack traces
- [ ] Bottom layer DEBUG, top layer ERROR
- [ ] Don't swallow exceptions
- [ ] Friendly translation of technical errors

---

## VIII. FAQ

### Q1: When to use DEBUG vs INFO?

**Rule**: User cares → INFO; Developer cares → DEBUG

**Examples**:
```python
# User cares about processed count
logger.info(f"✓ Processed {count} photos")  # INFO

# Developer cares about specific photo recognized
logger.debug(f"Recognized: {photo} -> {names}")  # DEBUG
```

### Q2: How to log sensitive information?

**Principle**: Sensitive info only at DEBUG level

**Examples**:
```python
# Full path may contain username
logger.debug(f"Full path: {os.path.abspath(path)}")  # DEBUG

# User only sees filename
logger.info(f"Processing file: {os.path.basename(path)}")  # INFO
```

### Q3: How to properly log in loops?

**Recommended Pattern**:
```python
logger.info(f"[Step 3/4] Performing face recognition...")

for photo in photos:
    logger.debug(f"Recognizing: {photo}")  # DEBUG
    result = recognize(photo)

logger.info(f"✓ Face recognition complete")  # INFO summary
logger.info(f"  - Recognized: {success_count} photos")
logger.info(f"  - Failed: {failed_count} photos")
```

---

## IX. Quick Reference

| Level | Use Case | Example Prefix | Default Output |
|-------|----------|----------------|----------------|
| DEBUG | Detailed debug | `Recognized:` | No |
| INFO | Key workflow | `[Step X/Y]` `✓` | Yes |
| WARNING | Recoverable exception | `Warning:` `⚠️` | Yes |
| ERROR | User-facing issue | `Error:` | Yes |
| CRITICAL | Fatal error | `Critical:` | Yes |

---

## X. Update Log

- 2024-01-15: Initial version, unified logging standards
