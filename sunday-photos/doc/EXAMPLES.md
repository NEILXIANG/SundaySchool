# 示例库（权威示例集合）

**版本**: v0.4.0  
**更新日期**: 2026-01-02

本文档是所有示例、配置、目录结构的**单一事实来源（SSOT）**。其他文档中的示例应该引用这里，而不是复制粘贴。

---

## 目录

1. [input 目录结构](#1-input-目录结构)
2. [output 目录结构](#2-output-目录结构)
3. [配置文件示例](#3-配置文件示例)
4. [命令行示例](#4-命令行示例)
5. [环境变量示例](#5-环境变量示例)

---

## 1. input 目录结构

### 1.1 标准结构（推荐）

```
input/
├── student_photos/                   # 学生参考照（强制：每个学生一个文件夹）
│   ├── Alice/                        # 学生名称作为文件夹名
│   │   ├── ref_01.jpg                # 参考照 1
│   │   ├── ref_02.jpg                # 参考照 2
│   │   └── ref_03.png                # 也支持 PNG
│   ├── Bob/
│   │   ├── photo_001.jpg
│   │   └── photo_002.jpg
│   └── 小名/                         # 支持中文名称
│       └── ref_01.jpg
└── class_photos/                     # 课堂照（建议按日期建子目录）
    ├── 2026-01-01/                   # 日期子目录（推荐格式）
    │   ├── classroom_photo_001.jpg
    │   ├── classroom_photo_002.jpg
    │   └── group_activity.png
    ├── 2026-01-02/
    │   └── more_photos.jpg
    └── loose_photo.jpg               # 也支持直接放根目录（程序会自动按日期归档）
```

**说明**:
- ✅ 学生名称可以是中文或英文
- ✅ 每个学生 2-5 张清晰正脸参考照效果最佳
- ✅ 课堂照建议按 `YYYY-MM-DD` 或 `YYYY_MM_DD` 建子目录
- ✅ 如果不建子目录，程序会自动分析日期并创建
- ✅ 支持的图片格式：jpg, jpeg, png, bmp, tiff, webp

### 1.2 支持的日期格式

程序可以自动识别以下日期格式，自动移动课堂照到对应日期文件夹：

| 格式 | 示例 | 识别方式 |
|-----|------|--------|
| ISO 标准 | `2026-01-02/` | ✅ 推荐 |
| 下划线分隔 | `2026_01_02/` | ✅ 支持 |
| 点号分隔 | `2026.01.02/` | ✅ 支持 |
| 中文日期 | `2026年1月2日/` | ✅ 支持 |
| 文件名中的日期 | `photo_20260102.jpg` | ✅ 自动提取 |
| 英文月份 | `2026-Jan-02/` | ✅ 支持 |

**例外处理**:
- 如果文件无法识别日期，程序会提示（检查 logs/ 中的日志）
- 日期文件夹优先级：文件夹名 > 文件名 > 文件元数据

---

## 2. output 目录结构

### 2.1 标准输出结构（处理完成后）

```
output/
├── Alice/                             # 学生 Alice 的所有识别结果
│   ├── 2026-01-01/                    # 日期 1
│   │   ├── classroom_photo_001.jpg    # Alice 在 2026-01-01 的照片
│   │   └── classroom_photo_002.jpg
│   └── 2026-01-02/                    # 日期 2
│       └── group_activity.png
├── Bob/                               # 学生 Bob 的所有识别结果
│   └── 2026-01-01/
│       └── classroom_photo_001.jpg
├── Unknown_Person_1/                  # 未知人脸聚类 1（相似人脸自动归组）
│   └── 2026-01-01/
│       ├── photo_034.jpg
│       └── photo_045.jpg
├── Unknown_Person_2/                  # 未知人脸聚类 2
│   └── 2026-01-01/
│       └── visitor_photo.jpg
├── unknown_photos/                    # 特殊情况：无法聚类的单次出现人脸
│   └── 2026-01-01/
│       └── single_unknown_face.jpg
├── no_face_photos/                    # 特殊情况：未检测到人脸的照片
│   └── 2026-01-01/
│       └── landscape_photo.jpg
├── error_photos/                      # 特殊情况：处理过程中出错的照片
│   └── 2026-01-01/
│       └── corrupted_image.jpg
└── 20260102_整理报告.txt              # 整理报告（文件名带时间戳，避免覆盖）
```

**说明**:
- 格式：`<学生名>/<日期>/<照片>`
- 时间戳报告：`YYYYMMDD_整理报告.txt`（防止多次运行时覆盖）
- `Unknown_Person_X`：自动聚类的未知人脸（X ≥ 1）
- `unknown_photos`：无法聚类的单个人脸
- `no_face_photos`：检测不到人脸的照片
- `error_photos`：处理出错的照片

### 2.2 缓存目录（隐藏）

```
output/
└── .state/                            # 隐藏状态目录
    ├── class_photos_snapshot.json     # 课堂照快照（用于增量处理）
    └── recognition_cache_by_date/    # 识别缓存（按日期分片）
        ├── 2026-01-01.json
        └── 2026-01-02.json

  ### 2.3 2 名学生小样本（输入/输出示例）

  输入示例：

  ```
  input/
  ├── student_photos/
  │   ├── Alice/
  │   │   ├── a1.jpg
  │   │   └── a2.jpg
  │   └── Bob/
  │       ├── b1.jpg
  │       └── b2.jpg
  └── class_photos/
    └── 2026-01-02/
      ├── c1.jpg
      └── c2.jpg
  ```

  运行后可能的输出（含 unknown 聚类）：

  ```
  output/
  ├── Alice/2026-01-02/...
  ├── Bob/2026-01-02/...
  ├── unknown_photos/2026-01-02/Unknown_Person_1/...
  ├── no_face_photos/2026-01-02/...   # 如无则不会出现
  ├── error_photos/2026-01-02/...     # 如无则不会出现
  ├── 20260102_整理报告.txt
  └── 20260102_智能分析报告.txt
  ```

  说明：
  - `Unknown_Person_X` 为相似未知人脸聚类；单次出现的未知人脸在 `unknown_photos/日期/` 下。
  - 报告文件带日期时间戳，避免覆盖；包含 unknown/no-face/error 分别的统计。
```

---

## 3. 配置文件示例

### 3.0 最小可用 config.json（直接复制）

```
{
  "input_dir": "input",
  "output_dir": "output",
  "log_dir": "logs",
  "tolerance": 0.6,
  "min_face_size": 50,
  "parallel_recognition": {
    "enabled": true,
    "workers": 6,
    "chunk_size": 12,
    "min_photos": 30
  },
  "unknown_face_clustering": {
    "enabled": true,
    "threshold": 0.45,
    "min_cluster_size": 2
  },
  "class_photos_dir": "class_photos",
  "student_photos_dir": "student_photos"
}
```

### 3.1 进阶配置

### 3.1 最小化配置（config.json）

```json
{
  "_comment": "最小化配置：只改你需要的",
  "input_dir": "input",
  "output_dir": "output",
  "log_dir": "logs",
  "tolerance": 0.6
}
```

**说明**：这个配置基本可以满足大多数场景。

### 3.2 完整配置（config.json）

```json
{
  "_comment_1": "路径配置",
  "input_dir": "input",
  "output_dir": "output",
  "log_dir": "logs",
  "class_photos_dir": "class_photos",
  "student_photos_dir": "student_photos",

  "_comment_2": "识别配置",
  "tolerance": 0.6,
  "min_face_size": 50,

  "_comment_3": "人脸后端",
  "face_backend": {
    "engine": "insightface"
  },

  "_comment_4": "并行识别配置",
  "parallel_recognition": {
    "enabled": true,
    "workers": 6,
    "chunk_size": 12,
    "min_photos": 30
  },

  "_comment_5": "未知人脸聚类配置（v0.4.0+）",
  "unknown_face_clustering": {
    "enabled": true,
    "threshold": 0.45,
    "min_cluster_size": 2
  }
}
```

### 3.3 特定场景配置

#### 场景 A：对识别效果要求高（严格匹配）

```json
{
  "tolerance": 0.55,
  "unknown_face_clustering": {
    "threshold": 0.40
  }
}
```

#### 场景 B：对识别宽松一点（容忍偶尔误判）

```json
{
  "tolerance": 0.65,
  "unknown_face_clustering": {
    "threshold": 0.50
  }
}
```

#### 场景 C：禁用未知人脸聚类

```json
{
  "unknown_face_clustering": {
    "enabled": false
  }
}
```

#### 场景 D：使用 dlib 后端（而非 InsightFace）

```json
{
  "face_backend": {
    "engine": "dlib"
  }
}
```

#### 场景 E：禁用并行处理（调试或低内存机器）

```json
{
  "parallel_recognition": {
    "enabled": false
  }
}
```

---

## 4. 命令行示例

### 4.1 基础运行

```bash
# 使用默认配置
python src/cli/run.py

# 使用指定工作目录的 config.json
cd /Users/teacher/Desktop/SundayPhotoOrganizer
python /path/to/src/cli/run.py
```

### 4.2 CLI 参数覆盖

```bash
# 指定输入/输出目录
python src/cli/run.py --input-dir /custom/input --output-dir /custom/output

# 指定识别阈值
python src/cli/run.py --tolerance 0.55

# 禁用并行处理（调试）
python src/cli/run.py --no-parallel

# 查看帮助
python src/cli/run.py --help
```

### 4.3 从源码运行

```bash
# 克隆并进入项目
git clone <repo-url> sunday-photos
cd sunday-photos

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行
python src/cli/run.py
```

---

## 5. 环境变量示例

### 5.1 强制指定 Work folder（便携/离线场景）

```bash
# macOS/Linux
export SUNDAY_PHOTOS_WORK_DIR=/Volumes/USB_Drive/SundayPhotos
python src/cli/run.py

# Windows（PowerShell）
$env:SUNDAY_PHOTOS_WORK_DIR = "D:\SundayPhotos"
python src\cli\run.py
```

### 5.2 切换人脸识别后端

```bash
# macOS/Linux 使用 dlib
export SUNDAY_PHOTOS_FACE_BACKEND=dlib
python src/cli/run.py

# Windows（PowerShell）
$env:SUNDAY_PHOTOS_FACE_BACKEND = "insightface"
python src\cli\run.py
```

### 5.3 禁用并行处理（调试/低内存）

```bash
# macOS/Linux
export SUNDAY_PHOTOS_NO_PARALLEL=1
python src/cli/run.py

# Windows（PowerShell）
$env:SUNDAY_PHOTOS_NO_PARALLEL = "1"
python src\cli\run.py
```

### 5.4 启用诊断输出

```bash
# macOS/Linux
export SUNDAY_PHOTOS_DIAG_ENV=1
python src/cli/run.py

# Windows（PowerShell）
$env:SUNDAY_PHOTOS_DIAG_ENV = "1"
python src\cli\run.py
```

### 5.5 组合示例：离线模式 + dlib + 诊断输出

```bash
# macOS/Linux
export SUNDAY_PHOTOS_WORK_DIR=/mnt/usb/work
export SUNDAY_PHOTOS_FACE_BACKEND=dlib
export SUNDAY_PHOTOS_DIAG_ENV=1
python src/cli/run.py

# Windows（PowerShell）
$env:SUNDAY_PHOTOS_WORK_DIR = "D:\offline_work"
$env:SUNDAY_PHOTOS_FACE_BACKEND = "dlib"
$env:SUNDAY_PHOTOS_DIAG_ENV = "1"
python src\cli\run.py
```

---

## 相关文档

- 完整配置参考：[CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)
- 老师快速开始：[TeacherQuickStart.md](TeacherQuickStart.md)
- 开发指南：[DeveloperGuide.md](DeveloperGuide.md)
- 运行时健康检查：[HealthCheck_Runtime.md](HealthCheck_Runtime.md)
- 发布验收清单：[HealthCheck_Release.md](HealthCheck_Release.md)
