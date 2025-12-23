# 配置说明（config.json）

本项目使用 `config.json` 作为默认配置文件。

## 1. 配置优先级

优先级从高到低：

1) 命令行参数（例如 `--input-dir`、`--tolerance`、`--no-parallel` 等）
2) `config.json`
3) 程序内置默认值

补充：
- 环境变量 `SUNDAY_PHOTOS_NO_PARALLEL=1`（或 `true`/`yes`）会强制禁用并行识别（用于排障或低内存环境）。

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
  - 学生参考照：`{input_dir}/student_photos/`
  - 课堂照片：`{input_dir}/class_photos/`
- `output_dir`：输出目录（默认 `output`）
- `log_dir`：日志目录（默认 `logs`）

### 3.2 人脸匹配阈值

- `tolerance`：人脸匹配阈值（0~1，默认 `0.6`）
  - 越小越严格：误识别更少，但可能漏识别
  - 越大越宽松：更容易匹配，但可能误识别

实践建议：`0.55~0.65` 通常较均衡。

### 3.3 并行识别（parallel_recognition）

并行识别通过多进程利用多核 CPU 提升速度，适合“课堂照数量很多”的场景。

- `parallel_recognition.enabled`：是否允许启用并行（默认 `true`）
- `parallel_recognition.workers`：并行进程数（默认 `4`）
- `parallel_recognition.chunk_size`：每批次分发给 worker 的照片数量（默认 `12`）
- `parallel_recognition.min_photos`：启用阈值（默认 `30`）
  - 当课堂照数量 < `min_photos` 时，自动回退串行（小批量更稳定）

强制回退串行（排障）：
- 命令行：`python run.py --no-parallel`
- 环境变量：`SUNDAY_PHOTOS_NO_PARALLEL=1`
