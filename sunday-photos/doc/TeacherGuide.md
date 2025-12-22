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

## 快速示例
1) 将学生照放入 `input/student_photos/`（张三.jpg、李四.jpg）。
2) 将课堂照放入 `input/class_photos/2025-12-21/`。
3) 运行 `./SundaySchool --tolerance 0.55`。
4) 查看 `output/2025-12-21/`，按学生分好的照片即为结果。
