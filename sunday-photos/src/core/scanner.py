"""
Input directory scanner.
"""
import os
import shutil
import re
import logging
from pathlib import Path
from typing import List, Dict

from .utils.fs import (
    is_supported_nonempty_image_path,
    is_ignored_fs_entry,
)
from .utils.date_parser import get_photo_date, parse_date_from_text
from .incremental_state import (
    build_class_photos_snapshot,
    compute_incremental_plan,
    load_snapshot,
)

logger = logging.getLogger(__name__)

class Scanner:
    def __init__(self, photos_dir: Path, output_dir: Path, reporter):
        self.photos_dir = photos_dir
        self.output_dir = output_dir
        self.reporter = reporter
        self.incremental_plan = None

    def organize_input_by_date(self):
        """将上课照片根目录下的照片按日期移动到对应子目录"""
        self.reporter.log_info("STEP", "2a/4 归档输入照片（按日期整理）")
        photo_root = Path(self.photos_dir)
        if not photo_root.exists():
            logger.warning(f"输入目录不存在: {photo_root}")
            return

        def _unique_target_path(dest_dir: Path, src_name: str) -> tuple[Path, bool]:
            """生成不会覆盖的目标路径。

            返回：(target_path, renamed)
            - renamed=True 表示发生同名冲突，已自动改名
            """
            candidate = dest_dir / src_name
            if not candidate.exists():
                return candidate, False
            base = candidate.stem
            ext = candidate.suffix
            for i in range(1, 1000):
                alt = dest_dir / f"{base}_{i:03d}{ext}"
                if not alt.exists():
                    return alt, True
            # 极端情况下仍冲突：使用时间戳兜底
            import time

            alt = dest_dir / f"{base}_{int(time.time())}{ext}"
            return alt, True

        moved_count = 0
        renamed_count = 0
        failed_count = 0
        for file in photo_root.iterdir():
            if not is_supported_nonempty_image_path(file):
                continue
            try:
                photo_date = get_photo_date(str(file))
                date_dir = photo_root / photo_date
                date_dir.mkdir(exist_ok=True)

                target_path, renamed = _unique_target_path(date_dir, file.name)
                shutil.move(str(file), str(target_path))
                moved_count += 1
                if renamed:
                    renamed_count += 1
                    logger.warning(f"检测到同名照片，已自动改名并归档: {file.name} -> {target_path.name}")
            except Exception as e:
                failed_count += 1
                logger.exception(f"归档照片失败: {file}")

        if moved_count > 0 or failed_count > 0:
            msg = f"已归档 {moved_count} 张照片 → 日期子目录"
            if renamed_count:
                msg += f"（同名自动改名 {renamed_count} 张）"
            if failed_count:
                msg += f"；失败 {failed_count} 张（详见日志）"
            self.reporter.log_info("OK" if failed_count == 0 else "WARN", msg)
        else:
            self.reporter.log_info("OK", "输入照片已按日期整理，无需移动")

    def scan(self) -> List[str]:
        """扫描输入目录，返回“本次需要处理”的课堂照片列表。"""
        self.organize_input_by_date()
        self.reporter.log_rule()
        self.reporter.log_info("STEP", f"2/4 扫描输入目录: {self.photos_dir}")

        if not self.photos_dir.exists():
            logger.error(f"输入目录不存在: {self.photos_dir}")
            return []

        previous = load_snapshot(self.output_dir)
        current = build_class_photos_snapshot(self.photos_dir)
        plan = compute_incremental_plan(previous, current)
        self.incremental_plan = plan

        if previous is None:
            self.reporter.log_info("INFO", "未找到增量快照（首次运行），将处理全部日期文件夹")

        if plan.deleted_dates:
            deleted_line = ", ".join(sorted(plan.deleted_dates))
            self.reporter.log_info("SYNC", f"检测到删除日期，将同步清理输出: {deleted_line}")

        if plan.changed_dates:
            changed_line = ", ".join(sorted(plan.changed_dates))
            self.reporter.log_info("PLAN", f"检测到变更日期，将仅处理: {changed_line}")
        else:
            self.reporter.log_info("PLAN", "未检测到新增或变更的日期文件夹")

        # 兼容多种“日期文件夹写法”
        date_to_dirs: Dict[str, List[Path]] = {}
        try:
            for child in self.photos_dir.iterdir():
                if is_ignored_fs_entry(child):
                    continue
                if not child.is_dir():
                    continue
                normalized = parse_date_from_text(child.name)
                if not normalized:
                    continue
                date_to_dirs.setdefault(normalized, []).append(child)

            # 第二轮：识别嵌套 YYYY/MM/DD 结构
            for year_dir in self.photos_dir.iterdir():
                if is_ignored_fs_entry(year_dir) or (not year_dir.is_dir()):
                    continue
                if not re.fullmatch(r"\d{4}", year_dir.name or ""):
                    continue
                for month_dir in year_dir.iterdir():
                    if is_ignored_fs_entry(month_dir) or (not month_dir.is_dir()):
                        continue
                    if not re.fullmatch(r"\d{1,2}", month_dir.name or ""):
                        continue
                    for day_dir in month_dir.iterdir():
                        if is_ignored_fs_entry(day_dir) or (not day_dir.is_dir()):
                            continue
                        if not re.fullmatch(r"\d{1,2}", day_dir.name or ""):
                            continue

                        normalized = parse_date_from_text(f"{year_dir.name}/{month_dir.name}/{day_dir.name}")
                        if not normalized:
                            continue
                        date_to_dirs.setdefault(normalized, []).append(day_dir)
        except Exception:
            date_to_dirs = {}

        photo_files = []
        for date in sorted(plan.changed_dates):
            for date_dir in sorted(date_to_dirs.get(date, []), key=lambda p: p.name):
                for root, _, files in os.walk(date_dir):
                    for file in files:
                        p = Path(root) / file
                        if is_supported_nonempty_image_path(p):
                            photo_files.append(str(p))

        self.reporter.log_info("STAT", f"本次需要处理 {len(photo_files)} 张照片")
        return photo_files
