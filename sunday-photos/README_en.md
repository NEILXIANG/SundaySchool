# Sunday School Photo Organizer

<div align="center">

**🎉 Intelligent Photo Organizer Designed for Teachers**

*Let teachers focus on teaching, let technology handle the chores*

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)](tests/)

[Features](#-core-features) • [Quick Start](#-quick-start) • [Docs](#-documentation) • [Highlights](#-technical-highlights) • [中文](README.md)

</div>

---

## 📖 Introduction

This is an intelligent photo organization tool designed for Sunday schools, training centers, and similar scenarios. Using advanced face recognition technology, it automatically sorts class photos by student, freeing teachers from hours of manual sorting.

### 🎯 The Problem

**Traditional Struggles**:
- 📸 Dozens of class photos taken every week
- 👥 Manual selection for each student
- ⏰ Hours spent sorting
- 😓 Prone to errors (missed or duplicated photos)

**Our Solution**:
- ✨ One-click execution, automatically recognizes all students
- 🚀 Typical batches processed in minutes
- 📊 Auto-generated detailed statistical reports
- 🎁 Smart clustering for unknown faces (visitors/parents)

---

## ⭐ Core Features

### 🎨 Ultimate User Experience
- **Out of the Box**: Auto-creates required folder structure on first run
- **Visual Feedback**: Colorful logs + real-time progress bars
- **Smart Fault Tolerance**: Graceful degradation on errors
- **Packaged Version**: No Python installation needed for teachers

### 🧠 Intelligent Recognition Engine
- **High Accuracy**: Uses InsightFace by default (recommended); supports fallback to dlib/face_recognition
- **Multi-Encoding Fusion**: Supports multiple reference photos per student
- **Unknown Face Clustering**: Groups unrecognized faces (e.g., visitors)
- **Incremental Caching**: Reuses encodings to speed up startup

### ⚡ Performance Architecture
- **Parallel Processing**:
  - Small batches (<min_photos): Serial (default)
  - Large batches (≥min_photos): Multi-process parallel
- **Incremental Engine**:
  - Tracks processing state by date folder
  - Only processes new/changed photos
- **Sharded Caching**:
  - Results cached by date
  - Auto-invalidates on parameter changes

### 🛡️ Enterprise-Grade Stability
- **Multi-Layer Fault Tolerance**: Core flows ensure completion
- **Atomic Operations**: Safe file writes to prevent corruption
- **Error Rollback**: Auto-cleans copied files on failure
- **Friendly Error Messages**: Actionable advice for common issues

### 📊 Professional Output
- **Clear Structure**: `Student/Date/Photo`
- **Unknown Grouping**: Similar unknown faces grouped into `Unknown_Person_X`
- **Detailed Reports**: Processing time, success rate, student distribution
- **Smart Naming**: Auto-renames duplicates (`_001`) to prevent overwrites

---

## 📁 Directory Structure

```
sunday-photos/
├── input/                      # Input Root
│   ├── student_photos/         # Reference photos (folder-only: student_photos/<student_name>/...)
│   │   ├── Alice/              # Example student folder
│   │   │   ├── ref_01.jpg
│   │   │   └── ref_02.png
│   │   └── Bob/
│       └── img_0001.jpg
│   └── class_photos/           # Class photos (date subfolders recommended)
│       ├── 2024-12-21/         # Example: date subfolder
│       │   └── group_photo.jpg
│       └── loose_photo.png     # Root files also supported
├── output/                     # Results: Student/Date hierarchy + Reports
│   ├── Alice/2024-12-21/...    # Example: Student/Date/Photo
│   ├── unknown_photos/2024-12-21/... # Unmatched faces
│   └── 20241221_Report.txt     # Auto-generated report
├── logs/                       # Logs
```

---

## 🚀 Quick Start

### 👩‍🏫 For Teachers (No Code)

1. **Download** the release package (macOS or Windows).
2. **Unzip** to Desktop.
3. **Put Photos**:
   - Reference photos -> `input/student_photos/<Name>/`
   - Class photos -> `input/class_photos/`
4. **Run**:
   - macOS: Double-click `SundayPhotoOrganizer.app` or `启动工具.sh`
   - Windows: Double-click `Launch_SundayPhotoOrganizer.bat`
5. **Done**: Check `output/` folder.

> See [Teacher Quick Start](doc/TeacherQuickStart_en.md) for details.

### 👨‍💻 For Developers (Python Mode)

1. **Clone & Install**:
   ```bash
   git clone ...
   cd sunday-photos
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Prepare Data**:
   - Create `input/student_photos` and `input/class_photos`.
   - Add some photos.

3. **Run**:
   ```bash
   python run.py
   ```

4. **Test**:
   ```bash
   python -m pytest
   ```

---

## ⚙️ Configuration (config.json)

Standard JSON doesn't support comments. To make config readable, we use `_comment` fields which are ignored by the program.

- **Config Reference (SSOT)**: [doc/CONFIG_REFERENCE_en.md](doc/CONFIG_REFERENCE_en.md)

(Note: Please refer to `CONFIG_REFERENCE_en.md` for all configuration details.)

---

## 📚 Documentation

> **Documentation Index**: [doc/INDEX_en.md](doc/INDEX_en.md)

- **User Guides**:
  - [Teacher Quick Start](doc/TeacherQuickStart_en.md) (3 steps)
  - [Teacher Guide](doc/TeacherGuide_en.md) (FAQ & Explanations)
- **Ops & Config**:
  - [Config Reference (SSOT)](doc/CONFIG_REFERENCE_en.md)
  - [Deployment Guide](doc/DeploymentGuide_en.md)
- **Development**:
  - [Developer Guide](doc/DeveloperGuide_en.md)
  - [Architecture Guide](doc/ArchitectureGuide_en.md)
  - [Testing Guide](doc/TESTING_en.md)
  - [Release Flow](doc/ReleaseFlow_en.md)

---

## 💡 Technical Highlights

- **Dual Engine**: Supports both `dlib` (classic) and `insightface` (modern, high accuracy).
- **Smart Parallelism**: Automatically switches between serial and parallel processing based on workload.
- **Robustness**: Designed to handle file system errors, encoding issues, and partial failures gracefully.
- **Teacher-Centric**: All technical complexity is hidden behind a simple "Input -> Run -> Output" workflow.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
