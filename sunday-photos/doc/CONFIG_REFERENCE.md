# 配置参考手册 (Configuration Reference)

**版本**: v1.3.0  
**更新日期**: 2025-12-27

本文档是项目配置的**单一事实来源 (SSOT)**。所有配置项的详细说明、默认值、取值范围均以此为准。

---

## 1. 配置层级与优先级

系统按以下优先级加载配置（从高到低）：

1. **命令行参数 (CLI Arguments)**: 运行时指定，优先级最高。
2. **环境变量 (Environment Variables)**: 用于容器化或临时覆盖。
3. **配置文件 (config.json)**: 用户持久化配置。
4. **内置默认值 (Hardcoded Defaults)**: 代码中的兜底值。

---

## 2. 核心配置项详解

### 2.1 路径配置 (Paths)

| 配置键 (JSON) | 环境变量 | CLI 参数 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `input_dir` | `SUNDAY_PHOTOS_INPUT_DIR` | `--input-dir` | `input` | 输入根目录，包含 `student_photos` 和 `class_photos`。 |
| `output_dir` | `SUNDAY_PHOTOS_OUTPUT_DIR` | `--output-dir` | `output` | 输出根目录，存放整理后的照片和报告。 |
| `log_dir` | `SUNDAY_PHOTOS_LOG_DIR` | N/A | `logs` | 日志文件存放目录。 |

### 2.2 人脸识别配置 (Face Recognition)

| 配置键 (JSON) | 环境变量 | CLI 参数 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `tolerance` | `SUNDAY_PHOTOS_TOLERANCE` | `--tolerance` | `0.6` | 识别阈值 (0.0 - 1.0)。越低越严格，越高越容易误判。建议范围 0.4 - 0.6。 |
| `min_face_size` | `SUNDAY_PHOTOS_MIN_FACE_SIZE` | N/A | `50` | 最小人脸像素值 (px)。小于此尺寸的人脸将被忽略。 |
| `face_backend.engine` | `SUNDAY_PHOTOS_FACE_BACKEND` | N/A | `insightface` | 人脸识别引擎。可选值: `insightface` (默认, 推荐), `dlib` (需额外安装)。 |

### 2.3 并行处理配置 (Parallel Processing)

| 配置键 (JSON) | 环境变量 | 说明 |
| :--- | :--- | :--- |
| `parallel_recognition.enabled` | `SUNDAY_PHOTOS_PARALLEL` (1/0) | 是否启用多进程并行识别。默认 `true`。 |
| `parallel_recognition.workers` | `SUNDAY_PHOTOS_WORKERS` | 并行进程数。默认 `6`。建议设置为 CPU 核心数 - 1。 |
| `parallel_recognition.min_photos` | N/A | 触发并行的最小照片数。默认 `30`。少于此数量使用串行处理。 |
| N/A | `SUNDAY_PHOTOS_NO_PARALLEL` (1) | 强制禁用并行（优先级高于 enabled）。 |

### 2.4 未知人脸聚类 (Unknown Clustering)

| 配置键 (JSON) | 说明 |
| :--- | :--- |
| `unknown_face_clustering.enabled` | 是否启用未知人脸聚类。默认 `true`。 |
| `unknown_face_clustering.threshold` | 聚类判定阈值。默认 `0.45`。建议比识别阈值更严格。 |
| `unknown_face_clustering.min_cluster_size` | 最小聚类大小。默认 `2`。只有 >= 2 张相似照片才会归为一组。 |

---

## 3. 配置文件示例 (config.json)

```json
{
  "input_dir": "input",
  "output_dir": "output",
  "tolerance": 0.6,
  "min_face_size": 50,
  "face_backend": {
    "engine": "insightface"
  },
  "parallel_recognition": {
    "enabled": true,
    "workers": 6,
    "min_photos": 30
  },
  "unknown_face_clustering": {
    "enabled": true,
    "threshold": 0.45,
    "min_cluster_size": 2
  }
}
```
