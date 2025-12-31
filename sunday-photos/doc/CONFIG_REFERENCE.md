# 配置参考手册（SSOT）

**版本**: v1.4.0  
**更新日期**: 2025-12-31

本文档是“主日学课堂照片自动整理工具”（sunday-photos）的配置**单一事实来源 (SSOT)**：

- 哪些配置真的生效
- 生效优先级是什么
- 常用场景怎么配（带例子）

> 老师侧默认原则：老师不需要改配置。配置只面向维护者/技术同工。

---

## 0) 一句话先说明：什么叫 Work folder？

- **Work folder** 是程序读写 `input/ output/ logs/ config.json` 的“根目录”。
- 打包版默认优先使用“可执行文件同目录”；若不可写会回退到 Desktop/Home，并在控制台打印：`Work folder: ...`（以这行输出为准）。
- 维护者可用环境变量 **强制指定 Work folder**：`SUNDAY_PHOTOS_WORK_DIR=/path/to/work`。

---

## 1) 配置来源与优先级（权威口径）

生效优先级（从高到低）：

1. **命令行参数（CLI）**：如 `--input-dir --output-dir --tolerance --no-parallel`
2. **环境变量（Env）**：仅少数“运行态开关”支持（见第 3 节）
3. **配置文件（config.json）**：默认在 Work folder 根目录
4. **内置默认值**：见 `src/core/config.py`

说明：并不是所有配置都有“环境变量对应项”。本项目目前只有部分开关提供 env override（例如后端切换、并行开关、Work folder、诊断输出等）。

---

## 2) config.json 字段（真正会被读取的）

> 允许在 `config.json` 中使用 `_comment` / `*_comment` 字段作为说明文字；程序会忽略这些字段。

### 2.1 路径（Paths）

| 配置键 (JSON) | CLI 参数 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `input_dir` | `--input-dir` | `input` | 输入根目录（其下应包含 `student_photos/` 与 `class_photos/`）。 |
| `output_dir` | `--output-dir` | `output` | 输出根目录（包含按学生/日期分层 + 报告 + `.state/`）。 |
| `log_dir` | N/A | `logs` | 日志目录（参考照缓存与索引也在这里）。 |

提示：路径可为相对路径（相对 Work folder）或绝对路径。

### 2.2 识别阈值与最小人脸

| 配置键 (JSON) | CLI 参数 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `tolerance` | `--tolerance` | `0.6` | 匹配阈值（越小越严格）。老师端不建议改；技术同工排障时可临时改。 |
| `min_face_size` | N/A | `50` | 最小人脸像素近似值。过大可能漏人脸；过小可能误检。 |

兼容说明（历史字段）：

- `face_recognition.tolerance` / `face_recognition.min_face_size` 仍被支持。
- **当且仅当** 顶层字段未显式设置时，程序会把 `face_recognition.*` 提升为顶层生效。

### 2.3 人脸后端（Face backend）

| 配置键 (JSON) | 默认值 | 说明 |
| :--- | :--- | :--- |
| `face_backend.engine` | `insightface` | 可选：`insightface`（默认/推荐）、`dlib`（可选，需安装 `requirements-dlib.txt`）。 |

注意：环境变量 `SUNDAY_PHOTOS_FACE_BACKEND` 的优先级高于 config.json（见第 3 节）。

### 2.4 并行识别（Parallel recognition）

| 配置键 (JSON) | 默认值 | 说明 |
| :--- | :--- | :--- |
| `parallel_recognition.enabled` | `true` | 是否允许并行（满足阈值才会真正并行）。 |
| `parallel_recognition.workers` | `6` | 并行进程数。项目策略为“稳定优先”，默认不会自动拉高。 |
| `parallel_recognition.chunk_size` | `12` | 每个批次包含的照片数。 |
| `parallel_recognition.min_photos` | `30` | 仅当待处理照片数 ≥ 该值，才会尝试并行。 |

