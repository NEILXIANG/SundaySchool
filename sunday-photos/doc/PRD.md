# 产品需求说明文档 / Product Requirements Document (PRD)

**项目**: 主日学照片整理工具 / Sunday Photos Organizer  
**版本**: 1.3.0  
**更新日期**: 2026-01-02

---

## 1. 产品概述 / Overview

### 1.1 产品定位
- **核心价值**：解放老师双手，让照片管理从"繁琐手工"变成"一键完成"
- **目标用户**：主日学教师、培训机构组织者、活动管理员（无需额外技术准备也可用）
- **应用场景**：课堂合照批量整理、活动照片归档、学生成长记录管理

### 1.2 核心目标
- 通过人脸识别将课堂合照按学生自动分类 / Classify classroom photos by student via face recognition
- 输出按 `学生/日期` 三级组织，直观易用 / Outputs organized by student and date
- 智能识别未知人脸并自动聚类（访客/家长归组）/ Cluster unknown faces automatically
- 默认设置即可运行，打包版双击即用 / Works with sensible defaults, packaged version ready-to-use
- 路径与阈值可配置，满足高级需求 / Configurable paths and tolerance for advanced users

---

## 2. 功能需求 / Functional Requirements

### 2.1 核心功能
- **人脸识别引擎** / Face Recognition Engine：
  - 默认使用 **InsightFace**（CPU 推理，ArcFace embedding 常见为 512 维）
  - 支持可配置回退到 `face_recognition/dlib`（embedding 常见为 128 维；需自行安装依赖）
  - 支持多编码融合（每学生多张参考照，自动选择最佳匹配）
  - 识别效果：参考照质量良好时通常更准；以实际运行报告为准
  
- **智能聚类** / Intelligent Clustering (v0.4.0)：
  - 未知人脸自动聚类，相似人脸归入 `Unknown_Person_X` 组
  - 贪婪算法 + 默认严格阈值(0.45)，避免误聚类（可通过 config.json 的 unknown_face_clustering.threshold 调整）
  - 支持配置：unknown_face_clustering.enabled/threshold/min_cluster_size
  - 应用场景：访客/家长/新学生自动归档
  
- **增量处理** / Incremental Processing：
  - 按日期文件夹追踪处理状态，仅处理变化部分
  - 删除同步：输入删除时自动清理输出
  - 识别结果缓存：参数未变时复用，提升速度
  
- **并行识别** / Parallelization：
  - 小批量（低于 `min_photos`）默认串行，减少进程启动开销
  - 大批量（达到 `min_photos`）启用多进程并行（默认 workers=6，固定不做“智能拉高”）
  - 异常自动回退串行，确保完成
  
- **文件整理** / File Organization：
  - 输出结构：`output/学生名/日期/照片`
  - 未知照片：`output/unknown_photos/日期/` 或 `output/unknown_photos/Unknown_Person_X/日期/`
  - 智能文件命名：照片默认保留原名；同目录重名自动添加 `_001/_002...` 避免覆盖（整理报告文件名带时间戳前缀）
  
- **配置管理** / Configuration Management：
  - config.json（支持注释字段）
  - 环境变量覆盖（临时配置）
  - 命令行参数（调试用）
  
- **日志与报告** / Logging & Reporting：
  - 彩色日志（绿色成功/黄色警告/红色错误）
  - 实时进度条（tqdm）
  - 详细统计报告（耗时/成功率/学生分布）

### 2.2 命令行接口 / CLI
```bash
# 基础使用
python run.py

# 带参数使用
python run.py \
  --input-dir "input" \      # 输入目录 default: input
  --output-dir "output" \    # 输出目录 default: output
  --tolerance 0.6           # 识别阈值 default: 0.6

# 环境变量
SUNDAY_PHOTOS_PARALLEL=1 python run.py  # 临时启用并行
SUNDAY_PHOTOS_NO_PARALLEL=1 python run.py  # 强制禁用并行
SUNDAY_PHOTOS_FACE_BACKEND=insightface python run.py  # 选择 InsightFace 后端（默认）
SUNDAY_PHOTOS_FACE_BACKEND=dlib python run.py  # 选择 dlib/face_recognition 后端（可选）
```

### 2.3 打包版（老师模式）
- **运行方式**：双击 `release_console/启动工具.sh` (macOS) 或 `Launch_SundayPhotoOrganizer.bat` (Windows)
- **工作目录**：可执行文件同目录（首次自动创建 `input/`、`output/`、`logs/`）
- **参数配置**：通过 `config.json` 修改（可选，默认即可）

