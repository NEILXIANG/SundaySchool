# 🎓 主日学照片整理工具 - 部署指南（控制台版）

**版本**: v0.4.0  
**更新日期**: 2025-12-23

## 📦 发布交付物

控制台/命令行分发，位于 `release_console/` 目录：

1. **SundayPhotoOrganizer** (macOS 可执行文件，已设置执行权限)
2. **SundayPhotoOrganizer.exe** (Windows 可执行文件)
3. **启动工具.sh** (macOS 启动脚本；可双击或终端运行)
4. **Launch_SundayPhotoOrganizer.bat** (Windows 启动脚本；双击运行)
5. **使用说明.txt** (中文用户指南)
6. **USAGE_EN.txt** (英文用户指南)

分发给老师时，请保持这些文件在同一目录下。

## 📂 目录结构概览

### 源码目录结构
```
sunday-photos/                 # 项目根目录
├── release_console/           # 打包交付目录
├── input/                     # 源码模式输入目录
│   ├── student_photos/        # 学生参考照（格式：student_photos/<学生名>/...）
│   └── class_photos/          # 课堂照片（建议按日期分子目录）
├── output/                    # 源码模式输出目录
│   ├── Alice/2024-12-21/...   # 按学生→日期分层
│   └── unknown_photos/...     # 未识别照片
├── logs/                      # 源码模式日志目录
├── src/                       # 源代码（核心、CLI、UI、工具脚本）
├── tests/                     # 自动化测试（包括打包验证、教师友好测试）
├── doc/                       # 文档目录
├── run.py                     # 开发模式入口脚本
├── run_all_tests.py           # 全量测试脚本
└── requirements.txt           # Python 依赖声明
```

### 运行期自动创建（与可执行文件同目录）
首次运行时，程序会在可执行文件同目录自动创建：
```
./input/
├── student_photos/            # 学生参考照（每个学生一个文件夹）
└── class_photos/              # 课堂照片（建议按日期分子目录，如 2024-12-21/）
./output/                      # 整理结果（按学生/日期/照片.jpg 结构）
./logs/                        # 运行日志（可定期清空）
```
若程序所在目录不可写：会自动回退到桌面（或主目录），并在控制台提示实际路径。

### 📥 输入目录示例（源码模式）
```
input/
├── student_photos/
│   ├── Alice/                 # 每个学生一个文件夹
│   │   ├── ref_01.jpg         # 参考照文件名可随意
│   │   └── ref_02.png
│   └── Bob/
│       └── img_0001.jpg
└── class_photos/
    ├── 2024-12-21/            # 建议按日期建子目录
    │   ├── group_photo.jpg
    │   └── game_time.png
    └── 2024-12-28/
        └── discussion.jpg
```

### 📤 输出目录示例（整理后）
```
output/
├── Alice/                     # 每个学生独立文件夹
│   ├── 2024-12-21/            # 按日期分层
│   │   ├── group_photo_103045.jpg
│   │   └── game_time_104823.jpg
│   └── 2024-12-28/
│       └── discussion_101010.jpg
├── Bob/
│   └── 2024-12-21/
│       └── group_photo_103045.jpg
└── unknown_photos/            # 未识别照片
    ├── Unknown_Person_1/      # 🆕 v0.4.0 相似人脸自动归组
    │   └── 2024-12-21/
    │       ├── visitor_a.jpg
    │       └── visitor_b.jpg
    └── 2024-12-21/            # 单次出现的人脸
        └── blurry_105632.jpg
```

## 🚀 老师使用流程

