# Sunday School Photo Organizer

<div align="center">

**🎉 Intelligent Photo Organizer Designed for Teachers**

*Let teachers focus on teaching, let technology handle the chores*

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)](tests/)

[Features](#-core-features) • [Documentation](#-documentation) • [中文](README.md)

</div>

---

## 📖 Introduction

This is an intelligent photo organization tool designed for Sunday schools. Using advanced face recognition technology, it automatically sorts class photos by student, freeing teachers from hours of manual sorting.

---

## 🚀 Documentation

**For Teachers (Quick Start)** 👇  
[Teacher Quick Start](doc/TeacherQuickStart_en.md) (3 steps)

**For Teachers (Full Guide)** 👇  
[Teacher Guide](doc/TeacherGuide_en.md) (FAQ, Best Practices)

**For Developers** 👇  
[Developer Guide](doc/DeveloperGuide_en.md) (Setup, Build)

**For Architecture** 👇  
[Architecture Guide](doc/ArchitectureGuide_en.md) (Design, Modules)

**For Configuration** 👇  
[Config Reference](doc/CONFIG_REFERENCE_en.md) (Parameters, Env Vars)

**For Release Managers** 👇  
[Release Flow](doc/ReleaseFlow_en.md) (Packaging, CI/CD)

**Examples & Checklists** 👇  
[Examples](doc/EXAMPLES_en.md) | [FAQ](doc/FAQ_en.md) | [Health Check](doc/HealthCheck_Runtime_en.md)

**Full Index** 👇  
[Documentation Index](doc/INDEX_en.md)

---

## ⭐ Core Features

- 🧠 **Intelligent Recognition**: InsightFace with multi-encoding fusion.
- ⚡ **High Performance**: Parallel processing + Incremental updates + Caching.
- 🛡️ **Fault Tolerance**: Graceful degradation on errors.
- 📊 **Professional Output**: Auto-generated reports, Unknown face clustering.
- 🎨 **Out of the Box**: Zero-config start, auto-creates directories.

---

## 📁 Directory Structure Example

For detailed structure, see [EXAMPLES_en.md](doc/EXAMPLES_en.md).

```
Work folder/
├── input/                    # Source photos
│   ├── student_photos/       # Reference photos
│   └── class_photos/         # Class photos
├── output/                   # Organized results
└── logs/                     # Runtime logs
```