环境变量可以强制关闭/开启并行（见第 3 节）。CLI 参数 `--no-parallel` 也会强制禁用。

### 2.5 未知人脸聚类（Unknown face clustering）

| 配置键 (JSON) | 默认值 | 说明 |
| :--- | :--- | :--- |
| `unknown_face_clustering.enabled` | `true` | 是否启用未知人脸聚类。 |
| `unknown_face_clustering.threshold` | `0.45` | 聚类阈值（建议比 `tolerance` 更严格）。 |
| `unknown_face_clustering.min_cluster_size` | `2` | 仅当聚类数 ≥ 该值才创建 `Unknown_Person_X/`。 |

---

## 3) 环境变量（只列“真的会生效”的）

> 这些主要给维护者/排障用；不要要求老师手动设置。

| 环境变量 | 示例 | 用途 |
| :--- | :--- | :--- |
| `SUNDAY_PHOTOS_WORK_DIR` | `/Users/teacher/Desktop/SundayPhotoOrganizer` | 强制指定 Work folder 根目录（便携/演示/权限受限时很有用）。 |
| `SUNDAY_PHOTOS_FACE_BACKEND` | `insightface` / `dlib` | 覆盖人脸后端选择（优先级高于 config.json）。 |
| `SUNDAY_PHOTOS_NO_PARALLEL` | `1` | 强制禁用并行（排障/低内存机器）。 |
| `SUNDAY_PHOTOS_PARALLEL` | `1` | 强制启用并行（在 `parallel_recognition.enabled=true` 的基础上进一步确保开启）。 |
| `SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS` | `0` | 覆盖并行启用阈值。 |
| `SUNDAY_PHOTOS_DIAG_ENV` | `1` | 输出更多诊断信息（适合 CI/排障）。 |
| `SUNDAY_PHOTOS_PRINT_DIAG` | `1` | 启动器/HUD 打印诊断摘要（侧重点不同）。 |
| `SUNDAY_PHOTOS_TEACHER_MODE` | `1` | 教师模式（更克制的输出与行为，避免噪声）。 |
| `SUNDAY_PHOTOS_INSIGHTFACE_HOME` | `/path/to/.insightface` | 指定 InsightFace 模型目录（离线/便携部署）。 |
| `SUNDAY_PHOTOS_INSIGHTFACE_MODEL` | `buffalo_l` | 指定 InsightFace 模型名（默认 `buffalo_l`）。 |
| `SUNDAY_PHOTOS_QUIET_MODELS` | `1` | 控制模型加载相关日志是否更安静。 |

---

## 4) 常用场景示例（可直接复制）

### 4.1 源码模式：指定输入输出目录

```bash
python src/cli/run.py --input-dir input --output-dir output
```

### 4.2 排障：强制串行（避免多进程问题）

macOS/Linux:

```bash
SUNDAY_PHOTOS_NO_PARALLEL=1 python src/cli/run.py
```

Windows PowerShell:

```powershell
$env:SUNDAY_PHOTOS_NO_PARALLEL = "1"
python src\cli\run.py
```

### 4.3 切换到 dlib 后端（仅技术同工/维护者）

```bash
SUNDAY_PHOTOS_FACE_BACKEND=dlib python src/cli/run.py
```

### 4.4 离线/便携：指定 Work folder 与 InsightFace 模型目录

```bash
SUNDAY_PHOTOS_WORK_DIR=/path/to/work \
SUNDAY_PHOTOS_INSIGHTFACE_HOME=/path/to/insightface_home \
python src/cli/run.py
```

---

## 5) 相关文档

- 老师快速开始：`doc/TeacherQuickStart.md` / `doc/TeacherQuickStart_en.md`
- 老师指南：`doc/TeacherGuide.md` / `doc/TeacherGuide_en.md`
- 测试指南：`doc/TESTING.md` / `doc/TESTING_en.md`
- 开发与打包：`doc/DeveloperGuide.md` / `doc/DeveloperGuide_en.md`
