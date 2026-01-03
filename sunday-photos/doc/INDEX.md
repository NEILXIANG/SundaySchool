# 文档索引（权威入口）

**版本**: v0.4.0  
**更新日期**: 2026-01-02

目标：减少重复、统一口径、让项目更稳定、便于维护。

---

## 1. 快速按角色查找

| 我是... | 看这份文档 | 用时 |
|--------|----------|-----|
| **老师**（只想照做）| [TeacherQuickStart.md](TeacherQuickStart.md) | 5 分钟 |
| **老师**（需要解释/FAQ） | [TeacherGuide.md](TeacherGuide.md) + [FAQ.md](FAQ.md) | 20 分钟 |
| **老师**（遇到问题） | [HealthCheck_Runtime.md](HealthCheck_Runtime.md) 或 [FAQ.md](FAQ.md) | 5-10 分钟 |
| **技术同工**（调参/排障） | [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) + [FAQ.md](FAQ.md) | 15 分钟 |
| **技术同工**（诊断问题） | [HealthCheck_Runtime.md](HealthCheck_Runtime.md) + logs/ | 10 分钟 |
| **开发者**（理解架构） | [ArchitectureGuide.md](ArchitectureGuide.md) | 30 分钟 |
| **开发者**（本地开发） | [DeveloperGuide.md](DeveloperGuide.md) | 30 分钟 |
| **开发者**（写配置） | [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) + [EXAMPLES.md](EXAMPLES.md) | 20 分钟 |
| **发布维护者**（打包） | [ReleaseFlow.md](ReleaseFlow.md) | 30 分钟 |
| **发布维护者**（验收） | [ReleaseAcceptanceChecklist.md](ReleaseAcceptanceChecklist.md) + [HealthCheck_Release.md](HealthCheck_Release.md) | 1 小时 |

---

## 2. 完整文档清单

### 用户文档（👩‍🏫 老师与非技术同工）

| 文档 | 用途 |
|-----|------|
| [TeacherQuickStart.md](TeacherQuickStart.md) / [TeacherQuickStart_en.md](TeacherQuickStart_en.md) | 3 步上手 |
| [TeacherGuide.md](TeacherGuide.md) / [TeacherGuide_en.md](TeacherGuide_en.md) | 深入使用、最佳实践 |
| [FAQ.md](FAQ.md) / [FAQ_en.md](FAQ_en.md) | 快速问题查阅 |
| [EXAMPLES.md](EXAMPLES.md) / [EXAMPLES_en.md](EXAMPLES_en.md) | 权威示例与配置 |
| [HealthCheck_Runtime.md](HealthCheck_Runtime.md) / [HealthCheck_Runtime_en.md](HealthCheck_Runtime_en.md) | 运行时故障诊断 |
| [HealthCheck_Release.md](HealthCheck_Release.md) / [HealthCheck_Release_en.md](HealthCheck_Release_en.md) | 发布验收清单 |

### 开发文档（🛠️ 开发者与维护者）

| 文档 | 用途 |
|-----|------|
| [ArchitectureGuide.md](ArchitectureGuide.md) / [ArchitectureGuide_en.md](ArchitectureGuide_en.md) | 系统设计、模块原理 |
| [DeveloperGuide.md](DeveloperGuide.md) / [DeveloperGuide_en.md](DeveloperGuide_en.md) | 本地开发、测试、打包 |
| [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) / [CONFIG_REFERENCE_en.md](CONFIG_REFERENCE_en.md) | **SSOT**: 所有参数、优先级、环境变量 |
| [TESTING.md](TESTING.md) / [TESTING_en.md](TESTING_en.md) | 运行测试、覆盖率 |
| [LoggingStandards.md](LoggingStandards.md) / [LoggingStandards_en.md](LoggingStandards_en.md) | 日志格式、排障指南 |
| [OPTIMIZATION_SUMMARY_20260102.md](OPTIMIZATION_SUMMARY_20260102.md) | 文档体系优化总结（2026-01-02） |

