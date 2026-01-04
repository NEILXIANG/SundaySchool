# Sunday School Photo Organizer

<div align="center">

**🎉 Intelligent Photo Organizer Designed for Teachers**

*Let teachers focus on teaching, let technology handle the chores*

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)](tests/)

[Quick Start](#-quick-start) • [Features](#-core-features) • [Documentation](#-documentation) • [中文](README.md)

</div>

---

## 📖 Introduction

This is an intelligent photo organization tool designed for Sunday schools. Using advanced face recognition technology, it automatically sorts class photos by student, freeing teachers from hours of manual sorting.

---

## 🚀 Quick Start

### Option 1: Pre-built Release (For Teachers)
No Python installation required:

1. Download the latest [Release](https://github.com/NEILXIANG/SundaySchool/releases)
2. Unzip and run:
   - **macOS**: Double-click `SundayPhotoOrganizer.app` or `启动工具.sh`
   - **Windows**: Double-click `Launch_SundayPhotoOrganizer.bat`
3. The app shows `Work folder` path. Put photos into:
   - Student reference photos → `input/student_photos/<student_name>/`
   - Class photos → `input/class_photos/`
4. Run again, results appear in `output/`

See detailed guide: [Teacher Quick Start](sunday-photos/doc/TeacherQuickStart_en.md)

### Option 2: Run from Source (For Developers)
```bash
# Clone repository
git clone https://github.com/NEILXIANG/SundaySchool.git
cd SundaySchool/sunday-photos

# Create virtual environment
python -m venv ../.venv
source ../.venv/bin/activate  # Windows: ..\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run (teacher mode)
python run.py
```

First run auto-creates `input/`, `output/`, `logs/` directories.

---

## 🛠️ Tech Stack

- **Python** 3.8+ (3.10+ recommended)
- **InsightFace** 0.7+ (buffalo_l model, offline-ready)
- **OpenCV** 4.x (image processing)
- **ONNX Runtime** (cross-platform inference, CPU version)
- **scikit-learn** (face clustering)
- **PyInstaller** 6.x (bundling executables)

---

## 🚀 Documentation

**For Teachers (Quick Start)** 👇  
[Teacher Quick Start](sunday-photos/doc/TeacherQuickStart_en.md) (3 steps)

**For Teachers (Full Guide)** 👇  
[Teacher Guide](sunday-photos/doc/TeacherGuide_en.md) (FAQ, Best Practices)

**For Developers** 👇  
[Developer Guide](sunday-photos/doc/DeveloperGuide_en.md) (Setup, Build)

**For Architecture** 👇  
[Architecture Guide](sunday-photos/doc/ArchitectureGuide_en.md) (Design, Modules)

**For Configuration** 👇  
[Config Reference](sunday-photos/doc/CONFIG_REFERENCE_en.md) (Parameters, Env Vars)

**For Release Managers** 👇  
[Release Flow](sunday-photos/doc/ReleaseFlow_en.md) (Packaging, CI/CD)

**Examples & Checklists** 👇  
[Examples](sunday-photos/doc/EXAMPLES_en.md) | [FAQ](sunday-photos/doc/FAQ_en.md) | [Health Check](sunday-photos/doc/HealthCheck_Runtime_en.md)

**Full Index** 👇  
[Documentation Index](sunday-photos/doc/INDEX_en.md)

---

## ⭐ Core Features

- 🧠 **Intelligent Recognition**: InsightFace with multi-encoding fusion.
- ⚡ **High Performance**: Parallel processing + Incremental updates + Caching.
- 🛡️ **Fault Tolerance**: Graceful degradation on errors.
- 📊 **Professional Output**: Auto-generated reports, Unknown face clustering.
- 🎨 **Out of the Box**: Zero-config start, auto-creates directories.

---

## 📁 Directory Structure

For detailed structure, see [EXAMPLES_en.md](sunday-photos/doc/EXAMPLES_en.md).

```
SundaySchool/
├── sunday-photos/            # Main project
│   ├── src/                  # Source code
│   ├── tests/                # Test cases
│   ├── doc/                  # Full documentation
│   ├── scripts/              # Build scripts
│   ├── config.json           # Configuration
│   └── run.py                # Entry point
│
├── Work folder/              # Runtime workspace (example)
│   ├── input/
│   │   ├── student_photos/   # Reference photos
│   │   └── class_photos/     # Class photos
│   ├── output/               # Organized results
│   └── logs/                 # Runtime logs
```

---

## 📝 License

This project is licensed under the [MIT License](LICENSE).

---

## 🤝 Contributing

Issues and Pull Requests are welcome! See [Developer Guide](sunday-photos/doc/DeveloperGuide_en.md).
