# 配置说明（config.json）

**版本**: v0.4.0  
**更新日期**: 2025-12-26

本项目使用 `config.json` 作为默认配置文件，支持默认配置直接运行（会自动生成默认配置）。

## 1. 配置优先级

优先级从高到低：

1) **命令行参数**（例如 `--input-dir`、`--tolerance`、`--no-parallel` 等）
2) **config.json**（不存在时自动创建默认配置；老师无需修改）
3) **程序内置默认值**

补充：
- 环境变量 `SUNDAY_PHOTOS_NO_PARALLEL=1`（或 `true`/`yes`）会强制禁用并行识别（用于排障或低内存环境）
- 环境变量 `SUNDAY_PHOTOS_PARALLEL=1` 可临时启用并行识别（无需修改配置文件）
 - 环境变量 `SUNDAY_PHOTOS_FACE_BACKEND=insightface|dlib` 可临时切换人脸识别后端（优先级高于 config.json）

## 2. 为什么 config.json 里有“注释字段”

标准 JSON 不支持 `//` 或 `/* */` 注释。

为了让老师/维护者打开配置就能看懂，本项目在 `config.json` 中使用：
- `_comment`
- `xxx_comment`

来存放说明文字。

程序会忽略这些字段，因此文件仍然是合法 JSON。

## 3. 常用字段速览

### 3.1 路径

- `input_dir`：输入根目录（默认 `input`）
  - 源码/开发模式：相对路径会基于项目根目录解析
  - 打包老师版：默认是“可执行文件同目录下的 `input/`”（首次运行自动创建）
  - 学生参考照：`{input_dir}/student_photos/`
  - 课堂照片：`{input_dir}/class_photos/`
- `output_dir`：输出目录（默认 `output`）
- `log_dir`：日志目录（默认 `logs`）

### 3.2 人脸匹配阈值

- `tolerance`：人脸匹配阈值（0~1，默认 `0.6`）
  - 越小越严格：误识别更少，但可能漏识别
  - 越大越宽松：更容易匹配，但可能误识别

说明：推荐使用顶层 `tolerance`。历史配置里可能出现 `face_recognition.tolerance`，程序也会兼容读取（当未显式设置顶层 `tolerance` 时生效）。

实践建议：`0.55~0.65` 通常较均衡。

### 3.2.1 最小人脸尺寸（远景/模糊优化）

- `min_face_size`：最小人脸尺寸（像素近似值，默认 `50`）
  - 越小：更容易检测到远处/小人脸，但可能增加误检与耗时
  - 越大：更少误检，但可能漏掉远处人脸

说明：推荐使用顶层 `min_face_size`。历史配置里可能出现 `face_recognition.min_face_size`，程序也会兼容读取（当未显式设置顶层 `min_face_size` 时生效）。

### 3.3 人脸识别后端（face_backend）

默认后端为 **InsightFace（推荐）**，同时支持回退到 **dlib/face_recognition**（需要你自行安装对应依赖）。

- `face_backend.engine`：后端引擎选择
  - `insightface`（默认）：更适合复杂/多人/角度变化场景；embedding 常见为 512 维
  - `dlib`：兼容旧的 `face_recognition/dlib`；embedding 常见为 128 维

优先级：若设置了环境变量 `SUNDAY_PHOTOS_FACE_BACKEND`，则会覆盖 `config.json`。

**重要（缓存隔离）**：参考照编码缓存会按“后端/模型”分目录保存，避免不同后端的维度混用导致报错：

- 参考照缓存：`{input_dir}/logs/reference_encodings/<engine>/<model>/`
- 参考照快照：`{input_dir}/logs/reference_index/<engine>/<model>.json`

### 3.4 未知人脸聚类（🆕 v0.4.0）

**新功能**：自动将相似的未知人脸归为一组，便于管理访客、家长、新学生。

- `unknown_face_clustering.enabled`：是否启用聚类（默认 `true`）
- `unknown_face_clustering.threshold`：聚类阈值（默认 `0.45`，比匹配阈值更严格）
  - 越小越严格：只有非常相似的人脸才会归组
  - 越大越宽松：更多人脸会被归为同一组
- `unknown_face_clustering.min_cluster_size`：最小聚类大小（默认 `2`）
  - 只有当组内照片数 ≥ 此值时才会创建 `Unknown_Person_X` 文件夹
  - 单次出现的人脸会直接放在 `unknown_photos/日期/` 下

**输出结构**：
```
output/
└── unknown_photos/
    ├── Unknown_Person_1/     # 第一组相似人脸（如访客A）
    │   └── 2025-12-21/
    │       ├── photo1.jpg
    │       └── photo2.jpg
    ├── Unknown_Person_2/     # 第二组相似人脸（如家长B）
    │   └── 2025-12-28/
    │       └── photo3.jpg
    └── 2025-12-21/           # 单次出现的人脸
        └── blurry.jpg
```

**应用场景**：
- **访客管理**：多次来访的家长会自动归组
- **新学生识别**：经常出现的未知人脸可能是新学生
- **志愿者追踪**：定期参与的志愿者照片集中管理

### 3.5 并行识别（parallel_recognition）

并行识别通过多进程利用多核 CPU 提升速度，适合“课堂照数量很多”的场景。

当前策略（更稳定、口径更清晰）：
- 小批量（照片数 < `min_photos`）默认回退串行（减少进程启动开销，调试也更直观）
- 大批量（照片数 ≥ `min_photos`）启用并行
- 并行识别异常时自动回退串行，保证流程不中断

- `parallel_recognition.enabled`：是否允许启用并行（默认 `true`）
- `parallel_recognition.workers`：并行进程数（默认 `6`，固定不做“智能拉高”，仅做不超过 CPU 核心数的上限保护）
- `parallel_recognition.chunk_size`：每批次分发给 worker 的照片数量（默认 `12`）
- `parallel_recognition.min_photos`：启用阈值（默认 `30`）
  - 当课堂照数量 < `min_photos` 时，自动回退串行（小批量更稳定）

**快速启用方式**：
- **临时启用**：`SUNDAY_PHOTOS_PARALLEL=1 python run.py`
- **持久配置**：在 `config.json` 中设置 `parallel_recognition.enabled: true`

调试技巧：
- `SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS=0` 可在调试时强制“小批量也走并行”（默认建议不要开）

### 3.6 缓存与增量刷新（强制全量重跑）

默认情况下，程序会使用快照与缓存加速重复运行。若发现“新增照片未被处理”或想强制全量重跑，可选择：
- 删除输出目录下的增量/缓存痕迹：`output/.state/`（增量快照 + 按日期缓存 `recognition_cache_by_date/*.json`）；然后重新运行。
- 或者，将 `class_photos/` 中对应日期子目录重命名/移动，再次运行会视为新输入进行全量处理。
注意：删除缓存不会删除原始照片，仅会让程序重新识别并生成新的输出与报告。

强制回退串行（排障）：
- 命令行：`python run.py --no-parallel`
- 环境变量：`SUNDAY_PHOTOS_NO_PARALLEL=1`

## 4. 默认配置模式（通常无需改动）

- 打包版首次运行会在“工作目录（Work folder）”中自动创建 `input/`、`output/`、`logs/` 与 `config.json`，并写入默认值；老师通常不需要编辑此文件。
  - Work folder 选择规则：优先在可执行文件同目录创建；若不可写则回退到桌面（或主目录）；启动时会打印实际 Work folder 路径。
- 源码运行时若缺少 `config.json`，也会回退到内置默认配置。
- 路径字段若填写相对路径，会自动基于项目根目录解析；打包版则基于 Work folder 解析。
