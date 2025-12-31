# Documentation Index (Single Source of Truth)

**Last updated**: 2025-12-31

Goal: reduce duplication, keep docs consistent, and make releases more stable.

---

## 1) Which doc should I read? (by audience)

- Teachers (just follow steps): `doc/TeacherQuickStart_en.md`
- Teachers (explanations/FAQ): `doc/TeacherGuide_en.md`
- Maintainers (config/troubleshooting/env vars): `doc/CONFIG_REFERENCE_en.md`
- Contributors (architecture/implementation): `doc/ArchitectureGuide_en.md`, `doc/DeveloperGuide_en.md`
- Release/acceptance: `doc/ReleaseAcceptanceChecklist_en.md`, `doc/ReleaseFlow_en.md`, `doc/TESTING_en.md`

---

## 2) Doc governance rules (to prevent drift)

- Single Source of Truth
  - Folder layout / Work folder / cache paths: `src/core/` is authoritative
  - Teacher step-by-step: `TeacherQuickStart` is authoritative
  - FAQ and explanations: `TeacherGuide` is authoritative (don’t duplicate long explanations in QuickStart)
  - Parameters & env vars: `CONFIG_REFERENCE` is authoritative (Teacher docs should not teach parameter tuning)

- Avoid copy/paste
  - Keep each “folder tree / output layout / troubleshooting block” in one place; others should link to it.

- Change checklist (when code changes)
  - Work folder / entrypoint names: update `TeacherQuickStart` and `TeacherGuide`
  - Cache structure/paths: update `CONFIG_REFERENCE` and `ArchitectureGuide` (and `HealthCheck` if relevant)
  - Environment variables: update `CONFIG_REFERENCE` and `HealthCheck`
  - Release artifact layout: update `ReleaseFlow` and `ReleaseAcceptanceChecklist`

---

## 3) Delivery & stability recommendations

- Release gate: run `pytest -q`; for strict acceptance run `REQUIRE_PACKAGED_ARTIFACTS=1 pytest -q`
- Offline/packaged runs: prefer silent/controlled behavior over showing third-party network-check warnings to teachers.
