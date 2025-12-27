# 测试指南 / Testing Guide

**版本**: v0.4.0  
**更新日期**: 2025-12-26

## 运行方式 / How to Run

### 快速入门
- **全量回归** Full: `python run_all_tests.py`
- **单文件** Single: `python tests/test_basic.py`
- **无交互阻塞**: 测试入口已设置 `GUIDE_FORCE_AUTO=1`；非交互默认自动选择

### 高级选项
- **并行运行**（更快）: `pytest -n auto`（需安装 `pytest-xdist`）
- **详细输出**: `pytest -v`
- **只运行失败用例**: `pytest --lf`
- **覆盖率报告**: `pytest --cov=src --cov-report=html`

## 测试套件速览 / Suite Overview

### 核心功能测试
- **基础与修复** Basics & Fixes
  - `tests/test_basic.py`: 基础流程、配置加载、输入验证
  - `tests/test_fixes.py`: Bug修复验证
  - `tests/test_fixes_validation.py`: 修复有效性检查
  
- **集成与端到端** Integration & E2E
  - `tests/test_integration.py`: 完整工作流测试
  - `tests/test_all_teacher_features.py`: 教师功能集成验证
  - `tests/test_comprehensive.py`: 综合场景覆盖

### 新功能测试（v0.4.0）
- **未知人脸聚类** Unknown Face Clustering
  - `tests/test_clustering.py`: 聚类算法单元测试
  - `tests/test_integration_clustering.py`: 聚类端到端流程
  - 验证点：
    - 贪心算法正确性
    - 阈值配置生效
    - 文件夹命名规范（Unknown_Person_X）
    - 单次出现人脸处理

### 性能与规模测试
- **并行识别** Parallel Recognition
  - `tests/test_parallel_recognizer.py`: 并行性能验证
  - `tests/test_recognition_cache.py`: 缓存机制测试
  
- **规模测试** Scalability
  - `tests/test_scalability_student_manager.py`: 大规模学生数据
  - `tests/test_large_dataset_generation.py`: 大批量照片处理

### 用户体验测试
- **教师友好** Teacher-friendly
  - `tests/test_teacher_friendly.py`: 开箱即用
  - `tests/test_teacher_help_system.py`: 帮助系统响应
  - `tests/test_teacher_onboarding_flow.py`: 首次使用流程

### 打包与部署测试
- **打包验证** Packaging
  - `tests/test_console_app.py`: 控制台版本测试
  - `tests/test_packaged_app.py`: 打包产物完整性
  - 注意：
    - 日常开发/CI：无打包产物时自动跳过（skip）
    - 发布验收：设置 `REQUIRE_PACKAGED_ARTIFACTS=1` 强制要求产物存在

### 边界与异常测试
- **边界测试** Edge Cases
  - `tests/test_edge_cases.py`: 空目录、无参考、重复照片等
  - `tests/test_network_testdata_builder.py`: 网络异常场景

## 测试覆盖范围 / Coverage

### 功能覆盖
- ✅ 人脸识别：匹配、聚类、缓存
- ✅ 文件管理：复制、移动、增量处理
- ✅ 配置系统：加载、验证、优先级
- ✅ 用户交互：命令行、自动化指导
- ✅ 打包部署：macOS/Windows可执行文件

### 场景覆盖
- ✅ 正常流程：完整工作流（参考照 → 课堂照 → 整理）
- ✅ 异常情况：空目录、缺失文件、格式错误
- ✅ 边界条件：大批量、单人、无人脸
- ✅ 性能场景：并行加速、缓存命中
- ✅ 用户体验：首次运行、帮助系统、错误提示

### 当前测试状态
- **总用例数**: 以 `pytest -q` 输出为准（持续增长）
- **通过率**: 100%
- **覆盖率**: 以 `pytest-cov` 报告为准（视口径与范围）

## 常见问题 / FAQ

### Q1: face_recognition 警告（仅当使用 dlib 后端时）
**现象**: `pkg_resources is deprecated`

**原因**: 可选后端 `face_recognition` 上游依赖 `pkg_resources`（已弃用）

**解决**: 
- 已在 `src/core/main.py` 中添加警告过滤
- 不影响功能，可忽略

### Q2: 路径不存在错误
**现象**: `FileNotFoundError: input/student_photos/`

**原因**: 测试临时目录未创建

**解决**:
- 测试会自动创建 `input/output` 目录
- 手动运行时确保 CWD 为仓库根目录: `cd sunday-photos`

### Q3: 打包测试跳过
**现象**: `test_console_app.py` 显示 "SKIPPED"

**原因**: 未构建打包产物（`release_console/` 为空）

**解决**:
- **日常开发**: 跳过是正常的，无需处理
- **发布验收**: 先运行 `bash scripts/build_mac_app.sh`，再设置环境变量:
  ```bash
  REQUIRE_PACKAGED_ARTIFACTS=1 python run_all_tests.py
  ```

### Q4: 聚类测试失败
**现象**: `test_integration_clustering.py` 断言失败

**原因**: 聚类阈值或测试数据配置不当

**解决**:
1. 检查 `config.json` 中 `unknown_face_clustering.threshold` 设置
2. 确认测试数据人脸质量（需清晰、正脸）
3. 查看 `logs/` 目录下最新日志定位问题

### Q5: 并行测试不稳定
**现象**: `test_parallel_recognizer.py` 偶尔失败

**原因**: 多进程竞争或内存不足

**解决**:
- 临时禁用并行: `SUNDAY_PHOTOS_NO_PARALLEL=1 pytest tests/test_parallel_recognizer.py`
- 减少并行度: 修改 `config.json` 中 `parallel_recognition.workers` 为 `2`

## 配置说明

详细配置字段与注释规则详见：
- **中文**: [CONFIG.md](CONFIG.md)
- **English**: [CONFIG_en.md](CONFIG_en.md)

## 持续集成 / CI

推荐 CI 配置（GitHub Actions 示例）:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.7', '3.8', '3.9', '3.10', '3.11']
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -r requirements.txt
      - run: python run_all_tests.py
```

## 发布验收清单 / Release Acceptance

在发布前，必须通过以下检查：
1. ✅ **全量测试**: `python run_all_tests.py` 100% 通过
2. ✅ **打包测试**: `REQUIRE_PACKAGED_ARTIFACTS=1 python run_all_tests.py` 通过
3. ✅ **手动验证**: 实际运行打包产物，测试核心流程
4. ✅ **文档审查**: 确认所有文档版本号已更新

详见: [ReleaseAcceptanceChecklist.md](ReleaseAcceptanceChecklist.md)

## 调试技巧 / Debugging Tips

### 1. 详细日志
```bash
pytest -v -s  # -s 显示 print 输出
```

### 2. 单步调试
```python
import pdb; pdb.set_trace()  # 在测试代码中设置断点
```

### 3. 保留测试数据
```python
# tests/conftest.py
@pytest.fixture
def temp_dir(tmp_path):
    yield tmp_path
    # 注释掉清理逻辑，保留测试数据
    # shutil.rmtree(tmp_path)
```

### 4. 查看实际输出
```bash
ls -la tests/test_output/  # 查看测试生成的文件
cat logs/sunday_photos_*.log  # 查看程序日志
```