### 目录说明
- **release_console/**: 打包交付目录（包含可执行文件、启动脚本、使用说明）
- **可执行文件同目录** (首次运行自动创建):
  - `input/student_photos/`: 学生参考照（每人一个文件夹）
  - `input/class_photos/`: 课堂照片（建议按日期建子目录）
  - `output/`: 整理结果（自动按学生→日期分层）
  - `logs/`: 运行日志

### 输入规则（源码运行场景）
- **默认输入根目录**: `input/`
- **学生参考照**: 放在 `input/student_photos/`
  - 文件夹模式：每个学生创建一个文件夹 `input/student_photos/<学生名>/`
  - 在学生文件夹内放入该学生的参考照（文件名可随意）
  - 每个学生建议 2-5 张清晰照片（程序最多使用 5 张）
  - 示例：`input/student_photos/Alice/ref_01.jpg`, `input/student_photos/Bob/img_0001.jpg`
  
- **课堂照片**: 放在 `input/class_photos/`，建议按日期建子目录
  - 示例：`input/class_photos/2024-12-21/group_photo.jpg`
  - 如不分日期，也可直接放在 `class_photos/` 根目录，程序会按检测到的日期自动归档
  
- **输出**: 自动写入 `output/`，按学生→日期分层，并生成整理报告

## ▶️ 启动方式

### macOS
- **双击运行**: 双击 `release_console/SundayPhotoOrganizer` 或 `release_console/启动工具.sh`
- **终端运行**: `./release_console/SundayPhotoOrganizer` (如需要先执行 `chmod +x`)

**首次运行提示**: 如果 macOS 阻止运行，请前往"系统设置 → 隐私与安全性"选择"仍要打开"。

### Windows
- **双击运行**: 双击 `release_console/SundayPhotoOrganizer.exe` 或 `release_console/Launch_SundayPhotoOrganizer.bat`

**注意**: 较旧的构建版本可能使用目录布局（如 `release_console/SundayPhotoOrganizer/SundaySchool`）。当前版本使用单文件模式：`release_console/SundayPhotoOrganizer`。

## 🧪 验证与测试

### 打包验证
- **控制台打包验收测试**: `tests/test_console_app.py`, `tests/test_packaged_app.py`
- **全量回归测试**: `python run_all_tests.py`

### 发布验收清单
详见 [ReleaseAcceptanceChecklist.md](ReleaseAcceptanceChecklist.md)，包括：
1. ✅ 可执行文件存在且可运行
2. ✅ 启动脚本正常工作
3. ✅ 使用说明文档完整
4. ✅ 全量测试通过（pytest 全绿）
5. ✅ 手动验证核心流程

## 💡 使用技巧

### 提高识别准确率
- 每个学生提供 2-5 张清晰的参考照片
- 参考照要求：清晰、正脸、无遮挡、光线充足
- 避免使用多人合照作为参考照

### 常见问题处理
- **提示照片缺失**: 检查文件夹名称和文件命名是否正确
- **识别不准确**: 补充高质量参考照片
- **程序运行缓慢**: 照片数量较多时，建议启用并行识别（在配置中设置）

### 增量处理
- 可以安全地多次运行程序
- 程序会自动识别并处理新增的照片
- 已处理的照片会被跳过（通过缓存机制）

## 🔧 边界情况处理

程序已针对以下情况进行优化：
- ✅ 空文件夹：自动跳过，不影响运行
- ✅ 重复照片：智能去重，保持运行稳定
- ✅ 无人脸照片：归入 unknown_photos，不中断流程
- ✅ 格式错误：自动跳过不支持的格式

## 🆕 v0.4.0 新特性

### 未知人脸智能聚类
- 自动将相似的未知人脸归为一组（如访客、家长、新学生）
- 输出到 `unknown_photos/Unknown_Person_1/`, `Unknown_Person_2/` 等
- 应用场景：
  - 访客管理：多次来访的家长自动归组
  - 新生识别：经常出现的未知人脸可能是新学生
  - 志愿者追踪：定期参与者的照片集中管理

详细配置见 [CONFIG.md](CONFIG.md) 的 `unknown_face_clustering` 章节。

## 🔨 架构优化

### 模块化更新
- **核心模块**: 新增 `config` 子模块，提升配置管理可维护性
- **UI模块**: 新增 `validators` 和 `guides` 子模块，改善代码组织
- **测试覆盖**: 用例数随迭代增长，覆盖核心功能、性能、用户体验、打包部署

### 性能优化
- **智能并行识别**: 大批量照片（如 50+张）自动建议启用并行，通常可明显加速（取决于机器与照片规模）
- **多层缓存**: L1 内存缓存 + L2 磁盘缓存 + L3 增量快照，二次运行通常更快（取决于缓存命中与变更比例）
- **增量处理**: 只处理新增或变更的照片，节省时间

## 📚 相关文档

- **用户指南**: [TeacherGuide.md](TeacherGuide.md) - 老师使用指南（详细三步流程）
- **配置说明**: [CONFIG.md](CONFIG.md) - 配置文件详解
- **开发指南**: [DeveloperGuide.md](DeveloperGuide.md) - 开发者手册
- **测试指南**: [TESTING.md](TESTING.md) - 测试套件说明
- **产品需求**: [PRD.md](PRD.md) - 产品需求文档
- **架构指南**: [ArchitectureGuide.md](ArchitectureGuide.md) - 技术架构详解

## 🛠️ 开发者相关

### 打包流程
- **macOS**: `bash scripts/build_mac_app.sh`
- **Windows**: `powershell scripts/build_windows_console_app.ps1`

详见 [DeveloperGuide.md](DeveloperGuide.md) 的打包章节。

### 环境要求
- Python 3.7-3.14
- 依赖库：face_recognition, dlib, opencv-python, Pillow 等
- 完整列表见 `requirements.txt`

---

*最后更新：2025-12-23 | 版本：v0.4.0*
