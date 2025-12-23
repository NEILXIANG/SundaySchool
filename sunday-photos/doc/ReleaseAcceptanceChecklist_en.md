# Release Acceptance Checklist

**Version**: v0.4.0  
**Updated**: 2025-12-23

Purpose: Ensure the "teacher-ready release package" passes rigorous validation before delivery, preventing issues such as: missing executables, inconsistent documentation, missing directories after running, or teachers not knowing what to do next.

Scope:
- When you're ready to distribute the entire `release_console/` folder to teachers.

---

## A. Required Deliverables

Must exist under `sunday-photos/release_console/` (by platform):

**macOS:**
- `SundayPhotoOrganizer` (macOS console executable)
- `启动工具.sh` (launcher script for double-click or terminal execution)

**Windows:**
- `SundayPhotoOrganizer.exe` (Windows console executable)
- `Launch_SundayPhotoOrganizer.bat` (launcher script; double-click entry, keeps window open)

**Universal:**
- `使用说明.txt` (Chinese teacher guide, zero-parameter approach)
- `USAGE_EN.txt` (English teacher guide, optional)

**Optional** (placeholder/example directories; teachers actually use Desktop `SundaySchoolPhotoOrganizer/`):
- `input/` (may contain `student_photos/`, `class_photos/` for source-mode examples)
- `output/` (can be empty)
- `logs/` (can be empty)

**Acceptance Points:**
- **macOS**: Executable has execute permission; launches normally.
- **Windows**: Executable launches normally; .bat launcher script starts the program and doesn't instantly close.

---

## B. Runtime Behavior (Teacher-Side Zero-Parameter)

### First Run:
- Creates `SundaySchoolPhotoOrganizer/` on Desktop (or the agreed-upon directory name in documentation).
- Automatically creates/confirms the following subdirectories exist:
  - `student_photos/`, `class_photos/`, `output/`, `logs/`
- If essential photos are missing:
  - Output must be "non-technical description + what to do next + where logs are"
  - Program should exit safely (no accidental deletion/moving)

### Missing Student Reference Photos (allowed to continue):
- `student_photos` can be temporarily empty; program can still continue organizing.
- **Acceptance Point**: Must clearly prompt "classroom photos will all go to unknown" and provide "how to add reference photos to improve accuracy" as next step.

### Missing Classroom Photos (must exit):
- When `class_photos` is empty, should prompt next steps and exit safely.

### Normal Organization:
- After processing completes, prompt "completed + where output is".
- Should attempt to automatically open `output/`; if auto-open fails, it should still be considered success (should not return failure due to this).

### Date Grouping/Moving:
- If the program will move classroom photos to `YYYY-MM-DD/`: must explain in output or documentation that "this is normal behavior".

### Recognition Inaccuracy:
- Only allowed to give "three-step method" suggestions:
  1) Add clear frontal-face reference photos
  2) Reference photos should not be group photos
  3) Classroom photos should be clear and well-lit
- Must NOT ask teachers to adjust parameters, change thresholds, or edit config files.

---

## C. Error Loop Closure (Help-Friendly)

Any error message must include:
- What happened (teacher-facing language)
- What to do next (specific actions)
- Log location (so teachers can send the latest log to you)

**Acceptance Point:**
- When an error occurs, the latest log file must exist in `logs/`.

---

## D. One-Click Acceptance (Developer Side)

Recommended acceptance sequence:

1) **Build packaging artifacts** (macOS):
   - Use repository scripts to build, confirm artifacts land in `release_console/`.
   - Windows artifacts need to be built on Windows (PyInstaller doesn't support cross-platform compilation).

2) **Run tests in strict mode** (require packaged artifacts to exist):
   - In VS Code, run task: `release acceptance (build + require packaged artifacts)`
   - Or use equivalent command (see repository testing documentation).

**Pass Criteria:**
- Strict mode pytest all green (128+ test cases pass).
- `release_console/` artifacts complete; manual trial run meets sections B/C.

---

## E. Manual Quick Spot Check (2 Minutes Before Sending to Teachers)

- Double-click launch entry (executable or launcher script) once
- Confirm desktop directory created successfully
- Put 1-2 random photos to simulate input, confirm no crash
- Confirm `output/` has results or clear prompts
- Confirm `logs/` generated logs

---

## Checklist Summary

### Pre-Release Validation
- [ ] All deliverables exist in `release_console/`
- [ ] Executables have correct permissions (macOS: chmod +x)
- [ ] User guides are complete and accurate
- [ ] All tests pass (128+ test cases, 100% pass rate)
- [ ] Strict mode tests pass (`REQUIRE_PACKAGED_ARTIFACTS=1`)

### Runtime Behavior
- [ ] First run creates desktop directory structure
- [ ] Missing photos trigger helpful prompts (not crashes)
- [ ] Normal processing completes successfully
- [ ] Output directory opens automatically (or clear path shown)
- [ ] Date grouping behavior is explained

### Error Handling
- [ ] All errors have user-friendly messages
- [ ] Next steps are clearly indicated
- [ ] Log files are generated and accessible
- [ ] No technical jargon in user-facing messages

### Manual Testing
- [ ] Double-click launch works (macOS & Windows)
- [ ] Desktop directory creation verified
- [ ] Sample photo processing tested
- [ ] Output verification completed
- [ ] Log generation confirmed

---

## Related Documentation

- **Deployment Guide**: [DeploymentGuide.md](DeploymentGuide.md) - Detailed deployment instructions
- **Teacher Guide**: [TeacherGuide.md](TeacherGuide.md) - End-user documentation
- **Testing Guide**: [TESTING.md](TESTING.md) - Test suite documentation
- **Developer Guide**: [DeveloperGuide.md](DeveloperGuide.md) - Development handbook

---

*Last Updated: 2025-12-23 | Version: v0.4.0*
