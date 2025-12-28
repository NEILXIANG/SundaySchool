# AI Requirements & Prompt Templates (for this project: teacher-friendly, zero-arg photo organizer)

Purpose:
- Reusable templates to help an AI understand the goal, constraints, and acceptance criteria.
- Includes:
  - Generic templates (usable for any project)
  - A fill-in template tailored to this repository (copy/paste to AI)
  - Specialized templates: testing / packaging / release acceptance

Last updated: 2025-12-22

---

## 0. How to use (recommended workflow)

1) Use Template A to clarify the requirement (goal / constraints / acceptance / non-goals).
2) If you are changing an existing repo, use Template B (Brownfield).
3) Ask the AI to output: “files changed + verification commands + risks”.
4) Require a final “self-check list” (consistency, edge cases, test coverage).

---

## 1) Template A: Generic “gold prompt” (recommended)

Copy the whole section below to the AI and replace anything inside [brackets].

### Template A (copy/paste)

You are a senior software engineer + product engineer. Make the smallest possible change to satisfy the requirement, while keeping it testable and releasable.

[Project]
- Name: [...]
- One-sentence goal: [...]

[Users]
- Primary user: [...] (skill level, typical behavior)
- Secondary user: [...]

[Minimal user steps (must be executable step-by-step)]
1) [...]
2) [...]
3) [...]

[Forbidden / Non-goals (explicit to prevent scope creep)]
- Users must NOT: [...]
- Not in this change: [...]

[Input/Output (be specific: paths, naming, examples)]
- Input folder structure:
  - [path] meaning [...]
- Filename rules:
  - [pattern] examples [...]
- Output folder structure:
  - [path] meaning [...]

[Core functions (priority order)]
- FR1: [...]
- FR2: [...]
- FR3: [...]

[Edge cases / failure scenarios (must cover)]
- BC1: [...]
- BC2: [...]
- BC3: [...]

[User-facing error messages]
- Must include:
  1) what happened (plain language)
  2) what to do next (actionable)
  3) where logs/evidence are (for support)

[Acceptance criteria (verifiable)]
- AC1: [...]
- AC2: [...]
- AC3: [...]

[Testing]
- Tests to add/update:
  - [...]
- Default tests must NOT depend on:
  - [...]

[Delivery]
- Output:
  - file change list (one sentence per file)
  - how to verify (commands/tasks)
  - risks + rollback
  - open issues (if any)

---

## 2) Template B: Brownfield changes (repo-specific fill-in)

Use this when iterating on this repository. Copy to the AI and only adjust a few parameters.

### Template B (copy/paste)

You are working in an existing Python repository (pytest + PyInstaller). This is a “Sunday School classroom photo organizer” for teachers.

[Most important product principles]
- Teacher workflow should be “zero args by default, zero extra config by default, and very clear steps”.
- Docs / launchers / executable names / console messages must be consistent.

[Teacher UX requirements (must implement)]
1) Teachers run the packaged app by double-clicking.
2) The app creates `input/`, `output/`, `logs/` next to the executable.
   - `input/` contains `student_photos/` and `class_photos/`.
   - Student reference photos must follow a single strict layout:
     - Only valid layout: `student_photos/<student_name>/...` (one top-level folder per student; filenames don’t matter)
     - Forbidden: images directly under `student_photos/`
     - Forbidden: nested folders under a student folder
     - Limit: use up to 5 reference photos per student (prefer latest modified)
3) If photos are missing: tell the teacher exactly what to put where, then exit.
4) If photos are present: finish organizing and open `output/` automatically.
5) If recognition is inaccurate: do NOT mention parameters/thresholds/config; only provide the “3-step fix” (add clearer frontal refs; avoid group photos as refs; use clearer classroom photos).
6) On errors: always close the loop (what happened + what to do next + where the logs are).
7) The app may move classroom photos into `YYYY-MM-DD/` folders: explain it upfront.

[Allowed scope]
- Allowed: entry output text, teacher docs, error message UX, behavior consistency, tests, packaging/acceptance docs.
- Not allowed: GUI, cloud services, asking teachers to tune parameters.

[Verification]
- `pytest` must be green.
- For releases: provide a strict acceptance mode (requires packaged artifacts exist / runnable / docs present).

[You must output]
- File change list + purpose per file
- New/updated test points
- Risks (especially consistency and teacher confusion)

---

## 3) Template C: Testing / packaging / release acceptance

### Template C (copy/paste)

Goal: establish a “stable dev default + strict release gate” dual mode.

Constraints:
- Default tests must NOT depend on packaged artifacts; missing artifacts should skip those tests.
- Release acceptance must be able to force artifacts to exist, and validate:
  - executable exists and runs
  - launchers exist
  - usage docs exist

Output:
- pytest design (dev mode skip; strict mode fail)
- packaging script key points (same venv, reproducible, artifacts go to release folder)
- one-shot acceptance command (build → strict pytest)

---

## 4) Project-specific core checklist (copy/paste)

- K1 Teacher workflow should be zero-arg by default.
- K2 Entrypoints/docs/scripts/artifact names must match.
- K3 “auto move into date folders” is correct but confusing; explain it upfront.
- K4 Errors must include next step + log location.
- K5 Releases must have a strict acceptance gate.

---

## 5) Suggested final answer format

Ask the AI to always include:
- What changed
- Why
- Risks
- How to verify (commands/tasks)
- Rollback
