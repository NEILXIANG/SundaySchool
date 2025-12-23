# 主日学课堂照片自动整理工具 (优化版)

🎉 **专为非技术老师设计的照片自动整理工具，操作极其简单！**（纯控制台版本，无GUI）

---

## ✨ 新版特性

### 🎨 优化用户体验
- 彩色日志输出，清晰显示处理状态
- 友好的进度条和实时反馈
- 详细的统计信息和结果展示

### 🛡️ 增强错误处理
- 自动创建缺失目录
- 智能错误恢复机制
- 详细的错误提示和解决建议

### 🚀 提升性能
- 优化人脸识别算法
- 减少计算资源消耗
- 更快的处理速度

### ⚙️ 灵活配置
- 支持环境变量配置
- 内置合理默认识别阈值（老师无需调整）
- 多种文件命名方式

### 🧠 智能功能（规划中）
- 重复检测、质量分析、智能命名仍在规划中，当前版本未提供

---

## 📁 目录结构（含作用说明）

```
sunday-photos/
├── input/                      # 输入根目录
│   ├── student_photos/         # 学生参考照（folder-only: student_photos/<student_name>/...）
│   │   ├── Alice/              # Example student folder
│   │   │   ├── ref_01.jpg
│   │   │   └── ref_02.png
│   │   └── Bob/
│   │       └── img_0001.jpg
│   └── class_photos/           # 课堂照片（建议按日期子目录）
│       ├── 2024-12-21/         # 示例：按日期分子目录
│       │   └── group_photo.jpg
│       └── loose_photo.png     # 若不分日期也可直接放根目录
├── output/                     # 整理结果：学生/日期分层 + 报告
│   ├── Alice/2024-12-21/...    # 示例：学生/日期/照片
│   ├── unknown_photos/2024-12-21/... # 未匹配人脸的照片
│   └── 20241221_整理报告.txt    # 示例：自动生成的报告
├── logs/                       # 运行日志（可清空）
├── src/                        # 源码入口
│   ├── core/                   # 核心逻辑（配置、人脸识别、整理管线）
│   ├── cli/                    # 命令行入口脚本
│   ├── ui/                     # 交互式指导、教师助手
│   ├── scripts/                # 打包与辅助脚本
│   └── classroom/              # 示例/占位（课堂照片示例）
├── tests/                      # 自动化测试（含教师友好、打包验证）
│   └── legacy/                 # 历史测试样例（保留参考）
├── doc/                        # 文档（PRD、测试说明、部署说明等）
├── release_console/            # 控制台打包产物（可执行与启动脚本）
├── run.py                      # 根入口脚本（调用 src/main.py）
├── run_all_tests.py            # 一键运行全套测试
├── requirements.txt            # 依赖声明
└── README.md                   # 项目说明（当前文档）
```

### 📥 input 目录示例
```
input/
├── student_photos/
│   ├── Alice/
│   │   ├── ref_01.jpg
│   │   └── ref_02.jpg
│   └── Bob/
│       └── img_0001.png
└── class_photos/
   ├── 2024-12-21/
   │   ├── group_photo.jpg
   │   └── game_time.png
   └── 2024-12-28/
      └── discussion.jpg
```

### 📤 output 目录示例
```
output/
├── Alice/
│   ├── 2024-12-21/
│   │   ├── group_photo_103045.jpg
│   │   └── game_time_104823.jpg
│   └── 2024-12-28/
│       └── discussion_101010.jpg
├── Bob/
│   └── 2024-12-21/
│       └── group_photo_103045.jpg
└── unknown_photos/
   └── 2024-12-21/
   └── blurry_105632.jpg
```

**目录作用说明**
- input/: 放置所有输入照片；student_photos/ 为参考照，class_photos/ 为课堂照（建议按日期分子目录）。
- output/: 程序整理输出，按学生→日期分层，包含报告文件。
- logs/: 运行日志输出目录（可清空）。
- src/: 项目源码与模块。
- tests/: 自动化测试用例。
- doc/: 项目文档（PRD、测试说明等）。
- release_console/: 已打包的控制台版本及说明。

**input 目录示例（源码运行）**
```
input/
├── student_photos/          # Reference (folder-only): student_photos/<student_name>/...
│   ├── Alice/
│   │   ├── ref_01.jpg
│   │   └── ref_02.png
│   └── Bob/
│       └── img_0001.jpg
└── class_photos/            # 课堂照，建议按日期子目录
   ├── 2024-12-21/
   │   ├── group_photo.jpg
   │   └── game_time.png
   └── 2024-12-28/
      └── discussion.jpg
```

