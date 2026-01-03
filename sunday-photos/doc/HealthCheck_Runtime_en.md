# Runtime Health Check & Troubleshooting

**Version**: v0.4.0  
**Last updated**: 2026-01-02

Purpose: Quickly diagnose issues when the program behaves unexpectedly.

---

## 1. Basic Environment Check

- [ ] **Work Folder Location**: 
  - Check the first line of console output: `Work folder: ...`
  - Confirm this directory is writable.
  - Confirm `input/`, `output/`, `logs/` exist inside it.

- [ ] **Input Directory Structure**:
  - Does every student have their own folder under `input/student_photos/`?
  - Are there photos in `input/class_photos/`?

- [ ] **Log Files**:
  - Is there a fresh `.log` file in `logs/`?
  - Open the latest log, are there any `ERROR` or `WARNING` messages?

---

## 2. Common Symptoms & Solutions

### Symptom A: Crash immediately (Flash and close)
- **Cause**: Permission issues or missing dependencies (Windows).
- **Diagnosis**: 
  - macOS: Open Terminal, drag executable in, press Enter.
  - Windows: Open CMD, drag .exe in, press Enter.
- **Solution**: 
  - Check antivirus software.
  - Check for missing VC++ Runtime.

### Symptom B: "input directory not found"
- **Cause**: Wrong working directory (not running from next to executable).
- **Solution**: 
  - Always double-click the `Launcher` or `.app`.
  - Check if `Work folder` path matches expectation.

### Symptom C: All photos go to unknown
- **Cause**: Invalid reference photos or threshold too high.
- **Diagnosis**: 
  - Is `input/student_photos/` empty?
  - Does log say `Loaded 0 students`?
- **Solution**: 
  - Ensure reference photos are clear frontal faces.
  - Ensure photos are inside `student_photos/<Name>/`, not directly in root.

---

## 3. Automated Diagnosis (Recommended)

If available, run the diagnostic script:

```bash
# macOS / Linux
bash scripts/diagnose.sh
```

---

## 4. Cache Clearing (Last Resort)

If you suspect cache corruption:

1. Delete `output/.state/` folder (resets incremental state).
2. Delete `logs/reference_encodings/` folder (forces re-encoding references).
3. Rerun the program.
