# 发布验收清单（Release Acceptance Checklist）
**版本**: v0.4.0  
**更新日期**: 2026-01-02
目的：确保“老师可用的发布包”在交付前通过强校验，避免出现：可执行文件缺失、说明不一致、运行后找不到目录、老师不知道下一步怎么做。

适用范围：
- 你准备把 `release_console/` 整个文件夹发给老师使用时。

---

## A. 必备产物

在 `sunday-photos/release_console/` 下必须存在（按平台）：

- macOS：
  - `SundayPhotoOrganizer`（macOS 控制台可执行文件）
  - `启动工具.sh`（双击入口脚本，或老师按照说明运行）
- Windows：
  - `SundayPhotoOrganizer.exe`（Windows 控制台可执行文件）
  - `Launch_SundayPhotoOrganizer.bat`（双击入口脚本，保持窗口不闪退）
- 通用：
  - `README.md`（老师版简明说明，默认无需参数的口径；详细文档见 doc/）
  - `README_EN.md`（英文简明说明，可选）

可选（占位/示例目录；老师实际使用程序同级目录下的 `input/`、`output/`、`logs/`）：
- `input/`（如需提供源码模式示例，可包含 `student_photos/`、`class_photos/`）
- `output/`（可为空）
- `logs/`（可为空）

验收点：
- macOS：可执行文件具备执行权限；能正常启动。
- Windows：可执行文件能正常启动；.bat 启动脚本能拉起程序且不会秒退。

---

## B. 运行行为（老师端默认无需参数）

首次运行：
- 在程序同级创建 `input/`、`output/`、`logs/`；若不可写则回退桌面（或主目录）。
  - 以控制台打印的 `Work folder:` 为准。
- 自动创建/确认以下子目录存在：
  - `student_photos/`、`class_photos/`、`output/`、`logs/`
- 若缺少必要照片：
  - 输出必须是“通俗易懂的描述 + 下一步怎么做 + 日志在哪里”
  - 程序应安全退出（不产生误删/误移动）

缺少学生参考照（允许继续）：
- student_photos 可以暂时为空，程序仍可继续整理。
- 验收点：必须明确提示“课堂照片会全部归入 unknown”，并给出“如何补参考照提升准确度”的下一步。

缺少课堂照片（必须退出）：
- class_photos 为空时应提示下一步并安全退出。

正常整理：
- 处理完成后，提示“已完成 + 输出在哪里”。
- 尽可能自动打开 `output/`；如果自动打开失败，也必须视为成功（不应因此返回失败）。

日期分组/移动：
- 若程序会把课堂照移动到 `YYYY-MM-DD/`：必须提前在输出或说明中解释“这是正常现象”。

识别不准：
- 只允许给“三步法”建议：
  1) 补清晰正脸参考照
  2) 参考照不要多人合照
  3) 课堂照尽量清晰明亮
- 不允许要求老师调参、改阈值、编辑配置文件。

---

## C. 错误闭环（求助友好）

任何错误提示必须包含：
- 发生了什么（面向老师）
- 下一步怎么做（具体动作）
- 日志位置（让老师能把最新日志发给你）

验收点：
- 发生错误时 `logs/` 里确实有最新日志文件。

---

## D. 一键验收（开发者侧）

推荐验收顺序：
1) 构建打包产物（macOS）：
   - 使用仓库内脚本构建，并确认产物落到 `release_console/`。
  - Windows 产物需在 Windows 上构建（PyInstaller 不支持跨平台交叉编译）。
2) 严格模式跑测试（要求打包产物存在）：
   - 在 VS Code 里运行任务：`release acceptance (build + require packaged artifacts)`
   - 或使用等价命令（见仓库测试说明）。

通过标准：
- 严格模式 pytest 全绿。
- `release_console/` 内产物齐全，手工试运行符合 B/C。

并行识别/未知聚类关键路径（自动化覆盖）：
- 并行识别异常时自动回退串行：`tests/test_e2e_parallel_and_clustering.py::test_e2e_parallel_recognize_fallback_to_serial`
- 并行识别成功路径（不走回退）：`tests/test_e2e_parallel_and_clustering.py::test_e2e_parallel_recognize_success_path`
- unknown_face_clustering enabled 的落盘行为：`tests/test_e2e_parallel_and_clustering.py::test_e2e_unknown_face_clustering_enabled`

---

## E. 人工快速抽检（发给老师前 2 分钟）

- 双击运行入口（可执行文件或启动脚本）一次
- 确认工作目录创建成功（默认在程序同级；若不可写会回退到桌面/主目录）
- 确认 `input/`、`output/`、`logs/` 目录创建成功
- 随便放 1-2 张照片模拟输入，确认不会崩溃
- 确认 output/ 有结果或有明确提示
- 确认 logs/ 生成日志

开发者命令（可选）：
- 全量回归：`python3 -m pytest -q`
- 仅验证并行识别/聚类相关 e2e：`python3 -m pytest -q tests/test_e2e_parallel_and_clustering.py`
