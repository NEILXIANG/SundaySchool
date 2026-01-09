# SundayPhotoOrganizer

<div align="center">

**🎉 专为教会主日学设计的自动照片整理工具**

*让老师专注教学，让技术处理琐事*

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)](tests/)

[快速开始](#-快速开始) • [特性](#-核心特性) • [文档导航](#-文档导航) • [English](README_en.md)

</div>

---

## 📖 项目简介

这是一个专为教会主日学场景设计的照片智能整理工具。通过人脸识别技术，自动将课堂合照按学生分类整理，让照片管理从"手工分类"变成"一键完成"。

---

## 🚀 快速开始

### 方式一：打包版（推荐给老师）
无需安装 Python，下载后直接运行：

1. 下载最新 [Release](https://github.com/NEILXIANG/SundaySchool/releases)
2. 解压后双击运行：
   - **macOS**: `SundayPhotoOrganizer.app` 或 `启动工具.sh`
   - **Windows**: `Launch_SundayPhotoOrganizer.bat`
3. 程序会显示 `Work folder` 路径，将照片放入：
   - 学生参考照 → `input/student_photos/<学生名>/`
   - 课堂照片 → `input/class_photos/`
4. 再次运行，结果自动出现在 `output/`

详细说明请看：[老师快速开始](sunday-photos/doc/TeacherQuickStart.md)

### 方式二：从源码运行（开发者）
```bash
# 克隆仓库
git clone https://github.com/NEILXIANG/SundaySchool.git
cd SundaySchool/sunday-photos

# 创建虚拟环境
python -m venv ../.venv
source ../.venv/bin/activate  # Windows: ..\.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行（教师模式）
python run.py
```

首次运行会自动创建 `input/`、`output/`、`logs/` 目录。

---

## 🛠️ 技术栈

- **Python** 3.8+ (推荐 3.10+)
- **InsightFace** 0.7+ (buffalo_l 模型，离线可用)
- **OpenCV** 4.x (图像处理)
- **ONNX Runtime** (跨平台推理引擎，CPU 版本)
- **scikit-learn** (人脸聚类)
- **PyInstaller** 6.x (打包为可执行文件)

---

## 🚀 文档导航

**我是老师，想快速开始** 👇  
[老师快速开始](sunday-photos/doc/TeacherQuickStart.md)（3 步完成）

**我想了解更多用法** 👇  
[老师完整指南](sunday-photos/doc/TeacherGuide.md)（常见问题、最佳实践）

**家长关心隐私与是否联网** 👇  
[隐私与离线处理说明（面向家长）](sunday-photos/doc/Privacy_Notice.md)（可直接转发/打印）

**Privacy & Offline Notice (for parents)** 👇  
[Privacy & Offline Processing Notice (For Parents)](sunday-photos/doc/Privacy_Notice_en.md)

**我是开发者，想贡献代码** 👇  
[开发指南](sunday-photos/doc/DeveloperGuide.md)（本地开发、打包步骤）

**我需要理解项目架构** 👇  
[架构指南](sunday-photos/doc/ArchitectureGuide.md)（设计原理、模块说明）

**我需要配置和参考手册** 👇  
[配置参考](sunday-photos/doc/CONFIG_REFERENCE.md)（所有参数详解、环境变量、优先级）

**我是运维维护者，要发布** 👇  
[发布流程](sunday-photos/doc/ReleaseFlow.md)（打包步骤、CI/CD 工作流）

**我需要示例和检查清单** 👇  
[示例库](sunday-photos/doc/EXAMPLES.md) | [常见问题](sunday-photos/doc/FAQ.md) | [健康检查](sunday-photos/doc/HealthCheck_Runtime.md)

**我找不到需要的文档** 👇  
[完整文档索引](sunday-photos/doc/INDEX.md)（所有文档索引和治理规则）

---

## ⭐ 核心特性

- 🧠 **智能识别**：InsightFace 多编码融合，自动选择最佳匹配。
- ⚡ **高效处理**：并行识别 + 增量处理 + 分片缓存。
- 🛡️ **智能容错**：异常自动降级，确保流程完成。
- 📊 **专业输出**：自动生成统计报告，未知人脸智能聚类。
- 🎨 **开箱即用**：双击运行，首次自动创建工作目录。

---

## 📁 目录结构

详细目录结构说明请参考 [EXAMPLES.md](sunday-photos/doc/EXAMPLES.md)。

```
SundaySchool/
├── sunday-photos/            # 主项目目录
│   ├── src/                  # 源代码
│   ├── tests/                # 测试用例
│   ├── doc/                  # 完整文档
│   ├── scripts/              # 构建脚本
│   ├── config.json           # 配置文件
│   └── run.py                # 启动入口
│
├── Work folder/              # 运行时工作目录（示例）
│   ├── input/
│   │   ├── student_photos/   # 学生参考照
│   │   └── class_photos/     # 课堂照
│   ├── output/               # 整理结果
│   └── logs/                 # 运行日志
```

---

## 📝 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请参考 [开发指南](sunday-photos/doc/DeveloperGuide.md)。
