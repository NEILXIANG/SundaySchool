# 项目体检报告（Sunday School Photo Organizer / sunday-photos）

更新日期：2025-12-26

## 1. 结论摘要（TL;DR）
- 代码可运行、测试通过；源码态与打包态验证均通过。
- 人脸识别后端已支持 **InsightFace（默认）** 与 **dlib/face_recognition（可选）** 的配置切换，并对缓存做了**按后端隔离**，避免 128/512 embedding 混用。
- 并行策略为“**可控并行**”：默认开启、默认 `workers=6`、`min_photos=30`，不做自动“智能拉高”。
- 文档已对齐实现（后端/并行/缓存/打包），并补齐/修正中英文说明与部署文档细节。

## 2. 验收结果（自动化）
- 源码态：`pytest -q` 通过（示例输出：`198 passed, 6 skipped`）。
- 打包态：已构建 macOS onefile 控制台产物，并运行 `REQUIRE_PACKAGED_ARTIFACTS=1 pytest -q` 通过（示例输出：`198 passed, 6 skipped`）。

建议的“发布验收一键动作”：
- 先构建：`bash scripts/build_mac_app.sh`
- 再验收：`REQUIRE_PACKAGED_ARTIFACTS=1 python -m pytest -q`

## 3. 核心模块体检（结构与职责）
- `src/core/main.py`
  - 主流程编排：输入扫描 → 增量缓存命中 → 未命中识别（串行/并行）→ 文件落盘与报告。
  - 关键点：并行启用判断基于 `parallel_recognition`（enabled/min_photos/workers）与环境变量覆盖。
- `src/core/face_recognizer.py`
  - 人脸后端抽象与兼容层：
    - 默认 InsightFace（常见 512 维 embedding）
    - 可选 dlib/face_recognition（常见 128 维 embedding）
  - 关键点：
    - **后端选择优先级**：环境变量 `SUNDAY_PHOTOS_FACE_BACKEND` > `config.json`（`face_backend.engine`）。
    - **缓存隔离**：参考照编码缓存/快照按 `engine/model` 分目录存储，避免跨后端污染。
    - **缓存快照兼容**：快照包含 `engine/model/embedding_dim` 元信息，自动失效旧缓存。
- `src/core/parallel_recognizer.py`
  - 仅负责“识别”并行化：spawn 子进程、initializer 缓存只读数据、`imap_unordered` 输出结果。
  - 关键点：支持 `SUNDAY_PHOTOS_NO_PARALLEL=1` 强制串行；并行失败会在主流程回退串行。
- `src/core/config_loader.py` / `src/core/config.py`
  - 统一默认配置与覆盖策略；并行默认值集中在 `DEFAULT_PARALLEL_RECOGNITION`。

## 4. 逻辑风险与合理性检查
### 4.1 多人场景误分配风险（已知、合理解释）
- 现象：同一张照片多张脸都可能落到同一学生（当多张脸与某学生 embedding 距离都 < tolerance）。
- 原因：1-N 最近邻 + 阈值策略在多人合影、遮挡、角度复杂时会出现“近似距离碰撞”。
- 建议（不改变需求前提下）：
  - 老师侧：提高参考照质量（2–5 张清晰正脸）与课堂照清晰度。
  - 工程侧（如未来要提升）：可引入“每张照片每个学生最多分配一次/每张脸唯一分配”的约束、或更严格的二阶段判别（但属于产品策略变更）。

### 4.2 缓存一致性风险（已处理）
- 已修复问题：历史 128 维缓存与新 512 维 embedding 混用导致 `shapes (128,) and (512,) not aligned`。
- 当前策略：按后端隔离 + 快照 version/元信息校验 + 距离计算维度不一致兜底（避免崩溃与误匹配）。

### 4.3 打包与离线部署风险（需知会）
- InsightFace 可能在首次运行下载模型至本机缓存（默认 `~/.insightface/`），离线机器需要预下载并随部署提供。
- 可在部署时通过环境变量指定缓存目录（详见 DeveloperGuide/CONFIG）。

## 5. 文档一致性体检（代码 vs 文档）
已对齐要点：
- 人脸后端：默认 InsightFace，可选 dlib/face_recognition；切换方式（env/config）与缓存隔离路径。
- 并行策略：默认开启、默认 workers=6、无智能拉高；禁用方式 `SUNDAY_PHOTOS_NO_PARALLEL=1`。
- 打包产物与教师使用路径：`release_console/` 同目录 input/output/logs 工作流；不可写时回退 Desktop/Home，并以 `Work folder:` 为准。

## 6. 清理与产物管理（已执行/建议执行）
已执行（安全清理，不影响真实输入照片）：
- 清理 `sunday-photos/` 下的构建/缓存/中间产物（如 `build/`、`dist/`、`output/`、`logs/`、`.pytest_cache/`、`__pycache__/`、`.debug_work/` 等）。
- 清理仓库根目录下的历史运行日志与临时文件（如根目录 `logs/` 与 `temp.txt`）。

可选（需要你确认是否删除）：
- 删除历史虚拟环境目录 `sunday-photos/.venv310/`（如确认不再使用，可运行：`bash scripts/clean_generated_artifacts.sh --venv --yes`）。

## 7. 建议的后续改进清单（按优先级）
- P0（稳定性/可运维）：为离线部署补充“模型预下载/随包分发”的标准操作步骤与检查项。
- P1（识别体验）：对多人照片引入更强约束的“分配策略”（需要明确产品规则）。
- P2（可维护性）：将主流程中并行决策/提示日志抽取为小函数，进一步降低 `main.py` 复杂度（不改行为）。
