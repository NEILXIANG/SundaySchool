# 产品需求说明文档 / Product Requirements Document (PRD)
项目：主日学照片整理工具 / Sunday Photos Organizer  
版本：1.0

---

## 1. 产品概述 / Overview
- 目标 Goals：
  - 通过人脸识别将课堂合照按学生分类 / Classify classroom photos by student via face recognition.
  - 输出按日期+学生组织 / Outputs organized by date and student.
  - 路径与阈值可配置 / Configurable paths and tolerance.
- 用户 Users：主日学教师、活动组织者；零基础也可用 / Teachers and organizers; non-technical friendly.

## 2. 功能需求 / Functional Requirements
- 核心功能 Core Features：
  - 人脸识别 / Face recognition (`face_recognition`).
  - 文件整理 / File organizer (student/date folders).
  - 配置管理 / Config management via config.json.
  - 日志记录 / Logging with levels.
- 命令行接口 CLI：
  ```bash
  python src/run.py \
    --input-dir "input" \    # 默认输入 default input
    --output-dir "output" \   # 默认输出 default output
    --tolerance 0.6           # 阈值 tolerance 0~1 (default 0.6)
  ```

## 3. 非功能需求 / Non-Functional
- 性能 Performance：≤2s/张（标准硬件）；支持并发（需按需优化）。
- 兼容 Compatibility：Windows/macOS/Linux；Python >=3.8.
- 安全 Security：配置字段必填/范围校验；日志不记录人脸编码。

## 4. 数据需求 / Data
- 输入 Input：
  ```
  input/
  ├── student_photos/      # 姓名 或 姓名_序号.jpg / Name or Name_index.jpg
  └── class_photos/        # 推荐日期子目录 / date subfolders recommended
  ```
  格式 formats: jpg/png, ≤5MB。
- 输出 Output：
  ```
  output/
  ├── ZhangSan/
  │   ├── 2025-12-21/
  │   └── 2025-12-28/
  └── LiSi/
      └── 2025-12-21/
  ```

## 5. 配置需求 / Config
- config.json
  ```json
  {
    "input_dir": "input",      // 必填 required
    "output_dir": "output",     // 必填 required
    "tolerance": 0.6,           // 可选 optional 0~1
    "log_level": "INFO"         // 可选 optional: DEBUG/INFO/WARNING/ERROR
  }
  ```
- 依赖 Dependencies（requirements.txt）：face_recognition>=1.3.0, Pillow>=10.3.0, numpy>=1.26.0.

## 6. 测试需求 / Testing
- 场景 Scenarios：单元 / unit；集成 / integration；性能 / performance (100+ photos)。
- 测试数据 Test data：示例照片位于 tests/data/student_photos 与 tests/data/class_photos。

## 7. 交付物 / Deliverables
1) 代码仓库（实现、测试、文档） / Repo with impl, tests, docs.
2) 可执行脚本 run.py（打包/清理脚本单独维护） / run.py; packaging/cleanup separately.
3) 文档 Docs：README、使用指南、PRD（本文件）。

## 8. 风险与约束 / Risks & Constraints
- 人脸识别精度依赖参考照质量 / Accuracy depends on reference quality.
- 大批量时的内存/CPU占用 / Resource load for large batches.