---

## 3. 非功能需求 / Non-Functional Requirements

### 3.1 性能
- **识别速度** Performance（参考信息，非承诺；以实际运行输出为准）：
  - 串行/并行耗时会随照片数量、清晰度与硬件差异而变化
  - 增量处理通常更快（仅处理变化的输入；加速效果取决于缓存命中与变更比例）
  
- **资源占用** Resource Usage：
  - 内存：100张照片约 500MB-1GB
  - CPU：支持多核并行（默认开启；默认 `workers=6`，且不超过 CPU 核心数）
  - 磁盘：会写入增量状态与缓存（大小与照片数量/人脸数量相关；以实际目录占用为准）

### 3.2 兼容性 / Compatibility
- **操作系统**：Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python版本**：3.7 - 3.14（推荐 3.10+）
- **架构支持**：x86_64, ARM64 (macOS M1/M2)

### 3.3 安全性 / Security
- 配置字段范围校验（tolerance: 0-1）
- 日志不记录人脸编码（numpy数组）
- 缓存使用原子操作，避免损坏

### 3.4 稳定性 / Reliability
- **容错设计**：核心流程确保完成，辅助功能静默失败
- **自动回退**：并行失败→串行，内存不足→跳过
- **错误回滚**：文件操作失败时自动清理
- **测试覆盖**：覆盖核心/边界/打包验证（用例数随迭代持续增长）

---

## 4. 数据需求 / Data Requirements

### 4.1 输入规范 / Input
```
input/
├── student_photos/      # 学生参考照（唯一方式：student_photos/学生名/...）
│   ├── Alice/
│   │   ├── ref_01.jpg   # 文件名随意
│   │   └── ref_02.png
│   └── Bob/
│       └── photo.jpg
└── class_photos/        # 课堂照片（建议按日期子目录）
    ├── 2025-12-21/
    │   └── group.jpg
    └── loose.jpg        # 根目录照片会自动移动到日期子目录
```

- **格式支持**：JPG, PNG, BMP（自动检测）
- **文件大小**：不做限制（超大图片可能占用更多内存）
- **参考照数量**：每学生最多使用 5张（按修改时间取最新）
- **参考照质量要求**：
  - 清晰正脸，无遮挡
  - 尽量单人照（避免多人合照）
  - 建议 2-5张不同角度

### 4.2 输出结构 / Output
```
output/
├── Alice/                    # 学生文件夹
│   ├── 2025-12-21/
│   │   ├── group.jpg
│   │   └── activity.jpg
│   └── 2025-12-28/
│       └── discussion.jpg
├── Bob/
│   └── 2025-12-21/
│       └── group.jpg
├── unknown_photos/           # 未识别照片
│   ├── Unknown_Person_1/     # 聚类组（v0.4.0）
│   │   └── 2025-12-21/
│   │       ├── visitor_a.jpg
│   │       └── visitor_b.jpg
│   └── 2025-12-21/           # 单次出现
│       └── blurry_105632.jpg
├── .state/                   # 隐藏状态（增量/缓存）
│   ├── class_photos_snapshot.json
│   └── recognition_cache_by_date/
│       └── 2025-12-21.json
└── 20251221_143052_整理报告.txt      # 自动带时间戳前缀
```

---

## 5. 配置需求 / Configuration

### 5.1 配置文件 (config.json)
```json
{
  "input_dir": "input",                # 必填 required
  "output_dir": "output",              # 必填 required
  "log_dir": "logs",                   # 可选 optional
  "tolerance": 0.6,                    # 识别阈值 0~1, default: 0.6
  "min_face_size": 50,                 # 最小人脸尺寸（像素近似值），default: 50
  "unknown_face_clustering": {         # 未知人脸聚类（v0.4.0）
    "enabled": true,
    "threshold": 0.45,
    "min_cluster_size": 2
  },
  "log_level": "INFO",                 # DEBUG/INFO/WARNING/ERROR
  "parallel_recognition": {
    "enabled": true,                   # 并行开关
    "workers": 6,                      # 进程数（固定默认值）
    "chunk_size": 12,                  # 批次大小
    "min_photos": 30                   # 启用阈值
  }
}
```

