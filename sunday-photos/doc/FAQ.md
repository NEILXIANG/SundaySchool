# 常见问题（FAQ）& 故障排查

**版本**: v0.4.0  
**更新日期**: 2026-01-02

快速问题查阅。如需详细解释，请参考相应的文档链接。

---

## 目录

1. [安装与启动](#1-安装与启动)
2. [识别与整理](#2-识别与整理)
3. [配置与优化](#3-配置与优化)
4. [高级问题](#4-高级问题)
5. [故障排查](#5-故障排查)

---

## 1. 安装与启动

### Q1: macOS 提示"无法打开，因为无法验证开发者"

**A**: 这是 macOS 的安全提示（Gatekeeper）。解决方法：

**选项 A：系统设置（推荐）**
1. 点击"取消"
2. 打开「系统设置」→「隐私与安全性」
3. 往下翻，找到"已阻止打开 SundayPhotoOrganizer"或"SundayPhotoOrganizer.app"
4. 点"仍要打开（Open Anyway）"
5. 回到文件夹，再双击运行一次

**选项 B：右键打开方式**
1. 右键 `SundayPhotoOrganizer` → 选择「打开」
2. 再点一次「打开」确认

**选项 C：终端绕过**
```bash
xattr -dr com.apple.quarantine /path/to/SundayPhotoOrganizer.app
./path/to/SundayPhotoOrganizer
```

详见：[老师快速开始](TeacherQuickStart.md#1-macOS-提示无法打开因为无法验证开发者)

---

### Q2: Windows 运行时提示缺少某个 DLL 或库

**A**: 通常是缺少 Visual C++ Runtime 或其他系统库。

**解决**:
1. 下载并安装 [Microsoft Visual C++ Redistributable](https://support.microsoft.com/en-us/help/2977003)
2. 重启计算机
3. 重新运行程序

如问题仍存在，请收集 `logs/` 文件夹发给技术同工。

---

### Q3: Python 环境错误（ImportError、ModuleNotFoundError）

**A**: 说明依赖没有安装。

**解决**:
```bash
# 重新安装依赖
pip install -r requirements.txt

# 如果要使用 dlib 后端
pip install -r requirements-dlib.txt

# 重新运行
python src/cli/run.py
```

详见：[DeveloperGuide](DeveloperGuide.md)

---

## 2. 识别与整理

### Q4: 某个学生的照片没有被识别（全部进入 unknown_photos）

**A**: 可能的原因和解决方案：

| 原因 | 检查方法 | 解决方案 |
|-----|--------|--------|
| 参考照质量不佳 | 参考照是否清晰、光线好、是正脸？| 添加更多清晰的正脸参考照 |
| 参考照数量太少 | 每个学生有几张参考照？| 建议每人 2-5 张参考照 |
| 课堂照光线差/角度奇怪 | 课堂照是否清晰？| 如果照片本身不清晰，程序识别会困难 |
| 阈值设置太严格 | `tolerance` 设置是多少？| 尝试将 tolerance 从 0.6 改为 0.65 |
| 学生在照片中太小 | 学生在课堂照中占比多大？| 学生应该占比 1/3 以上，否则难以识别 |

**快速调整阈值**:
```json
{
  "tolerance": 0.65
}
```

详见：[CONFIG_REFERENCE](CONFIG_REFERENCE.md)、[TeacherGuide](TeacherGuide.md)

---

### Q5: 识别成功了，但有些照片分类错了（识别到了错误的学生）

**A**: 这通常是识别置信度接近阈值边界。

**解决**:
1. **收紧阈值**（更严格）：
   ```json
   {
     "tolerance": 0.55
   }
   ```
   这会减少误判，但可能增加漏识（进入 unknown）。

2. **改进参考照**：
   - 添加更多清晰的参考照
   - 移除质量不佳的参考照

3. **查看整理报告**：
   - 在 `output/*_整理报告.txt` 中查看识别置信度
   - 帮助判断是否需要调整阈值

详见：[TeacherGuide](TeacherGuide.md)

---

### Q6: "Unknown_Person_X" 文件夹是什么？

**A**: 这是程序自动聚类的"相似未知人脸"。

- 当某个人脸无法匹配到已知学生时，程序会尝试聚类
- 多个相似未知人脸会自动归组到 `Unknown_Person_1/`、`Unknown_Person_2/` 等
- 这通常是访客、家长、或识别失败的学生

**处理方式**：
- 快速查看这些照片，看是否有遗漏的学生
- 如果确实是学生，则重新添加参考照，重新运行程序

详见：[HealthCheck_Runtime](HealthCheck_Runtime.md)

---

## 3. 配置与优化

### Q7: 程序很慢，如何加速？

**A**: 几个加速策略：

| 策略 | 效果 | 代价 |
|-----|------|------|
| 启用并行处理（默认已启用） | 高 | CPU 占用高 |
| 增加并行进程数 `workers` | 中 | 内存占用增加 |
| 禁用未知人脸聚类 | 中 | 无法自动聚类未知人脸 |
| 减少参考照数量 | 低 | 识别精度可能下降 |
| 换更快的 GPU/CPU 机器 | 高 | 成本高 |

**配置示例**：
```json
{
  "parallel_recognition": {
    "enabled": true,
    "workers": 8,
    "min_photos": 20
  },
  "unknown_face_clustering": {
    "enabled": false
  }
}
```

详见：[CONFIG_REFERENCE](CONFIG_REFERENCE.md)

---

### Q8: 如何切换人脸识别后端（InsightFace ↔ dlib）？

**A**: 三种方式：

**方式 1：修改 config.json**
```json
{
  "face_backend": {
    "engine": "dlib"
  }
}
```

**方式 2：环境变量（优先级最高）**
```bash
export SUNDAY_PHOTOS_FACE_BACKEND=dlib
python src/cli/run.py
```

**方式 3：CLI 参数（仅限源码运行）**
```bash
python src/cli/run.py --face-backend dlib
```

**哪个后端更好**？
- **InsightFace**（默认）：精度高，速度快（需要 GPU 最优），推荐
- **dlib**：精度中等，速度较慢，仅作备选

详见：[CONFIG_REFERENCE](CONFIG_REFERENCE.md)

---

## 4. 高级问题

### Q9: 如何在离线/便携场景运行？

**A**: 使用 `SUNDAY_PHOTOS_WORK_DIR` 环境变量强制指定工作目录。

```bash
# macOS/Linux：从 USB 盘运行
export SUNDAY_PHOTOS_WORK_DIR=/Volumes/USB/SundayPhotos
python /Volumes/USB/sunday-photos/src/cli/run.py

# Windows：从 USB 盘运行（PowerShell）
$env:SUNDAY_PHOTOS_WORK_DIR = "D:\SundayPhotos"
D:\sunday-photos\python src\cli\run.py
```

这样程序会在指定位置创建 `input/`、`output/`、`logs/` 目录。

详见：[CONFIG_REFERENCE](CONFIG_REFERENCE.md#3-环境变量完整清单)

---

### Q10: 如何仅运行诊断，不处理照片？

**A**: 使用诊断模式启动。

```bash
# macOS/Linux
export SUNDAY_PHOTOS_DIAG_ENV=1
python src/cli/run.py --check-env

# Windows（PowerShell）
$env:SUNDAY_PHOTOS_DIAG_ENV = "1"
python src\cli\run.py --check-env
```

这会输出系统信息、依赖状态、配置加载情况，但不处理照片。

---

### Q11: 程序支持哪些图片格式？

**A**: 支持以下格式：

```
.jpg, .jpeg, .png, .bmp, .tiff, .webp
```

- JPEG 和 PNG 最常见，推荐使用
- WebP 现代浏览器支持，但老照片系统可能不支持
- BMP 和 TIFF 支持但不常用

---

## 5. 故障排查

### Q12: 程序突然崩溃或异常退出，怎么排查？

**A**: 按以下顺序排查：

**第 1 步：查看 logs/ 文件夹**
```bash
# 查看最新的日志
ls -lt logs/ | head
cat logs/sunday_photos_YYYYMMDD.log  # 查看详细日志
```

**第 2 步：常见原因**
| 错误信息 | 原因 | 解决方案 |
|--------|------|--------|
| `Permission denied` | 权限不足 | 检查输入/输出目录权限 |
| `Out of memory` | 内存不足 | 禁用并行处理：`"parallel_recognition": { "enabled": false }` |
| `ModuleNotFoundError` | 缺少依赖 | 重新安装：`pip install -r requirements.txt` |
| `libopenblas not found` | GPU/数学库缺失 | 重装 dlib：`pip install --upgrade dlib` |

**第 3 步：如果仍无法解决**
- 收集以下信息发给技术同工：
  1. 完整的 `logs/` 文件夹
  2. `config.json` 内容
  3. 操作系统版本
  4. Python 版本（`python --version`）

---

### Q13: 文件放进 input 后，程序没有处理

**A**: 检查以下几点：

1. **检查目录结构**：
   ```
   ✅ input/student_photos/Alice/ref.jpg      （正确）
   ✅ input/class_photos/2026-01-01/photo.jpg （正确）
   ❌ input/photo.jpg                         （错误：没有放在 class_photos）
   ❌ input/class_photos/Alice/photo.jpg      （错误：学生照应放在 student_photos）
   ```

2. **检查文件格式**：
   ```bash
   # 确保是支持的格式
   ls input/student_photos/Alice/*.jpg
   ls input/class_photos/2026-01-01/*.jpg
   ```

3. **检查权限**：
   ```bash
   # macOS/Linux
   ls -la input/
   chmod -R u+rwx input/  # 确保可读
   ```

4. **查看运行日志**：
   ```bash
   cat logs/sunday_photos_*.log | grep "input"
   ```

详见：[TeacherQuickStart](TeacherQuickStart.md)

---

### Q14: 整理完成后，output 目录是空的

**A**: 可能的原因：

| 原因 | 现象 | 解决 |
|-----|------|------|
| 没有学生参考照 | `input/student_photos/` 为空 | 添加学生参考照 |
| 没有课堂照 | `input/class_photos/` 为空 | 添加课堂照片 |
| 所有照片都进入 unknown | `output/unknown_photos/` 有文件，但 `output/<学生名>/` 为空 | 查看 Q4 解决方案 |
| 图片识别全失败 | logs 中全是 error | 查看 Q12 排查流程 |

---

### Q15: 如何回收磁盘空间？可以删除 logs/ 吗？

**A**: 可以，但要谨慎。

**安全操作**：
```bash
# 只保留最近 7 天的日志
find logs/ -type f -mtime +7 -delete

# 或完全清空（但会丢失诊断信息）
rm -rf logs/*
```

**不要删除**：
```bash
output/.state/                  # 增量处理状态（删除会重新处理所有照片）
logs/reference_encodings/       # 参考照缓存（删除会重新生成，更慢）
logs/reference_index/           # 参考照索引（同上）
```

详见：[HealthCheck_Runtime](HealthCheck_Runtime.md)

---

## 相关资源

- **详细指南**: [TeacherGuide.md](TeacherGuide.md)
- **配置参考**: [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)
- **示例**: [EXAMPLES.md](EXAMPLES.md)
- **健康检查**: [HealthCheck_Runtime.md](HealthCheck_Runtime.md)
- **开发指南**: [DeveloperGuide.md](DeveloperGuide.md)（如需深入了解技术细节）

---

**问题未解决？**

- 📧 查看 logs/ 文件夹中的详细日志
- 💬 在项目 Issues 中提问
- 👥 与技术同工联系
