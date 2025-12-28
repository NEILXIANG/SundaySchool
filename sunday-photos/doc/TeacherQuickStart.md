# 老师快速开始（macOS / Windows）

这份说明是给老师的：**不需要懂电脑**，照做即可。

## 你需要准备什么

- 一份“学生参考照”（用于识别每位学生）
- 一份“课堂/活动照片”（需要整理的照片）

## 3 步完成（最重要）

### 第 1 步：解压
1. 下载老师发给你的压缩包
2. 解压到桌面（推荐）

（截图占位：解压后桌面上出现一个文件夹）

### 第 2 步：把照片放进 input
打开解压后的文件夹，找到：
- `input/student_photos/`：放**学生参考照**（每个学生一个文件夹，每人 1~5 张，清晰正脸最好）
- `input/class_photos/`：放**课堂/活动照**（你今天拍的所有合照/抓拍）

示例（你可以照着理解，不需要完全一样）：
- `input/student_photos/张三/张三_1.jpg`
- `input/student_photos/张三/张三_2.jpg`
- `input/student_photos/李四/李四_1.jpg`
- `input/class_photos/2025-12-25_圣诞活动_001.jpg`
- `input/class_photos/2025-12-25_圣诞活动_002.jpg`

（截图占位：input 目录下有 student_photos 和 class_photos 两个文件夹）

### 第 3 步：运行（只点一个入口）
在解压后的文件夹里，找到并运行：

- macOS：双击 `SundayPhotoOrganizer.app`（推荐）或双击 `启动工具.sh`
- Windows：双击 `Launch_SundayPhotoOrganizer.bat`

运行中：会弹出一个黑色窗口并显示进度，**请不要关闭**。

（截图占位：运行中黑色窗口显示进度）

## 结果在哪里

- 整理结果在：`output/`
- 运行日志在：`logs/`

更多说明（一般用不上）：
- 详细老师指南：`doc/TeacherGuide.md`
- 配置与高级选项：`doc/CONFIG.md`

（截图占位：output 文件夹里出现整理后的结果）

## 最常见问题（看这里就够了）

### 1) macOS 提示“无法打开，因为无法验证开发者”
这是 macOS 的安全提示，不是你操作错。

处理方法（两种任选其一）：

A. 系统设置方式（推荐）
1. 先点“取消”
2. 打开「系统设置」→「隐私与安全性」
3. 往下翻，找到“已阻止打开 SundayPhotoOrganizer”或“SundayPhotoOrganizer.app”
4. 点“仍要打开（Open Anyway）”
5. 回到文件夹，再双击运行一次

（截图占位：隐私与安全性页面的“仍要打开”按钮）

B. 右键打开方式
1. 右键 `SundayPhotoOrganizer` → 选择「打开」
2. 再点一次「打开」确认

（截图占位：右键菜单里的“打开”）

### 2) 双击后窗口一闪就没了 / 没反应
请按顺序检查：
1. 确认照片放在 `input/student_photos/` 和 `input/class_photos/`
2. 确认你点的是入口（macOS 点 `SundayPhotoOrganizer.app` 或 `启动工具.sh`；Windows 点 `.bat`）
3. 仍不行：把 `logs/` 文件夹发给技术同工

## 如果出错，你只需要发我两样东西

1. `logs/` 文件夹（整个打包发我）
2. 你看到的报错截图（如果有）

---

给老师的一句话总结：
- “解压 → 放照片到 input → 点运行 → 去 output 拿结果；有问题发 logs。”
