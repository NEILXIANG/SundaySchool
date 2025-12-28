# 开发与打包指南 (Developer Guide)

**版本**: v0.4.0  
**更新日期**: 2025-12-26

面向开发者与发布维护者，涵盖本地调试、架构说明、打包与 CI 工作流。

---

## 📋 目录
- [项目结构要点](#-项目结构要点)
- [本地开发与测试](#-本地开发与测试)
- [核心架构说明](#-核心架构说明)
- [本地打包](#-本地打包)
- [CI/CD工作流](#-cicd工作流)
- [配置与参数](#-配置与参数)
- [排错速览](#-排错速览)
- [发布流程](#-发布流程)

---

## 📁 项目结构要点

```
sunday-photos/
├── src/
│   ├── core/                    # 核心模块（业务逻辑）
│   │   ├── main.py              # 主流程编排
│   │   ├── face_recognizer.py   # 人脸识别引擎（多编码融合+缓存）
│   │   ├── file_organizer.py    # 文件整理（学生/日期分层）
│   │   ├── student_manager.py   # 学生管理（参考照加载）
│   │   ├── parallel_recognizer.py # 并行识别（多进程）
│   │   ├── incremental_state.py # 增量处理（快照对比）
│   │   ├── recognition_cache.py # 识别缓存（按日期分片）
│   │   ├── clustering.py        # 未知人脸聚类（v0.4.0）
│   │   ├── config_loader.py     # 配置加载器
│   │   └── utils.py             # 工具函数
│   ├── cli/                     # 命令行入口
│   │   └── run.py               # CLI主入口
│   └── ui/                      # 交互式界面（教师助手）
├── tests/                       # 自动化测试（用例数随迭代增长）
│   ├── test_basic.py            # 基础功能
│   ├── test_integration.py      # 集成测试
│   ├── test_console_app.py      # 打包验证
│   ├── test_recognition_cache.py # 缓存测试
│   └── ...
├── scripts/                     # 打包脚本
│   ├── build_mac_app.sh         # 构建/刷新控制台发布包（onedir，release_console/）
│   ├── build_mac_teacher_app.sh # 构建老师双击版（.app，release_mac_app/）
│   └── build_windows_console_app.ps1 # Windows控制台发布包（onedir）
├── release_console/             # 打包产物目录
│   ├── SundayPhotoOrganizer/     # 控制台发布包目录（onedir）
│   │   ├── SundayPhotoOrganizer     # macOS可执行文件（在目录内）
│   │   └── SundayPhotoOrganizer.exe # Windows可执行文件（在目录内）
│   ├── 启动工具.sh                # macOS 启动脚本（推荐入口，固定工作目录）
│   ├── Launch_SundayPhotoOrganizer.bat # Windows 启动脚本
│   ├── 使用说明.md                # 中文使用说明（md-only）
│   └── USAGE_EN.md              # English usage (md-only)
├── release_mac_app/             # macOS 老师双击版（.app + input/output/logs）
├── doc/                         # 项目文档
├── config.json                  # 配置文件（示例）
├── requirements.txt             # Python依赖
└── README.md                    # 项目说明
```

**关键说明**：
- `src/core/`：核心业务逻辑，独立于CLI和打包
- `src/cli/run.py`：命令行入口，调用 `core/main.py`
- `release_console/`：交付目录，包含可执行文件和启动脚本
- `tests/`：测试覆盖所有核心功能和边界情况

---

## 🛠️ 本地开发与测试

### 1. 环境准备

**系统要求**：
- Python 3.7 - 3.14（推荐 3.10+）
- macOS/Linux/Windows
- 4GB+ 内存
- (macOS) Xcode Command Line Tools
- (Windows) Visual C++ Build Tools

**创建虚拟环境**：
```bash
cd sunday-photos
python -m venv .venv

# 激活虚拟环境
source .venv/bin/activate          # macOS/Linux
.venv\\Scripts\\activate            # Windows PowerShell
```

**安装依赖**：
```bash
pip install -r requirements.txt
```

**验证安装**：
```bash
python -c "import insightface; print('✓ insightface installed')"
python -c "import onnxruntime; print('✓ onnxruntime installed')"
python -c "import cv2; print('✓ opencv installed')"

# 可选：若你要切换到 dlib/face_recognition 后端
# 先安装可选依赖：
#   pip install -r requirements-dlib.txt
# 再验证这两项
python -c "import face_recognition; print('✓ face_recognition installed')"
python -c "import dlib; print('✓ dlib installed')"
```

### 2. 运行与调试

**基础运行**：
```bash
python run.py
```

**带参数运行**：
```bash
python run.py --input-dir input --output-dir output --tolerance 0.6
```

**查看帮助**：
```bash
python run.py --help
```

**调试模式**（详细日志）：
```bash
# 修改 config.json
{
  "log_level": "DEBUG"
}

python run.py
```

**临时启用并行**：
```bash
SUNDAY_PHOTOS_PARALLEL=1 python run.py
```

**强制禁用并行**（排障）：
```bash
SUNDAY_PHOTOS_NO_PARALLEL=1 python run.py
```

### 3. 测试

**运行全部测试**：
```bash
python run_all_tests.py
```

**运行特定测试文件**：
```bash
python -m pytest tests/test_basic.py -v
python -m pytest tests/test_integration.py -v
```

**运行打包验证测试**（需先打包）：
```bash
# 先打包
bash scripts/build_mac_app.sh

# 再测试
REQUIRE_PACKAGED_ARTIFACTS=1 python -m pytest -q
# 或使用快捷方式
python run_all_tests.py --require-packaged-artifacts
```

**测试覆盖率**：
```bash
python -m pytest --cov=src tests/
```

---

## 🏗️ 核心架构说明

### 工作流管线

```
用户运行
   ↓
SimplePhotoOrganizer (src/core/main.py)
   ├─→ 1. initialize() - 初始化组件
   │      ├─→ StudentManager - 加载学生名册和参考照
   │      ├─→ FaceRecognizer - 提取参考照编码（带缓存）
   │      └─→ FileOrganizer - 准备输出目录
   ├─→ 2. scan_input_directory() - 扫描输入
   │      ├─→ _organize_input_by_date() - 按日期归档照片
   │      ├─→ load_snapshot() - 加载增量快照
   │      └─→ compute_incremental_plan() - 计算变更
   ├─→ 3. process_photos() - 人脸识别
   │      ├─→ load_date_cache() - 加载日期缓存
   │      ├─→ FaceRecognizer.recognize_faces() - 串行识别
   │      │   或 parallel_recognize() - 并行识别
   │      ├─→ UnknownClustering - 未知人脸聚类
   │      └─→ save_date_cache_atomic() - 保存缓存
   ├─→ 4. organize_output() - 整理输出
   │      ├─→ FileOrganizer.organize_photos() - 文件复制
   │      └─→ create_summary_report() - 生成报告
   └─→ 5. save_snapshot() - 保存增量快照
```

  ### 运行时序 / Orchestration（含回退路径）

  ```
  用户 → CLI/run.py
      → ServiceContainer.build()
      → SimplePhotoOrganizer.run()
        → initialize()
          → StudentManager.load_students()
          → FaceRecognizer.load_reference_encodings()
          → FileOrganizer.prepare_output()
        → scan_input_directory()
          → organize_input_by_date()  # 失败→记录警告并继续后续日期
          → load_snapshot()            # 读取失败→用空快照
          → compute_incremental_plan()
        → process_photos()
          → load_date_cache()          # 缓存损坏→忽略缓存
          → parallel_or_serial_recognize()
            → parallel失败→自动降级串行
          → UnknownClustering.run()
          → save_date_cache_atomic()
        → organize_output()
          → FileOrganizer.move_and_copy()
          → create_summary_report()
        → save_snapshot()
  ```

  **异常与返回语义（约定）**
  - 预期可恢复的场景（单张图片损坏、单个日期失败）：记录 warning/ error 日志，跳过当前文件/日期，不中断主流程。
  - 不可恢复的场景（输入目录不存在、输出目录无写权限）：向上抛出异常，由 CLI 层统一捕获并输出面向老师的提示。
  - 并行识别失败：自动降级串行，不抛出致命异常；在日志中标记 fallback 原因。
  - 缓存/快照损坏：忽略损坏文件，使用空缓存/快照继续执行，并记录 warning。
  - 所有跨模块异常需在日志中包含：发生位置、文件路径（如有）、下一步建议。

### 关键设计模式

**1. 依赖注入容器** (`ServiceContainer`)：
- 统一管理核心服务实例
- 便于测试时注入Mock对象
- 示例：
  ```python
  container = ServiceContainer(config)
  student_manager = container.get_student_manager()
  face_recognizer = container.get_face_recognizer()
  ```

**2. 增量处理**（隐藏状态快照）：
- 快照位置：`output/.state/class_photos_snapshot.json`
- 记录内容：每个日期文件夹的文件列表 + 元信息(size/mtime)
- 工作原理：
  ```python
  previous = load_snapshot(output_dir)
  current = build_class_photos_snapshot(class_photos_dir)
  plan = compute_incremental_plan(previous, current)
  # plan.changed_dates: 需要重新处理的日期
  # plan.deleted_dates: 需要删除的日期
  ```

**3. 分片识别缓存**：
- 位置：`output/.state/recognition_cache_by_date/YYYY-MM-DD.json`
- key: `CacheKey(date, rel_path, size, mtime)`
- value: 识别结果 dict（与 `recognize_faces(return_details=True)` 兼容）
- 失效机制：参数指纹变化（tolerance/min_face_size/参考照指纹）

**4. 参考照增量缓存**：
- 位置：`{log_dir}/reference_encodings/<engine>/<model>/*.npy`
- 内容：每张参考照的 face encoding（numpy数组）
- 快照：`{log_dir}/reference_index/<engine>/<model>.json`（记录 rel_path/size/mtime/status/cache 等元信息）
- 优势：参考照未变化时复用，提升 3-5倍 启动速度

**5. 未知人脸聚类**（v0.4.0）：
- 算法：贪婪聚类（O(n²)）
- 阈值：0.45（比识别阈值0.6更严格）
- 输出：`{cluster_name: [photo_paths]}`
- 应用：`FileOrganizer` 根据聚类结果创建 `Unknown_Person_X/日期` 目录

---

## 📦 本地打包

### macOS 打包

**基础打包**（当前架构）：
```bash
cd sunday-photos
bash scripts/build_mac_app.sh
```

**指定架构打包**：
```bash
# Intel芯片（x86_64）
TARGET_ARCH=x86_64 bash scripts/build_mac_app.sh

# Apple Silicon（M1/M2, ARM64）
TARGET_ARCH=arm64 bash scripts/build_mac_app.sh
```

**产物位置**：
- `release_console/SundayPhotoOrganizer/`（onedir 发布包目录）
  - 可执行文件：`release_console/SundayPhotoOrganizer/SundayPhotoOrganizer`
  - 启动脚本：`release_console/启动工具.sh`
- （可选）老师双击版：`release_mac_app/SundayPhotoOrganizer.app`

**打包原理**：
- 使用 PyInstaller 目录模式（onedir）
- 打包模式：目录（更稳定，便于携带依赖/资源；本项目发布口径统一用 onedir）
- 包含所有依赖（Python运行时 + face_recognition + dlib + models）
- 体积约 150-200MB

**仅刷新发布目录（不重新跑 PyInstaller）**：
```bash
SKIP_PYINSTALLER=1 bash scripts/build_mac_app.sh
```

### Windows 打包

**环境准备**：
- 安装 Visual C++ Build Tools
- 安装 CMake（dlib依赖）

**执行打包**：
```powershell
cd sunday-photos
powershell -ExecutionPolicy Bypass -File scripts\\build_windows_console_app.ps1
```

**产物位置**：
- `release_console/SundayPhotoOrganizer/`（onedir 发布包目录）
  - 可执行文件：`release_console/SundayPhotoOrganizer/SundayPhotoOrganizer.exe`
- `release_console/Launch_SundayPhotoOrganizer.bat`（启动脚本，防止闪退）

**注意事项**：
- PyInstaller不支持交叉编译（必须在Windows上打包Windows版）
- 首次打包可能较慢（需要收集/压缩依赖与模型；若选择 dlib 后端且本机无预编译 wheel，也可能涉及编译）

---

## 🤖 CI/CD工作流

### GitHub Actions 配置

**1. macOS 通用包（arm64 + x86_64）**：
- Workflow文件：`.github/workflows/macos-universal-bundle.yml`
- 触发方式：手动触发（`workflow_dispatch`）
- 产物名：`macos-universal`
- 路径：Artifact 解压后目录 `release_console_universal/`
- 说明：对老师仅暴露一个入口 `SundayPhotoOrganizer`；两套架构二进制在 `bin/` 下（`bin/SundayPhotoOrganizer-arm64`、`bin/SundayPhotoOrganizer-x86_64`），启动脚本会自动选择架构

**2. Windows x86_64 构建**：
- Workflow文件：`.github/workflows/windows-build.yml`
- Runner：`windows-latest`
- 触发方式：手动触发
- 产物名：`windows-x86_64`
- 依赖：安装 CMake

**触发方式**：
1. 进入GitHub仓库
2. 点击 "Actions"
3. 选择对应的 Workflow
4. 点击 "Run workflow"

**下载产物**：
1. Workflow运行完成后
2. 点击运行记录
3. 下载 Artifacts（macos-universal / windows-x86_64）

---

## ⚙️ 配置与参数

### 命令行参数（src/cli/run.py）

```bash
python run.py [OPTIONS]

Options:
  --input-dir PATH      输入目录（默认: input）
  --output-dir PATH     输出目录（默认: output）
  --log-dir PATH        日志目录（默认: logs）
  --tolerance FLOAT     识别阈值 0-1（默认: 0.6，越低越严格）
  --help                显示帮助信息
```

### 配置文件（config.json）

见 [doc/CONFIG.md](CONFIG.md) 获取完整配置说明。

### 环境变量

```bash
# 临时启用并行
SUNDAY_PHOTOS_PARALLEL=1

# 强制禁用并行（排障）
SUNDAY_PHOTOS_NO_PARALLEL=1

# 自定义配置文件路径
SUNDAY_PHOTOS_CONFIG=/path/to/config.json
```

---

## 🔧 排错速览

### 常见问题

**1. `ModuleNotFoundError: No module named 'face_recognition'`**
- 原因：未安装依赖
- 解决：`pip install -r requirements.txt`

**2. dlib 编译失败（Windows）**
- 原因：缺少 Visual C++ Build Tools 或 CMake
- 解决：
  1. 安装 Visual Studio Build Tools
  2. 安装 CMake
  3. 重新运行 `pip install dlib`

**3. 打包后运行闪退**
- 原因：缺少启动脚本或控制台输出被忽略
- 解决：使用启动脚本而非直接双击可执行文件
  - macOS: `启动工具.sh`
  - Windows: `Launch_SundayPhotoOrganizer.bat`

**4. 找不到 `requirements.txt`（CI）**
- 原因：工作目录不正确
- 解决：确保 `working-directory: sunday-photos`

**5. 程序秒退，无报错**
- 原因：输入目录为空
- 解决：检查 `input/student_photos/` 和 `input/class_photos/` 是否有文件
- 排查：查看 `logs/photo_organizer_*.log`

**6. 并行识别失败**
- 原因：进程通信问题或资源不足
- 解决：程序会自动回退串行模式，可通过日志查看原因
- 强制禁用：`SUNDAY_PHOTOS_NO_PARALLEL=1 python run.py`

---

## 🚀 发布流程

发布时序图（步骤 + 输入/输出文件）详见：
- [doc/ReleaseFlow.md](ReleaseFlow.md)（中文版）
- [doc/ReleaseFlow_en.md](ReleaseFlow_en.md)（English）

面向老师的极简说明（会随发布包一起提供）：
- [doc/TeacherQuickStart.md](TeacherQuickStart.md)
- [doc/TeacherQuickStart_en.md](TeacherQuickStart_en.md)

### 发布前检查清单

参考 [doc/ReleaseAcceptanceChecklist.md](ReleaseAcceptanceChecklist.md)

**核心检查项**：
1. ✅ 本地测试全部通过（以 `pytest -q` 结果为准）
2. ✅ 打包产物生成成功
3. ✅ 打包验证测试通过（`REQUIRE_PACKAGED_ARTIFACTS=1`）
4. ✅ 手动测试打包版（工作目录 / Work folder 模式）
5. ✅ 文档更新（README/PRD/CHANGELOG）
6. ✅ 版本号更新

### 发布步骤

**1. 本地验证**：
```bash
# 运行全套测试
python run_all_tests.py

# 打包（根据平台）
bash scripts/build_mac_app.sh  # macOS
# 或
powershell -ExecutionPolicy Bypass -File scripts\\build_windows_console_app.ps1  # Windows

# 打包验证测试
python run_all_tests.py --require-packaged-artifacts

# 手动测试打包版
cd release_console
./启动工具.sh  # macOS
# 或双击 Launch_SundayPhotoOrganizer.bat  # Windows
```

**2. 触发CI构建**：
- 进入GitHub Actions
- 运行两个 Workflow（macOS universal / Windows）
- 等待构建完成

**3. 下载并验证产物**：
- 下载 Artifacts（macos-universal / windows-x86_64）
- 解压并验证可执行文件
- 手动测试（放入测试照片，运行，查看输出）

**4. 打包发布**：
- 创建发布包（包含可执行文件 + 启动脚本 + 使用说明）
- 命名规范：`SundayPhotoOrganizer_v0.4.0_macOS_universal.zip`

**5. 发布说明**：
- 附带《老师使用指南》（中英文）
- 说明对应芯片/平台
- 提供快速开始步骤

---

## 📚 相关文档

- [项目README](../README.md) - 项目概览和快速开始
- [PRD](PRD.md) - 产品需求文档
- [配置说明](CONFIG.md) - config.json 详细说明
- [测试文档](TESTING.md) - 测试策略和用例
- [老师指南](TeacherGuide.md) - 打包版使用说明
- [发布检查清单](ReleaseAcceptanceChecklist.md) - 发布前验收

---

## 🎯 工程亮点总结

1. **架构设计**：依赖注入 + 分层设计 + 状态隔离
2. **性能优化**：增量处理 + 多级缓存 + 并行识别（小批量回退串行）
3. **容错机制**：多层异常捕获 + 自动回退 + 原子操作
4. **测试覆盖**：覆盖核心流程 + 打包验证 + 边界场景（以 `pytest -q` 输出为准）
5. **用户体验**：开箱即用 + 智能提示 + 友好错误
6. **跨平台支持**：Windows/macOS(x86+ARM)/Linux
7. **未知人脸聚类**：智能归组访客/家长/新学生

---

**💡 开发提示**：
- 修改核心逻辑后务必运行 `python run_all_tests.py`
- 提交前检查代码风格（推荐使用 black/flake8）
- 新增功能需补充测试用例
- 更新功能需同步更新文档
