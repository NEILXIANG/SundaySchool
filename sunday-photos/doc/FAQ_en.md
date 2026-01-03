# FAQ & Troubleshooting

**Version**: v0.4.0  
**Last Updated**: 2026-01-02

Quick problem lookup. For detailed explanations, refer to the corresponding documentation links.

---

## Table of Contents

1. [Installation & Startup](#1-installation--startup)
2. [Recognition & Organization](#2-recognition--organization)
3. [Configuration & Optimization](#3-configuration--optimization)
4. [Advanced Issues](#4-advanced-issues)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Installation & Startup

### Q1: macOS says "Cannot open because cannot verify developer"

**A**: This is a macOS security feature (Gatekeeper). Solutions:

**Option A: System Settings (Recommended)**
1. Click "Cancel"
2. Open System Settings → Privacy & Security
3. Scroll down and find "Blocked applications" or "SundayPhotoOrganizer.app"
4. Click "Allow Anyway" or "Open"
5. Go back and double-click again

**Option B: Right-click to open**
1. Right-click `SundayPhotoOrganizer` → Choose "Open"
2. Click "Open" to confirm

**Option C: Terminal bypass**
```bash
xattr -dr com.apple.quarantine /path/to/SundayPhotoOrganizer.app
./path/to/SundayPhotoOrganizer
```

See: [Teacher Quick Start](TeacherQuickStart_en.md#most-common-issues)

---

### Q2: Windows missing DLL or library error

**A**: Usually missing Visual C++ Runtime or system libraries.

**Solution**:
1. Download and install [Microsoft Visual C++ Redistributable](https://support.microsoft.com/en-us/help/2977003)
2. Restart your computer
3. Run the program again

If the problem persists, send the `logs/` folder to your technical support.

---

### Q3: Python environment errors (ImportError, ModuleNotFoundError)

**A**: Dependencies not installed.

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# If you want to use dlib backend
pip install -r requirements-dlib.txt

# Run again
python src/cli/run.py
```

See: [Developer Guide](DeveloperGuide_en.md)

---

## 2. Recognition & Organization

### Q4: A student's photos are not recognized (all in unknown_photos)

**A**: Possible causes and solutions:

| Cause | Check | Solution |
|-------|-------|----------|
| Poor reference photo quality | Are reference photos clear, well-lit, frontal? | Add more clear frontal reference photos |
| Too few reference photos | How many per student? | Recommend 2-5 clear photos per student |
| Poor classroom photo quality | Are classroom photos clear? | If the source is blurry, recognition will be difficult |
| Threshold too strict | What is `tolerance` set to? | Try changing from 0.6 to 0.65 |
| Student too small in photo | What percentage of the frame? | Student should occupy >1/3 of frame for good recognition |

**Quick threshold adjustment**:
```json
{
  "tolerance": 0.65
}
```

See: [CONFIG_REFERENCE](CONFIG_REFERENCE_en.md), [Teacher Guide](TeacherGuide_en.md)

---

### Q5: Some photos are misclassified (recognized as wrong student)

**A**: Usually recognition confidence near threshold boundary.

**Solution**:
1. **Tighter threshold** (more strict):
   ```json
   {
     "tolerance": 0.55
   }
   ```
   Reduces false positives but may increase misses.

2. **Improve reference photos**:
   - Add more clear reference photos
   - Remove low-quality photos

3. **Check report**:
   - Review `output/*_Report.txt` for confidence scores
   - Helps determine if threshold adjustment is needed

See: [Teacher Guide](TeacherGuide_en.md)

---

### Q6: What is "Unknown_Person_X" folder?

**A**: These are automatically clustered similar unidentified faces.

- When a face cannot match any known student, it's clustered
- Multiple similar unknown faces are grouped into `Unknown_Person_1/`, `Unknown_Person_2/`, etc
- Usually visitors, parents, or failed recognition

**What to do**:
- Quickly review these photos
- If they're students, add reference photos and re-run

See: [HealthCheck_Runtime_en](HealthCheck_Runtime_en.md)

---

## 3. Configuration & Optimization

### Q7: Program is slow, how to speed up?

**A**: Several acceleration strategies:

| Strategy | Effect | Cost |
|----------|--------|------|
| Enable parallel processing (default) | High | High CPU usage |
| Increase parallel workers | Medium | More memory |
| Disable unknown face clustering | Medium | No auto-clustering |
| Reduce reference photo count | Low | Lower recognition accuracy |
| Get faster machine | High | Capital cost |

**Example config**:
```json
{
  "parallel_recognition": {
    "enabled": true,
    "workers": 8,
    "min_photos": 20
  },
  "unknown_face_clustering": {
    "enabled": false
  }
}
```

See: [CONFIG_REFERENCE](CONFIG_REFERENCE_en.md)

---

### Q8: How to switch face recognition backend (InsightFace ↔ dlib)?

**A**: Three ways:

**Method 1: Edit config.json**
```json
{
  "face_backend": {
    "engine": "dlib"
  }
}
```

**Method 2: Environment variable (highest priority)**
```bash
export SUNDAY_PHOTOS_FACE_BACKEND=dlib
python src/cli/run.py
```

**Method 3: CLI parameter (source run only)**
```bash
python src/cli/run.py --face-backend dlib
```

**Which backend is better?**
- **InsightFace** (default): High accuracy, fast (GPU recommended), recommended
- **dlib**: Medium accuracy, slower, use as fallback only

See: [CONFIG_REFERENCE](CONFIG_REFERENCE_en.md)

---

## 4. Advanced Issues

### Q9: How to run in offline/portable scenario?

**A**: Use `SUNDAY_PHOTOS_WORK_DIR` environment variable.

```bash
# macOS/Linux: Run from USB drive
export SUNDAY_PHOTOS_WORK_DIR=/Volumes/USB/SundayPhotos
python /Volumes/USB/sunday-photos/src/cli/run.py

# Windows: Run from USB drive (PowerShell)
$env:SUNDAY_PHOTOS_WORK_DIR = "D:\SundayPhotos"
D:\sunday-photos\python src\cli\run.py
```

This creates `input/`, `output/`, `logs/` in the specified location.

See: [CONFIG_REFERENCE](CONFIG_REFERENCE_en.md#3-environment-variables-complete-list)

---

### Q10: How to run diagnostics only, without processing photos?

**A**: Use diagnostic mode.

```bash
# macOS/Linux
export SUNDAY_PHOTOS_DIAG_ENV=1
python src/cli/run.py --check-env

# Windows (PowerShell)
$env:SUNDAY_PHOTOS_DIAG_ENV = "1"
python src\cli\run.py --check-env
```

This outputs system info, dependency status, config loading, but doesn't process photos.

---

### Q11: What image formats are supported?

**A**: Supported formats:

```
.jpg, .jpeg, .png, .bmp, .tiff, .webp
```

- JPEG and PNG most common, recommended
- WebP modern browsers, older systems may not support
- BMP and TIFF supported but rarely used

---

## 5. Troubleshooting

### Q12: Program crashes or exits unexpectedly, how to debug?

**A**: Follow these steps:

**Step 1: Check logs/ folder**
```bash
# See latest logs
ls -lt logs/ | head
cat logs/sunday_photos_YYYYMMDD.log  # View detailed log
```

**Step 2: Common causes**
| Error | Cause | Solution |
|-------|-------|----------|
| `Permission denied` | Insufficient permissions | Check input/output directory permissions |
| `Out of memory` | Not enough memory | Disable parallel: `"parallel_recognition": {"enabled": false}` |
| `ModuleNotFoundError` | Missing dependency | Reinstall: `pip install -r requirements.txt` |
| `libopenblas not found` | Missing GPU/math libraries | Reinstall dlib: `pip install --upgrade dlib` |

**Step 3: If still stuck**
- Collect and send:
  1. Complete `logs/` folder
  2. `config.json` content
  3. OS version
  4. Python version (`python --version`)

---

### Q13: Files in input folder not processed

**A**: Check these points:

1. **Check directory structure**:
   ```
   ✅ input/student_photos/Alice/ref.jpg         (Correct)
   ✅ input/class_photos/2026-01-01/photo.jpg    (Correct)
   ❌ input/photo.jpg                            (Wrong: not in class_photos)
   ❌ input/class_photos/Alice/photo.jpg         (Wrong: student photos go in student_photos)
   ```

2. **Check file format**:
   ```bash
   ls input/student_photos/Alice/*.jpg
   ls input/class_photos/2026-01-01/*.jpg
   ```

3. **Check permissions**:
   ```bash
   ls -la input/
   chmod -R u+rwx input/  # Ensure readable
   ```

4. **Check logs**:
   ```bash
   grep "input" logs/sunday_photos_*.log
   ```

See: [Teacher Quick Start](TeacherQuickStart_en.md)

---

### Q14: After processing, output directory is empty

**A**: Possible causes:

| Cause | What to see | Fix |
|-------|-------------|-----|
| No student reference photos | `input/student_photos/` empty | Add reference photos |
| No classroom photos | `input/class_photos/` empty | Add classroom photos |
| All photos in unknown | `output/unknown_photos/` has files | See Q4 solution |
| Recognition all failed | Lots of errors in logs | Follow Q12 troubleshooting |

---

### Q15: How to free up disk space? Can I delete logs/?

**A**: Yes, but carefully.

**Safe operations**:
```bash
# Keep only last 7 days of logs
find logs/ -type f -mtime +7 -delete

# Or clear completely (loses diagnostic info)
rm -rf logs/*
```

**Do NOT delete**:
```bash
output/.state/                  # Incremental state (deletes = reprocess all)
logs/reference_encodings/       # Reference photo cache (delete = regenerate, slower)
logs/reference_index/           # Reference index (same as above)
```

See: [HealthCheck_Runtime_en](HealthCheck_Runtime_en.md)

---

## Related Resources

- **Detailed Guide**: [TeacherGuide_en.md](TeacherGuide_en.md)
- **Configuration**: [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md)
- **Examples**: [EXAMPLES_en.md](EXAMPLES_en.md)
- **Health Check**: [HealthCheck_Runtime_en.md](HealthCheck_Runtime_en.md)
- **Developer Guide**: [DeveloperGuide_en.md](DeveloperGuide_en.md) (for technical details)

---

**Problem not solved?**

- 📧 Check detailed logs in logs/ folder
- 💬 Post in project Issues
- 👥 Contact your technical support team
