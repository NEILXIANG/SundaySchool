# SundayPhotoOrganizer

<div align="center">

**🎉 专为教会主日学设计的自动照片整理工具**

*让老师专注教学，让技术处理琐事*

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)](tests/)

[特性](#-核心特性) • [文档导航](#-文档导航) • [English](README_en.md)

</div>

---

## 📖 项目简介

这是一个专为教会主日学场景设计的照片智能整理工具。通过人脸识别技术，自动将课堂合照按学生分类整理，让照片管理从"手工分类"变成"一键完成"。

---

## 🚀 文档导航

**我是老师，想快速开始** 👇  
[老师快速开始](doc/TeacherQuickStart.md)（3 步完成）

**我想了解更多用法** 👇  
[老师完整指南](doc/TeacherGuide.md)（常见问题、最佳实践）

**我是开发者，想贡献代码** 👇  
[开发指南](doc/DeveloperGuide.md)（本地开发、打包步骤）

**我需要理解项目架构** 👇  
[架构指南](doc/ArchitectureGuide.md)（设计原理、模块说明）

**我需要配置和参考手册** 👇  
[配置参考](doc/CONFIG_REFERENCE.md)（所有参数详解、环境变量、优先级）

**我是运维维护者，要发布** 👇  
[发布流程](doc/ReleaseFlow.md)（打包步骤、CI/CD 工作流）

**我需要示例和检查清单** 👇  
[示例库](doc/EXAMPLES.md) | [常见问题](doc/FAQ.md) | [健康检查](doc/HealthCheck_Runtime.md)

**我找不到需要的文档** 👇  
[完整文档索引](doc/INDEX.md)（所有文档索引和治理规则）

---

## ⭐ 核心特性

- 🧠 **智能识别**：InsightFace 多编码融合，自动选择最佳匹配。
- ⚡ **高效处理**：并行识别 + 增量处理 + 分片缓存。
- 🛡️ **智能容错**：异常自动降级，确保流程完成。
- 📊 **专业输出**：自动生成统计报告，未知人脸智能聚类。
- 🎨 **开箱即用**：双击运行，首次自动创建工作目录。

---

## 📁 目录结构示例

详细目录结构说明请参考 [EXAMPLES.md](doc/EXAMPLES.md)。

```
Work folder/
├── input/                    # 照片源
│   ├── student_photos/       # 学生参考照
│   └── class_photos/         # 课堂照
├── output/                   # 整理结果
└── logs/                     # 运行日志
```
