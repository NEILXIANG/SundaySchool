# 开发与打包指南

面向开发者与发布维护者，涵盖本地调试、打包与 CI 工作流。

## 项目结构要点
- 核心代码：`sunday-photos/src/`（入口 `src/cli/run.py`，核心逻辑 `src/core/`）。
- 打包脚本：`sunday-photos/scripts/build_mac_app.sh`（macOS 控制台 onefile，可读 `TARGET_ARCH`）。
- 发布目录：`sunday-photos/release_console/`（可执行文件 `SundayPhotoOrganizer` + 启动脚本 + 使用说明）。
- Windows 产物：交付目录为 `sunday-photos/release_console/`（`SundayPhotoOrganizer.exe` + `Launch_SundayPhotoOrganizer.bat`）；`sunday-photos/dist/` 仅为 PyInstaller 的中间产物目录。

## 本地开发与测试
1) Python 3.14，推荐使用虚拟环境：
   ```bash
   cd sunday-photos
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
2) 运行帮助/自测：
   ```bash
   python src/cli/run.py --help
   python src/cli/run.py --input-dir input --output-dir output --tolerance 0.6
   ```
3) 目录自动创建：运行时会确保 `input/class_photos`、`input/student_photos`、`output`、`logs` 存在。

## 本地打包（macOS）
```bash
cd sunday-photos
bash scripts/build_mac_app.sh          # 默认当前架构 onefile，输出到 release_console/
TARGET_ARCH=x86_64 bash scripts/build_mac_app.sh
TARGET_ARCH=arm64  bash scripts/build_mac_app.sh
```
产物：`release_console/SundayPhotoOrganizer`（onefile 可执行文件）。

## 本地打包（Windows）
在 Windows 上使用 PowerShell 运行（PyInstaller 不支持跨平台交叉编译）：
```powershell
cd sunday-photos
powershell -ExecutionPolicy Bypass -File scripts\build_windows_console_app.ps1
```
产物：`release_console/SundayPhotoOrganizer.exe`（onefile 可执行文件）。

> 说明：旧版本可能是 onedir 结构 `release_console/SundayPhotoOrganizer/SundaySchool`；当前脚本输出为 onefile。

## GitHub Actions 工作流
- macOS x86_64: `.github/workflows/macos-x86-build.yml`（runner macos-12，产物名 `macos-x86_64`，路径 `sunday-photos/release_console/`）。
- macOS arm64: `.github/workflows/macos-arm-build.yml`（runner macos-14，产物名 `macos-arm64`，路径同上）。
- Windows x86_64: `.github/workflows/windows-build.yml`（runner windows-latest，产物名 `windows-x86_64`，路径 `sunday-photos/release_console/`）。
- 触发：`workflow_dispatch` 手动；进入对应 workflow 页面点击 “Run workflow”。

## 配置与参数
- 主要入口参数（`src/cli/run.py`）：`--input-dir`、`--output-dir`、`--tolerance`（默认 0.6，越低越严格）。
- 配置常量：见 `src/config.py` / `src/core/config.py`。

## 模型与体积注意
- `face_recognition_models` 含 ~95MB 模型文件（GitHub 会提示大文件，必要时可迁移至 Git LFS 或改为运行时下载）。
- onedir 打包包含 Python 与依赖，包体较大但启动较快；onefile 压缩小但启动慢（Windows 当前用 onefile）。

## 排错速览
- 找不到 `requirements.txt`：确保工作目录为 `sunday-photos`（CI 已设置 working-directory）。
- dlib/numpy 构建失败（Windows）：安装 VC Build Tools，或使用官方预编译轮子；必要时 pin 版本。确认 `cmake` 已安装（CI 已安装）。
- 运行秒退：检查 `input/class_photos` 是否有图片；查看 `logs/photo_organizer_*.log` 获取原因。

## 发布流程建议
1) 本地确认功能与文案（`python src/cli/run.py --help`）。
2) 触发 Actions：运行 macOS x86_64 / macOS arm64 / Windows build。
3) 下载对应 artifact（macos-x86_64、macos-arm64、windows-x86_64），解压后发给老师/用户。
4) 若需对外发布，附带《老师使用指南》并说明对应芯片包。