**output 目录示例（学生/日期分层）**
```
output/
├── Alice/
│   ├── 2024-12-21/
│   │   ├── group_photo_103045.jpg
│   │   └── game_time_104823.jpg
│   └── 2024-12-28/
│       └── discussion_101010.jpg
├── Bob/
│   └── 2024-12-21/
│       └── group_photo_103045.jpg
└── unknown_photos/
   └── 2024-12-21/
   └── blurry_105632.jpg
```


---

## 👩‍🏫 老师（打包版）使用（推荐，最少操作）

老师不需要安装 Python。请优先阅读老师指南：
- 中文：[doc/TeacherGuide.md](doc/TeacherGuide.md)
- English: [doc/TeacherGuide_en.md](doc/TeacherGuide_en.md)

补充文档：
- 发布前验收清单：[doc/ReleaseAcceptanceChecklist.md](doc/ReleaseAcceptanceChecklist.md)
- 反向 PRD（从现有实现倒推需求与边界）：[doc/PRD_reverse.md](doc/PRD_reverse.md)
- AI 提示词模板（用于后续迭代/修复）：[doc/AI_prompt_templates.md](doc/AI_prompt_templates.md)

### 1) 运行
- macOS：双击 `release_console/启动工具.sh`（推荐），或双击 `release_console/SundayPhotoOrganizer`

### 2) 放照片（只需要这一步）
首次运行会在桌面创建：`SundaySchoolPhotoOrganizer/`
- `student_photos/`：学生参考照（folder-only：`student_photos/<student_name>/...`，文件名随意）
- `class_photos/`：课堂照片（建议按日期子目录 `2025-12-21/group_photo.jpg`）

### 3) 再运行一次
整理完成后会自动打开 `output/`。

### 重要提示（避免“照片被移动”的惊吓）
- 程序可能会把 `class_photos` 根目录的照片按日期移动到 `YYYY-MM-DD/` 子目录，这是正常现象（为了增量处理与便于查找）。

---

## 🧑‍💻 开发者（源码运行）使用

### 第一步：准备学生照片
1. 📁 在 `input/student_photos/` 下为每个学生创建文件夹：`input/student_photos/<student_name>/`
2. 🏷️ 文件名随意（不用改名），每位学生最多使用 5 张（按修改时间取最新 5 张）
3. 📸 每个学生可以提供多张不同角度的参考照片

### 第二步：放入待整理照片
1. 📂 将课堂照片放入 `input/class_photos/` 目录，建议按日期创建子目录（如 `2024-12-21/照片.jpg`）
2. 📄 支持 JPG、PNG、BMP 等格式
3. 📅 照片会自动按日期整理到子目录

### 第三步：运行程序
```bash
# 基础使用
python run.py

# 带参数使用
python run.py --input-dir my_input --tolerance 0.65  # 兼容 --classroom-dir

# 查看帮助
python run.py --help
```

### 第四步：查看结果
1. ✨ 程序会自动在 `output/` 目录创建整理好的照片
2. 👥 每个学生都有自己的文件夹
3. 📅 照片按日期和活动自动分类
4. 📊 生成详细的整理报告和智能分析

---

## 🧪 测试与质量

- 运行全套测试：`python run_all_tests.py`
- 打包（macOS 控制台 onefile，可生成 release_console/SundayPhotoOrganizer）：`bash scripts/build_mac_app.sh`
- 打包产物强校验（发布前验收用）：`REQUIRE_PACKAGED_ARTIFACTS=1 python -m pytest -q`
   - 默认情况下，若未生成 `release_console/SundayPhotoOrganizer`，相关用例会自动跳过（不影响日常开发/CI）。
   - 也可以使用一键脚本：`python run_all_tests.py --require-packaged-artifacts`
- 主要测试文件在 [tests/](tests) 目录，涵盖：
   - 基础/修复/集成：如 [tests/test_basic.py](tests/test_basic.py)、[tests/test_integration.py](tests/test_integration.py)
   - 教师友好与上手流：如 [tests/test_teacher_friendly.py](tests/test_teacher_friendly.py)、[tests/test_teacher_onboarding_flow.py](tests/test_teacher_onboarding_flow.py)
   - 规模与打包验证：如 [tests/test_scalability_student_manager.py](tests/test_scalability_student_manager.py)、[tests/test_console_app.py](tests/test_console_app.py)
- 详见测试说明 [doc/TESTING.md](doc/TESTING.md)

---

## ⚙️ 配置（config.json）

标准 JSON 不支持注释。为了让配置“打开就能看懂”，本项目在 `config.json` 中使用 `_comment` / `xxx_comment` 字段存放说明文字，程序会忽略这些字段，文件仍然是合法 JSON。