### 5.2 依赖管理 (requirements.txt)
```
insightface
onnxruntime
opencv-python-headless
Pillow
numpy
tqdm
requests

# 可选（仅当选择 dlib 后端时需要）
face_recognition
dlib
```

---

## 6. 测试需求 / Testing Requirements

### 6.1 测试场景
- **单元测试** Unit Tests：核心功能模块（识别/整理/缓存）
- **集成测试** Integration Tests：完整流程验收
- **性能测试** Performance Tests：大批量场景（100+张）
- **打包验证** Packaging Validation：release acceptance检查
- **边界测试** Edge Cases：空输入/损坏文件/并发冲突

### 6.2 测试覆盖率
- **测试用例数**：以 `pytest -q` 输出为准（持续增长）
- **通过率要求**：100%
- **测试数据**：tests/data/ 目录

### 6.3 发布前检查清单
见 [doc/ReleaseAcceptanceChecklist.md](ReleaseAcceptanceChecklist.md)

---

## 7. 交付物 / Deliverables

### 7.1 源码仓库
- **实现**：src/ 目录（核心模块 + CLI）
- **测试**：tests/ 目录（覆盖核心与边界，持续增长）
- **文档**：doc/ 目录（PRD/README/开发指南/测试说明/配置说明）

### 7.2 打包产物
- **macOS（老师双击版 .app）**：release_mac_app/SundayPhotoOrganizer.app
- **macOS（控制台版 onedir）**：release_console/SundayPhotoOrganizer/SundayPhotoOrganizer（按构建架构分别生成 x86_64 / arm64）
- **Windows（控制台版 onedir）**：release_console/SundayPhotoOrganizer/SundayPhotoOrganizer.exe

### 7.3 用户文档
- **老师指南**：doc/TeacherGuide.md（中文） + doc/TeacherGuide_en.md（英文）
- **配置说明（SSOT）**：doc/CONFIG_REFERENCE.md（中文） + doc/CONFIG_REFERENCE_en.md（英文）
- **开发指南**：doc/DeveloperGuide.md
- **测试说明**：doc/TESTING.md

---

## 8. 风险与约束 / Risks & Constraints

### 8.1 技术风险
- **人脸识别精度**：依赖参考照质量（清晰度/角度/光线）
- **大批量性能**：200+张照片可能占用较多内存（建议分批处理）
- **模型体积/离线部署**：默认 InsightFace 可能在首次运行下载模型到本机缓存（离线环境需预下载并随部署一起提供）

### 8.2 用户约束
- **学习成本**：打包版零学习成本；源码版需基础命令行知识
- **参考照要求**：每学生至少 1张清晰正脸照
- **硬件要求**：推荐 4GB+ 内存，双核CPU

### 8.3 缓解策略
- **精度问题**：提供清晰的参考照要求说明 + 智能提示
- **性能问题**：默认并行（固定默认 workers）+ 增量处理 + 缓存优化
- **模型体积**：支持预下载/指定模型缓存目录，确保离线可用

---

## 9. 成功指标 / Success Metrics

### 9.1 功能指标
- ✅ 识别效果在参考照质量良好时通常更准（以实际运行报告为准）
- ✅ 常见规模通常可在几分钟内完成；大批量可选择并行加速（以实际运行结果为准）
- ✅ 测试通过率：以 `pytest -q` 运行结果为准
- ✅ 未知人脸聚类在照片质量较好时通常效果更好（以实际输出与抽样检查为准）

### 9.2 用户体验指标
- ✅ 老师首次上手时间通常较短（以教师实际体验为准）
- ✅ 操作步骤 ≤3步（放照片→运行→查看结果）
- ✅ 错误提示友好度（提供解决方案，非堆栈）

### 9.3 工程质量指标
- ✅ 代码测试覆盖（核心模块）
- ✅ 文档完整性（中英文双语）
- ✅ 跨平台兼容（Windows/macOS/Linux）

---

## 10. 未来规划 / Future Roadmap

### 10.1 短期优化（v1.4）
- 🔄 参考照质量检测（自动提示模糊/侧脸）
- 🔄 批量导入学生名单（CSV支持）
- 🔄 重复照片检测

### 10.2 中期增强（v2.0）
- 🔄 Web界面（简化老师操作）
- 🔄 云端存储集成（Google Photos/OneDrive）
- 🔄 照片质量分析

### 10.3 长期愿景
- 🔄 移动端应用（iOS/Android）
- 🔄 多语言界面
- 🔄 AI照片美化（自动选出最佳角度）
