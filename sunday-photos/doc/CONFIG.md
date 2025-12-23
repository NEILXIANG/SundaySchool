# 配置说明（config.json）

**版本**: v0.4.0  
**更新日期**: 2025-12-23

本项目使用 `config.json` 作为默认配置文件，支持零配置运行（自动生成默认配置）。

## 1. 配置优先级

优先级从高到低：

1) **命令行参数**（例如 `--input-dir`、`--tolerance`、`--no-parallel` 等）
2) **config.json**（不存在时自动创建默认配置；老师无需修改）
3) **程序内置默认值**

补充：
- 环境变量 `SUNDAY_PHOTOS_NO_PARALLEL=1`（或 `true`/`yes`）会强制禁用并行识别（用于排障或低内存环境）
- 环境变量 `SUNDAY_PHOTOS_PARALLEL=1` 可临时启用并行识别（无需修改配置文件）

## 2. 为什么 config.json 里有“注释字段”

标准 JSON 不支持 `//` 或 `/* */` 注释。

为了让老师/维护者打开配置就能看懂，本项目在 `config.json` 中使用：
- `_comment`
- `xxx_comment`

来存放说明文字。

程序会忽略这些字段，因此文件仍然是合法 JSON。

## 3. 常用字段速览

### 3.1 路径

- `input_dir`：输入根目录（默认 `input`，相对路径会基于项目根目录解析；打包版默认为桌面生成的 SundaySchoolPhotoOrganizer）
  - 学生参考照：`{input_dir}/student_photos/`
  - 课堂照片：`{input_dir}/class_photos/`
- `output_dir`：输出目录（默认 `output`）
- `log_dir`：日志目录（默认 `logs`）

### 3.2 人脸匹配阈值

- `tolerance`：人脸匹配阈值（0~1，默认 `0.6`）
  - 越小越严格：误识别更少，但可能漏识别
  - 越大越宽松：更容易匹配，但可能误识别

实践建议：`0.55~0.65` 通常较均衡。

### 3.3 未知人脸聚类（🆕 v0.4.0）

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

### 3.4 并行识别（parallel_recognition）

并行识别通过多进程利用多核 CPU 提升速度，适合“课堂照数量很多”的场景。当前默认关闭，满足低配机器与最简使用；当需要加速大批量照片时可开启。

**智能决策**：程序会根据实际情况自动选择最优模式：
- 当待识别照片 ≥ 50张且未开启并行时，会提示建议开启并预计节省时间
- 当照片数 < `min_photos` 时，自动使用串行（小批量更稳定）
- 并行识别异常时自动回退串行，保证流程不中断

- `parallel_recognition.enabled`：是否允许启用并行（默认 `false`）
- `parallel_recognition.workers`：并行进程数（默认 `4`）
- `parallel_recognition.chunk_size`：每批次分发给 worker 的照片数量（默认 `12`）
- `parallel_recognition.min_photos`：启用阈值（默认 `30`）
  - 当课堂照数量 < `min_photos` 时，自动回退串行（小批量更稳定）

**快速启用方式**：
- **临时启用**：`SUNDAY_PHOTOS_PARALLEL=1 python run.py`
- **持久配置**：在 `config.json` 中设置 `parallel_recognition.enabled: true`

强制回退串行（排障）：
- 命令行：`python run.py --no-parallel`
- 环境变量：`SUNDAY_PHOTOS_NO_PARALLEL=1`

## 4. 零配置模式（老师无需改动）

- 打包版首次运行会自动在桌面创建工作目录与 `config.json`，并写入默认值；老师不需要编辑此文件。
- 源码运行时若缺少 `config.json`，也会回退到内置默认配置。
- 路径字段若填写相对路径，会自动基于项目根目录解析；打包版则基于桌面创建的工作目录解析。
