# 测试指南

本项目已经收敛到统一的 `tests/` 目录，便于老师和开发者快速运行与定位测试。

## 运行方式

- 全量回归：`python run_all_tests.py`
- 单文件示例：`python tests/test_teacher_onboarding_flow.py`
- 避免交互阻塞：测试入口自动设置 `GUIDE_FORCE_AUTO=1`；非交互环境下会自动选择默认选项。

## 测试套件速览

- 基础与修复
  - [tests/test_basic.py](../tests/test_basic.py)
  - [tests/test_fixes.py](../tests/test_fixes.py)
  - [tests/test_fixes_validation.py](../tests/test_fixes_validation.py)
- 集成与端到端
  - [tests/test_integration.py](../tests/test_integration.py)
  - [tests/test_all_teacher_features.py](../tests/test_all_teacher_features.py)
- 教师友好场景（零基础保护）
  - [tests/test_teacher_friendly.py](../tests/test_teacher_friendly.py)
  - [tests/test_teacher_help_system.py](../tests/test_teacher_help_system.py)
  - [tests/test_teacher_onboarding_flow.py](../tests/test_teacher_onboarding_flow.py)
- 规模与打包验证
  - [tests/test_scalability_student_manager.py](../tests/test_scalability_student_manager.py)
  - [tests/test_console_app.py](../tests/test_console_app.py)
  - [tests/test_packaged_app.py](../tests/test_packaged_app.py)
- 旧版/简化检查
  - [tests/legacy/test_fixes_simple.py](../tests/legacy/test_fixes_simple.py)

## 常见问题

- face_recognition 相关告警：`pkg_resources is deprecated` 属于上游包警告，可忽略运行结果（已在stderr出现）。
- 路径/目录不存在：测试会自动创建 `input/`、`output/` 等目录；若手动运行请确保当前工作目录是项目根目录。
- 打包测试：`tests/test_console_app.py` 和 `tests/test_packaged_app.py` 依赖打包产物是否存在；若未打包会提示缺少文件并返回失败。
