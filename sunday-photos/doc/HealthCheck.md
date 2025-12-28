# 项目健康检查清单（Health Check Checklist）

**更新日期**: 2025-12-27

目的：这是一份“可执行”的检查清单，用于发布前/回归前快速确认项目处于健康状态。

说明：历史的“体检报告类总结”请参考 `doc/HealthCheckReport.md` / `doc/HealthCheckReport_en.md`。

---

## 1) 文档口径一致性（必须）

- 入口名称一致：`SundayPhotoOrganizer`（macOS app + console onedir + Windows onedir）
- 老师端唯一输入规范一致：`input/student_photos/<学生名>/*.jpg|png...`（禁止根目录直接放图；禁止更深层嵌套）
- 自动按日期归档课堂照的解释存在：`class_photos/` 根目录照片会被移动到 `YYYY-MM-DD/`
- “不准时三步法”一致：只允许建议补参考照/提高参考照质量/课堂照更清晰，不引导老师调参

建议抽查：
- `doc/TeacherQuickStart.md` / `doc/TeacherQuickStart_en.md`
- `doc/TeacherGuide.md` / `doc/TeacherGuide_en.md`
- `doc/CONFIG.md` / `doc/CONFIG_en.md`

---

## 2) 打包与产物结构（必须）

- onedir 产物存在：`release_console/SundayPhotoOrganizer/`
  - macOS 可执行：`release_console/SundayPhotoOrganizer/SundayPhotoOrganizer`
  - Windows 可执行：`release_console/SundayPhotoOrganizer/SundayPhotoOrganizer.exe`
- macOS 老师双击版存在（如需要）：`release_mac_app/SundayPhotoOrganizer.app`
- 发布包内只保留说明类 `.md`（md-only 口径）；必要的 `.txt`（例如运行生成的报告）不在此限制内

---

## 3) 运行目录与权限（必须）

- Work folder 行为符合预期：默认在“可执行文件同目录”创建 `input/ output/ logs/`
- 若目录不可写：回退到 Desktop/Home，并在控制台打印 `Work folder:` 作为唯一准确信息
- 环境变量 `SUNDAY_PHOTOS_WORK_DIR` 可强制指定 Work folder（便于便携/演示）

---

## 4) 缓存与增量（建议检查）

- 增量快照：`output/.state/class_photos_snapshot.json`
- 识别缓存（按日期）：`output/.state/recognition_cache_by_date/YYYY-MM-DD.json`
- 参考照缓存与快照统一在 `log_dir` 下（默认 `logs/`）：
  - `{log_dir}/reference_encodings/<engine>/<model>/*.npy`
  - `{log_dir}/reference_index/<engine>/<model>.json`

---

## 5) 并行与排障（建议检查）

- 默认并行策略：满足阈值才并行；并行失败会自动回退串行
- 排障开关可用：
  - 强制串行：`SUNDAY_PHOTOS_NO_PARALLEL=1`
  - 诊断输出：`SUNDAY_PHOTOS_DIAG_ENV=1`

---

## 6) 验收命令（推荐）

- 开发模式：`pytest -q`
- 发布严格模式（要求打包产物存在）：`REQUIRE_PACKAGED_ARTIFACTS=1 pytest -q`

