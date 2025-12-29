"""增量处理：隐藏状态快照（方案1）。

用途：
- 对 input/class_photos 按“日期文件夹（YYYY-MM-DD）”做快照；
- 通过对比前后快照，仅处理新增/变更的日期文件夹；
- 同步识别“被删除的日期文件夹”，用于清理输出目录中的对应日期数据。

设计取舍：
- 快照中只记录相对路径、文件大小、mtime（秒级），保持跨平台稳定。
- 0 字节图片会被忽略（视为无效输入），避免增量 diff 误报。
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .config import STATE_DIR_NAME, CLASS_PHOTOS_SNAPSHOT_FILENAME, SNAPSHOT_VERSION, DATE_DIR_PATTERN
from .utils.fs import is_supported_nonempty_image_path, is_ignored_fs_entry
from .utils.date_parser import parse_date_from_text


# 全局锁用于并发安全
_snapshot_lock = threading.Lock()


@dataclass(frozen=True)
class IncrementalPlan:
    changed_dates: Set[str]
    deleted_dates: Set[str]
    snapshot: Dict


def _state_dir(output_dir: Path) -> Path:
    return Path(output_dir) / STATE_DIR_NAME


def snapshot_file_path(output_dir: Path) -> Path:
    """返回快照文件路径（位于输出目录的隐藏状态目录下）。"""
    return _state_dir(output_dir) / CLASS_PHOTOS_SNAPSHOT_FILENAME


def iter_date_directories(class_photos_dir: Path) -> List[Path]:
    """枚举合法的日期子目录（YYYY-MM-DD）。

    说明：这是原有行为（也是增量处理的基线语义），用于保持向后兼容。
    多日期格式兼容逻辑在本模块内部快照构建中处理。
    """
    if not class_photos_dir.exists():
        return []
    date_dirs: List[Path] = []
    for child in class_photos_dir.iterdir():
        if is_ignored_fs_entry(child):
            continue
        if child.is_dir() and re.match(DATE_DIR_PATTERN, child.name):
            date_dirs.append(child)
    return sorted(date_dirs, key=lambda p: p.name)


def _iter_date_directories_multi_format(class_photos_dir: Path) -> List[tuple[str, Path]]:
    """枚举“可解析为日期”的子目录（多格式），用于构建快照。"""
    if not class_photos_dir.exists():
        return []
    date_dirs: List[tuple[str, Path]] = []
    for child in class_photos_dir.iterdir():
        if is_ignored_fs_entry(child):
            continue
        if not child.is_dir():
            continue
        normalized = parse_date_from_text(child.name)
        if not normalized:
            continue
        date_dirs.append((normalized, child))

    # 兼容嵌套目录：class_photos/YYYY/MM/DD/...
    for year_dir in class_photos_dir.iterdir():
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
                date_dirs.append((normalized, day_dir))

    return sorted(date_dirs, key=lambda it: (it[0], it[1].name))


def _file_entry(path: Path) -> Dict:
    stat = path.stat()
    # Use integer seconds for stable snapshots across platforms.
    return {
        "path": path.as_posix(),
        "size": int(stat.st_size),
        "mtime": int(stat.st_mtime),
    }


def build_class_photos_snapshot(class_photos_dir: Path) -> Dict:
    """为 input/class_photos 构建快照。

    快照结构：
    {
        version: int,
        generated_at: str,
        dates: {
            "YYYY-MM-DD": {
                source_dirs: ["2025-12-21", "2025.12.21", ...],
                files: [ {path,size,mtime}, ... ]
            },
            ...
        }
    }

    说明：输入端允许多种日期文件夹写法，但快照 key 一律标准化为 YYYY-MM-DD。
    """

    dates: Dict[str, Dict] = {}
    for normalized_date, date_dir in _iter_date_directories_multi_format(class_photos_dir):
        file_entries: List[Dict] = []
        for file_path in sorted(date_dir.rglob("*")):
            if is_supported_nonempty_image_path(file_path):
                rel = file_path.relative_to(date_dir).as_posix()
                entry = _file_entry(file_path)
                # 兼容：
                # - 若目录本身就是标准 YYYY-MM-DD，则沿用历史语义：path=相对日期目录路径（不带日期前缀）
                # - 若目录是其他写法（如 2025.12.23 / 2025年12月23日），则加上物理目录名前缀避免冲突
                if date_dir.name == normalized_date and re.match(DATE_DIR_PATTERN, date_dir.name):
                    entry["path"] = rel
                else:
                    physical_rel = date_dir.relative_to(class_photos_dir).as_posix()
                    entry["path"] = f"{physical_rel}/{rel}"
                file_entries.append(entry)

        bucket = dates.setdefault(normalized_date, {"source_dirs": [], "files": []})
        physical_rel = date_dir.relative_to(class_photos_dir).as_posix()
        if physical_rel not in bucket["source_dirs"]:
            bucket["source_dirs"].append(physical_rel)
        bucket["files"].extend(file_entries)

    # 保证稳定快照：排序 source_dirs 与 files
    for v in dates.values():
        v["source_dirs"] = sorted(set(v.get("source_dirs", [])))
        v["files"] = sorted(
            v.get("files", []),
            key=lambda e: (e.get("path", ""), e.get("size", 0), e.get("mtime", 0)),
        )

    return {
        "version": SNAPSHOT_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dates": dates,
    }


def load_snapshot(output_dir: Path) -> Optional[Dict]:
    """从输出目录加载历史快照；不存在或损坏时返回 None。"""
    with _snapshot_lock:
        path = snapshot_file_path(output_dir)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None


def save_snapshot(output_dir: Path, snapshot: Dict) -> None:
    """保存快照到输出目录（UTF-8 + pretty json，便于人工排查）。"""
    with _snapshot_lock:
        state_dir = _state_dir(output_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        path = snapshot_file_path(output_dir)
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_incremental_plan(previous: Optional[Dict], current: Dict) -> IncrementalPlan:
    """对比前后快照生成增量计划。

    - changed_dates：需要重新处理的日期目录（新增或内容变化）
    - deleted_dates：输入端已删除的日期目录（需要同步清理输出）
    """
    prev_dates = (previous or {}).get("dates", {})
    cur_dates = current.get("dates", {})

    prev_keys = set(prev_dates.keys())
    cur_keys = set(cur_dates.keys())

    deleted = prev_keys - cur_keys

    changed: Set[str] = set()
    if previous is None:
        # First run: treat all as changed.
        changed = set(cur_keys)
    else:
        for date in cur_keys:
            if date not in prev_dates:
                changed.add(date)
                continue
            if prev_dates.get(date, {}) != cur_dates.get(date, {}):
                changed.add(date)

    return IncrementalPlan(changed_dates=changed, deleted_dates=deleted, snapshot=current)