### 运维文档（📦 发布与部署）

| 文档 | 用途 |
|-----|------|
| [ReleaseFlow.md](ReleaseFlow.md) / [ReleaseFlow_en.md](ReleaseFlow_en.md) | 打包步骤、CI/CD 流程 |
| [DeploymentGuide.md](DeploymentGuide.md) / [DeploymentGuide_en.md](DeploymentGuide_en.md) | 离线部署、配置管理 |
| [ReleaseAcceptanceChecklist.md](ReleaseAcceptanceChecklist.md) / [ReleaseAcceptanceChecklist_en.md](ReleaseAcceptanceChecklist_en.md) | 发布前检查 |

### 产品文档（📋 需求与决策）

| 文档 | 用途 |
|-----|------|
| [PRD.md](PRD.md) / [PRD_en.md](PRD_en.md) | 功能需求、非功能指标 |

---

## 3. 文档治理规则（强制）

### 3.1 单一事实来源（SSOT）清单

以下内容在对应文档中定义，其他文档只能引用，**严禁复制粘贴**：

| 内容 | SSOT 文档 |
|-----|----------|
| **目录结构示例** | [EXAMPLES.md](EXAMPLES.md) |
| **配置字段详解** | [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) |
| **环境变量清单** | [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) |
| **命令行示例** | [EXAMPLES.md](EXAMPLES.md) / [DeveloperGuide.md](DeveloperGuide.md) |
| **Work folder 说明** | [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) + [HealthCheck_Runtime.md](HealthCheck_Runtime.md) |
| **缓存结构与路径** | [ArchitectureGuide.md](ArchitectureGuide.md) |
| **老师操作步骤** | [TeacherQuickStart.md](TeacherQuickStart.md) |
| **常见问题与解决方案** | [FAQ.md](FAQ.md) |
| **参考照要求** | [TeacherQuickStart.md](TeacherQuickStart.md) + [TeacherGuide.md](TeacherGuide.md) |
| **发布流程步骤** | [ReleaseFlow.md](ReleaseFlow.md) |

### 3.2 引用而非复制规则

**❌ 错误做法**（重复描述）：
```markdown
## input 目录结构
input/
├── student_photos/
│   └── Alice/
...
```

**✅ 正确做法**（链接引用）：
```markdown
## input 目录结构
详见 [EXAMPLES.md#1-input-目录结构](EXAMPLES.md#1-input-目录结构)
```

### 3.3 变更联动清单（代码改动时检查）

| 改动内容 | 同步清单 |
|--------|--------|
| Work folder 逻辑 | TeacherQuickStart, TeacherGuide, CONFIG_REFERENCE, HealthCheck |
| 参数/配置字段 | CONFIG_REFERENCE, EXAMPLES, ArchitectureGuide |
| 环境变量 | CONFIG_REFERENCE, HealthCheck, DeveloperGuide |
| 版本号/发布日期 | 所有文档头部 |
| 缓存结构/路径 | ArchitectureGuide, HealthCheck, CONFIG_REFERENCE |
| 打包产物结构 | ReleaseFlow, ReleaseAcceptanceChecklist, HealthCheck |

---

## 4. 编辑工作流

### 编辑前检查

- [ ] 这个改动属于哪份文档？
- [ ] 是否违反了某个 SSOT 规则？
- [ ] 对应的英文版本需要同步吗？
- [ ] 版本号和日期是否正确？

### 编辑后检查

- [ ] 所有链接是否有效？
- [ ] 表格对齐？
- [ ] 代码块语法高亮？
- [ ] 中英版本对齐？

---

## 📞 有问题？

- 📖 查看快速索引表（第 1 节）
- 🔍 Ctrl+F 搜索关键词
- 💬 在 Issues 中提问

**最后更新**: 2026-01-02