- 中文配置说明：[doc/CONFIG.md](doc/CONFIG.md)
- English config guide: [doc/CONFIG_en.md](doc/CONFIG_en.md)

---

## 📋 输出结构

```
output/
├── Alice/                             # Student folder
│   ├── 2024-12-21_group_photo_103045.jpg
│   ├── 2024-12-21_discussion_103146.jpg
│   └── 2024-12-21_showcase_103254.jpg
├── Bob/
│   ├── 2024-12-21_group_photo_103045.jpg
│   └── 2024-12-21_game_time_104823.jpg
├── Charlie/
│   └── 2024-12-21_group_photo_103045.jpg
├── unknown_photos/                    # Unmatched photos
│   └── blurry_105632.jpg
├── 整理报告.txt                        # 基础整理报告
└── 智能分析报告.txt                    # 智能分析结果
```

---

## ⚙️ 配置选项

### 命令行参数
- `--input-dir`: 输入数据目录 (默认: input，兼容 --classroom-dir)
- `--output-dir`: 输出目录 (默认: output)
- `--tolerance`: 人脸识别阈值 (0-1, 默认: 0.6)
- `--help`: 显示帮助信息
- `--check-env`: 检查运行环境

### 识别阈值建议
- `0.4`: 更严格，但可能漏识别
- `0.6`: 平衡设置，推荐值
- `0.8`: 更宽松，但可能误识别

---

## 🛠️ 安装和依赖

说明：本节仅适用于“源码运行”。老师使用打包版不需要安装 Python 依赖。

### 系统要求
- Python 3.7 或更高版本
- Windows、macOS、Linux

### 安装依赖
```bash
pip install -r requirements.txt
```

### 主要依赖包
- `face_recognition`: 人脸识别核心库
- `pillow`: 图像处理
- `numpy`: 数值计算
- `tqdm`: 进度条显示

---

## 🧠 智能功能（规划中，当前版本未实现）

- 以下能力为规划路线，代码暂未实现：重复/相似检测、质量分析、智能命名。
- 如需这些功能，请在后续版本更新后再使用，或自行扩展对应模块。

---

## 📊 日志和报告

### 彩色日志
- 🟢 绿色：成功信息
- 🟡 黄色：警告信息
- 🔴 红色：错误信息
- 🔵 蓝色：调试信息

### 详细报告
- 📄 整理报告.txt：基础整理统计
- 🤖 智能分析报告.txt：智能分析结果
- 📝 日志文件：详细的处理过程

---

## 🎯 核心特点

### ✅ 简单易用
- ❌ 不需要CSV文件
- ✅ 打包版无需编辑配置文件或参数；源码版支持调参
- ❌ 不需要计算机知识
- ✅ 只需创建文件夹和放照片

### 🤖 智能识别
- ✅ 自动识别人脸并整理
- ✅ 支持多人合影自动分类
- ✅ 智能错误处理和恢复
- ✅ 性能优化和加速

### 📈 专业功能
- ⚠️ 重复照片检测（规划中）
- ⚠️ 图片质量分析（规划中）
- ⚠️ 智能文件命名（规划中）
- ✅ 详细的统计报告

---

## 🆘 常见问题

### Q: 人脸识别不准确怎么办？
A: 1) 给该学生补 2-3 张清晰正脸参考照（清晰、正脸、无遮挡）
   2) 参考照尽量“只拍这个学生一个人”，不要用多人合照当参考照
   3) 确保课堂照光线充足、人脸不要太小/太模糊（必要时换更清晰的原图）
   4) 开发者（源码）如需调参：可调整 `--tolerance` 参数（0.4-0.8之间）

### Q: 程序运行很慢？
A: 1) 检查照片文件大小，避免过大照片
   2) 使用更高性能的计算机
   3) 调整识别参数优化速度

### Q: 如何处理同名学生？
A: 1) 使用更具体的文件夹名 (如: "Alice_Senior")
   2) 在文件夹中放入唯一参考照片

### Q: 某些照片未被识别？
A: 1) 检查照片中是否包含清晰人脸
   2) 查看智能分析报告了解原因
   3) 适当降低识别阈值

---

## 📞 技术支持

如果遇到问题：
1. 🔍 老师（打包版）：查看桌面 `SundaySchoolPhotoOrganizer/logs/` 目录中最新的日志文件
2. 🔍 开发者（源码）：查看 `logs/` 目录中的日志文件
2. 📊 查看生成的分析报告
3. 💡 使用 `python run.py --help` 查看帮助
4. 🔄 尝试调整配置参数

---

**🎉 享受使用这个为您精心设计的照片整理工具！**