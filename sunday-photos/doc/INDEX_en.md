# Documentation Index (Authoritative Entry Point)

**Version**: v0.4.0  
**Last Updated**: 2026-01-02

Goal: Minimize duplication, standardize conventions, and make project more sustainable.

---

## 1. Quick Find by Role

| I am... | Read this doc | Time |
|---------|---------------|------|
| **Teacher** (just follow steps) | [TeacherQuickStart_en.md](TeacherQuickStart_en.md) | 5 min |
| **Teacher** (need explanations/FAQ) | [TeacherGuide_en.md](TeacherGuide_en.md) + [FAQ_en.md](FAQ_en.md) | 20 min |
| **Teacher** (troubleshooting) | [HealthCheck_Runtime_en.md](HealthCheck_Runtime_en.md) or [FAQ_en.md](FAQ_en.md) | 5-10 min |
| **Tech Support** (tuning/debugging) | [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md) + [FAQ_en.md](FAQ_en.md) | 15 min |
| **Tech Support** (diagnosis) | [HealthCheck_Runtime_en.md](HealthCheck_Runtime_en.md) + logs/ | 10 min |
| **Developer** (understand arch) | [ArchitectureGuide_en.md](ArchitectureGuide_en.md) | 30 min |
| **Developer** (local dev) | [DeveloperGuide_en.md](DeveloperGuide_en.md) | 30 min |
| **Developer** (write configs) | [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md) + [EXAMPLES_en.md](EXAMPLES_en.md) | 20 min |
| **Release Manager** (packaging) | [ReleaseFlow_en.md](ReleaseFlow_en.md) | 30 min |
| **Release Manager** (acceptance) | [ReleaseAcceptanceChecklist_en.md](ReleaseAcceptanceChecklist_en.md) + [HealthCheck_Release_en.md](HealthCheck_Release_en.md) | 1 hour |

---

## 2. Complete Documentation List

### User Docs (Teachers & Non-Technical Staff)

| Document | Purpose |
|----------|---------|
| [TeacherQuickStart_en.md](TeacherQuickStart_en.md) | 3-step quick start |
| [TeacherGuide_en.md](TeacherGuide_en.md) | In-depth usage & best practices |
| [FAQ_en.md](FAQ_en.md) | Quick problem lookup |
| [EXAMPLES_en.md](EXAMPLES_en.md) | Authoritative examples & configs |
| [HealthCheck_Runtime_en.md](HealthCheck_Runtime_en.md) | Runtime diagnostics |
| [HealthCheck_Release_en.md](HealthCheck_Release_en.md) | Release acceptance checklist |

### Developer Docs (Developers & Maintainers)

| Document | Purpose |
|----------|---------|
| [ArchitectureGuide_en.md](ArchitectureGuide_en.md) | System design & module internals |
| [DeveloperGuide_en.md](DeveloperGuide_en.md) | Local dev, testing, packaging |
| [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md) | **SSOT**: All parameters, priorities, env vars |
| [TESTING_en.md](TESTING_en.md) | Running tests & coverage |
| [LoggingStandards_en.md](LoggingStandards_en.md) | Log formats & debugging |

### Operations Docs (Release & Deployment)

| Document | Purpose |
|----------|---------|
| [ReleaseFlow_en.md](ReleaseFlow_en.md) | Packaging & CI/CD workflow |
| [DeploymentGuide_en.md](DeploymentGuide_en.md) | Offline deployment & config mgmt |
| [ReleaseAcceptanceChecklist_en.md](ReleaseAcceptanceChecklist_en.md) | Pre-release checklist |

### Product Docs (Requirements & Decisions)

| Document | Purpose |
|----------|---------|
| [PRD_en.md](PRD_en.md) | Feature & non-functional requirements |

---

## 3. Documentation Governance Rules (Mandatory)

### 3.1 Single Source of Truth (SSOT) List

Below content is defined in specified docs. Other docs must reference, **no duplication**:

| Content | SSOT Document |
|---------|---------------|
| **Directory structure examples** | [EXAMPLES_en.md](EXAMPLES_en.md) |
| **Configuration field details** | [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md) |
| **Environment variable list** | [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md) |
| **Command line examples** | [EXAMPLES_en.md](EXAMPLES_en.md) / [DeveloperGuide_en.md](DeveloperGuide_en.md) |
| **Work folder explanation** | [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md) + [HealthCheck_Runtime_en.md](HealthCheck_Runtime_en.md) |
| **Cache structure & paths** | [ArchitectureGuide_en.md](ArchitectureGuide_en.md) |
| **Teacher operation steps** | [TeacherQuickStart_en.md](TeacherQuickStart_en.md) |
| **Common problems & solutions** | [FAQ_en.md](FAQ_en.md) |
| **Reference photo requirements** | [TeacherQuickStart_en.md](TeacherQuickStart_en.md) + [TeacherGuide_en.md](TeacherGuide_en.md) |
| **Release workflow steps** | [ReleaseFlow_en.md](ReleaseFlow_en.md) |

### 3.2 Reference Not Duplicate Rule

**❌ Wrong** (duplication):
```markdown
## input Directory
input/
├── student_photos/
│   └── Alice/
...
```

**✅ Correct** (link reference):
```markdown
## input Directory
See [EXAMPLES_en.md#1-input-directory-structure](EXAMPLES_en.md#1-input-directory-structure)
```

### 3.3 Change Synchronization Checklist

| Change | Sync To |
|--------|---------|
| Work folder logic | TeacherQuickStart, TeacherGuide, CONFIG_REFERENCE, HealthCheck |
| Parameter/config fields | CONFIG_REFERENCE, EXAMPLES, ArchitectureGuide |
| Environment variables | CONFIG_REFERENCE, HealthCheck, DeveloperGuide |
| Version/date | All doc headers |
| Cache structure/paths | ArchitectureGuide, HealthCheck, CONFIG_REFERENCE |
| Packaged artifact structure | ReleaseFlow, ReleaseAcceptanceChecklist, HealthCheck |

---

## 4. Editor Workflow

### Before Editing

- [ ] Which document(s) does this change belong to?
- [ ] Does it violate any SSOT rule?
- [ ] Does the corresponding English version need sync?
- [ ] Are version & date fields correct?

### After Editing

- [ ] All links valid?
- [ ] Tables aligned?
- [ ] Code block syntax highlighting?
- [ ] Chinese & English versions synchronized?

---

## Questions?

- 📖 Check quick reference (Section 1)
- 🔍 Ctrl+F search keywords
- 💬 Post in Issues

**Last Updated**: 2026-01-02
