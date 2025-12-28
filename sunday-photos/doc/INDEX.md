# 文档索引（权威入口）

**更新日期**：2025-12-27

目标：减少重复、统一口径、让交付更稳定。

---

## 1) 我该看哪份？（按角色）

- 老师（只想照做）：`doc/TeacherQuickStart.md`
- 老师（需要解释/FAQ）：`doc/TeacherGuide.md`
- 同工（需要调参/排障/环境变量）：`doc/CONFIG_REFERENCE.md`
- 贡献者/维护者（看架构与实现）：`doc/ArchitectureGuide.md`、`doc/DeveloperGuide.md`
- 发布/验收（交付稳定）：`doc/ReleaseAcceptanceChecklist.md`、`doc/ReleaseFlow.md`、`doc/TESTING.md`

---

## 2) 文档治理规则（减少漂移）

- 单一事实来源（Single Source of Truth）
  - 目录结构/Work folder/缓存路径：以 `src/core/` 实现为准
  - 老师操作步骤：以 `TeacherQuickStart` 为准
  - FAQ/解释：以 `TeacherGuide` 为准（不要在 QuickStart 重复写长解释）
  - 参数/环境变量：以 `CONFIG` 为准（Teacher* 不讲调参）

- 避免复制粘贴
  - 同一段“目录树/输出结构/报错排障”只保留一处，其它文档用链接引用

- 变更联动清单（改代码时顺手检查）
  - 改 Work folder/入口文件名：同步 `TeacherQuickStart`、`TeacherGuide`
  - 改缓存结构/路径：同步 `CONFIG_REFERENCE`、`ArchitectureGuide`（必要时 `HealthCheck`）
  - 改环境变量：同步 `CONFIG_REFERENCE`、`HealthCheck`
  - 改发布产物结构：同步 `ReleaseFlow`、`ReleaseAcceptanceChecklist`

---

## 3) 交付与稳定性建议（当前项目口径）

- 交付门禁：发布前至少跑一次 `pytest -q`，发布严格模式跑 `REQUIRE_PACKAGED_ARTIFACTS=1 pytest -q`
- 离线/打包环境：避免第三方库联网检查噪声；遇到噪声优先做“静默/可控”处理（而不是让老师看到警告）
