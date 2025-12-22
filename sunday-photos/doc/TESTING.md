# 测试指南 / Testing Guide

## 运行方式 / How to Run
- 全量回归 Full: `python run_all_tests.py`
- 单文件 Single: `python tests/test_teacher_onboarding_flow.py`
- 无交互阻塞: 测试入口已设置 `GUIDE_FORCE_AUTO=1`；非交互默认自动选择 / Non-interactive auto-select.

## 测试套件速览 / Suite Overview
- 基础与修复 Basics & Fixes
  - tests/test_basic.py
  - tests/test_fixes.py
  - tests/test_fixes_validation.py
- 集成与端到端 Integration & E2E
  - tests/test_integration.py
  - tests/test_all_teacher_features.py
- 教师友好 Teacher-friendly
  - tests/test_teacher_friendly.py
  - tests/test_teacher_help_system.py
  - tests/test_teacher_onboarding_flow.py
- 规模与打包 Scale & Packaging
  - tests/test_scalability_student_manager.py
  - tests/test_console_app.py
  - tests/test_packaged_app.py
- 旧版/简化 Legacy/Simple
  - tests/legacy/test_fixes_simple.py
- 边界测试 Edge cases
  - tests/test_edge_cases.py: 空目录、无参考、重复照片 / empty dirs, missing refs, duplicates.

## 常见问题 / FAQ
- face_recognition 告警：`pkg_resources is deprecated` 为上游噪声，可忽略 / upstream noise.
- 路径不存在：测试会自动创建 input/output；手动运行确保 CWD 为仓库根 / ensure repo root.
- 打包测试：test_console_app.py、test_packaged_app.py 需要打包产物；缺失会提示失败 / requires packaged artifacts.
