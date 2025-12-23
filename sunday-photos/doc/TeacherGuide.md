# 老师使用指南

适用对象：直接使用发布包的老师，不需要安装 Python。

## 获取与目录
- 从 GitHub Actions 下载对应芯片的压缩包：macos-x86_64（Intel）、macos-arm64（Apple Silicon）、windows-x86_64（Windows）。
- 解压后，进入 `release_console/SundayPhotoOrganizer/`（Windows 为 `dist/` 内可执行）。
- 关键目录（已预创建）：
  - `input/student_photos/` 学生参考照
  - `input/class_photos/` 课堂照片（可按日期子目录）
  - `output/` 分类结果
  - `logs/` 日志

## 照片准备
- 学生参考照：`姓名.jpg` 或 `姓名_序号.jpg`，清晰正脸（如：张三.jpg、张三_1.jpg）。
- 课堂照片：放入 `input/class_photos/`，可建 `2024-12-21/照片.jpg` 这类子目录。

## 增量处理（老师无感）
为避免每次都重复处理历史照片，程序会按“日期文件夹（YYYY-MM-DD）”自动增量：
- 新增一个日期文件夹：只处理这一天。
- 在原日期文件夹中补充/替换/删除照片：只重做这一天。
- 删除某个日期文件夹：会自动把 `output/` 中对应日期的结果一起清理。

提示：
- 如果不小心把课堂照直接放在 `input/class_photos/` 根目录，程序会尝试按日期自动归档到对应日期子目录。
- 程序会在 `output/.state/` 保存“上次处理到哪”的隐藏状态（请不要手动删除/改名）。

## 运行方式（macOS）
- 双击 `release_console/启动工具.sh`（如被拦截，右键“打开”或终端执行 `chmod +x release_console/启动工具.sh` 后双击）。
- 或终端进入 `release_console/SundayPhotoOrganizer`，执行 `./SundaySchool`，可选参数：
  - `--tolerance 0.6`（默认 0.6，数值越低越严格，可尝试 0.4–0.8）
  - `--input-dir input` / `--output-dir output` 自定义目录
- Windows：解压后，在 `dist/` 目录双击 `SundaySchool.exe`（首次运行如被拦截，选择“仍要运行”或允许权限）。

## 查看结果
- 整理完成后，在 `output/` 中按学生分好类；未识别照片也会集中在输出内。
- 日志位于 `logs/`，可用于排查。

## 常见问题
- 程序很快结束且无输出：确认 `class_photos` 里有 jpg/png 照片。
- 识别不准：为学生添加更多清晰正脸参考照，或将 `--tolerance` 调低到 0.5/0.45。
- 权限问题：给可执行文件或脚本加执行权限（macOS 终端 `chmod +x SundaySchool` 或 `chmod +x 启动工具.sh`）。
- 更新了学生参考照但识别结果似乎没变化：先再运行一次；如仍不对，可删除 `output/.state/recognition_cache_by_date/` 下对应日期的缓存文件后再运行（只影响那些日期）。
- 电脑较慢/卡顿：可以临时关闭并行识别（更稳但更慢），设置环境变量 `SUNDAY_PHOTOS_NO_PARALLEL=1` 后再运行。

## 快速示例
1) 将学生照放入 `input/student_photos/`（张三.jpg、李四.jpg）。
2) 将课堂照放入 `input/class_photos/2025-12-21/`。
3) 运行 `./SundaySchool --tolerance 0.55`。
4) 查看 `output/2025-12-21/`，按学生分好的照片即为结果。
