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
from .utils import is_supported_nonempty_image_path, is_ignored_fs_entry


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
    """枚举合法的日期子目录（YYYY-MM-DD）。"""
    if not class_photos_dir.exists():
        return []
    date_dirs: List[Path] = []
    for child in class_photos_dir.iterdir():
        if is_ignored_fs_entry(child):
            continue
        if child.is_dir() and re.match(DATE_DIR_PATTERN, child.name):
            date_dirs.append(child)
    return sorted(date_dirs, key=lambda p: p.name)


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
                    files: [ {path,size,mtime}, ... ]
                },
                ...
            }
        }
        """

        dates: Dict[str, Dict] = {}
        for date_dir in iter_date_directories(class_photos_dir):
                file_entries: List[Dict] = []
                for file_path in sorted(date_dir.rglob("*")):
                        if is_supported_nonempty_image_path(file_path):
                                rel = file_path.relative_to(date_dir)
                                entry = _file_entry(file_path)
                                entry["path"] = rel.as_posix()
                                file_entries.append(entry)

                dates[date_dir.name] = {"files": file_entries}

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
