# Testing Guide

Tests are consolidated under `tests/` for quick runs by teachers and developers.

## How to run
- Full regression: `python run_all_tests.py`
- Single file: `python tests/test_teacher_onboarding_flow.py`
- No interactive blocking: `GUIDE_FORCE_AUTO=1` is set by test entrypoints; defaults auto-select in non-interactive runs.

## Suite overview
- Basics & fixes
  - tests/test_basic.py
  - tests/test_fixes.py
  - tests/test_fixes_validation.py
- Integration & end-to-end
  - tests/test_integration.py
  - tests/test_all_teacher_features.py
- Teacher-friendly flows
  - tests/test_teacher_friendly.py
  - tests/test_teacher_help_system.py
  - tests/test_teacher_onboarding_flow.py
- Scale & packaging
  - tests/test_scalability_student_manager.py
  - tests/test_console_app.py
  - tests/test_packaged_app.py
- Legacy/simple
  - tests/legacy/test_fixes_simple.py
- Edge cases
  - tests/test_edge_cases.py: empty dirs, missing references, duplicates.

## FAQ
- face_recognition warnings: `pkg_resources is deprecated` is upstream noise; ignore.
- Missing paths/dirs: tests auto-create `input/`, `output/`, etc.; ensure CWD is repo root when running manually.
- Packaging tests: `test_console_app.py` and `test_packaged_app.py` expect packaged artifacts; if absent, they will fail with missing-file messages.
