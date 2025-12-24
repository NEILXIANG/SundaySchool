"""课堂照片识别结果缓存（按日期分片）。

设计目标：
- 对老师无感：缓存保存在 output/.state 下，用户无需理解或操作。
- 与增量处理对齐：以日期文件夹（YYYY-MM-DD）为最小失效/重建单元。
- 稳健：缓存损坏/读写失败时自动回退为不命中，不影响主流程。

缓存策略：
- key：相对路径(rel_path) + size + mtime
- value：FaceRecognizer.recognize_faces(return_details=True) 兼容的结果 dict
- params_fingerprint：识别参数指纹变化时自动整体失效（避免复用旧结果）
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


CACHE_VERSION = 1
STATE_DIR_NAME = ".state"
CACHE_DIR_NAME = "recognition_cache_by_date"


@dataclass(frozen=True)
class CacheKey:
    date: str
    rel_path: str
    size: int
    mtime: int


def cache_root(output_dir: Path) -> Path:
    return Path(output_dir) / STATE_DIR_NAME / CACHE_DIR_NAME


def date_cache_path(output_dir: Path, date: str) -> Path:
    return cache_root(output_dir) / f"{date}.json"


def compute_params_fingerprint(params: Dict[str, Any]) -> str:
    """计算识别参数指纹（用于缓存失效）。

    params 建议只包含：tolerance/min_face_size/resize_long_edge/库版本等。
    """
    payload = json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _empty_cache(date: str, params_fingerprint: str) -> Dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "date": date,
        "params_fingerprint": params_fingerprint,
        "entries": {},
    }


def load_date_cache(output_dir: Path, date: str) -> Dict[str, Any]:
    """加载某日期缓存。

    失败/不存在：返回空结构（不抛异常）。
    """
    path = date_cache_path(output_dir, date)
    if not path.exists():
        return {
            "version": CACHE_VERSION,
            "date": date,
            "params_fingerprint": "",
            "entries": {},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {
                "version": CACHE_VERSION,
                "date": date,
                "params_fingerprint": "",
                "entries": {},
            }
        data.setdefault("entries", {})
        return data
    except Exception:
        return {
            "version": CACHE_VERSION,
            "date": date,
            "params_fingerprint": "",
            "entries": {},
        }


def save_date_cache_atomic(output_dir: Path, date: str, cache: Dict[str, Any]) -> None:
    """原子保存日期缓存（tmp -> rename）。"""
    root = cache_root(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = date_cache_path(output_dir, date)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(cache, ensure_ascii=False, indent=2)
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def invalidate_date_cache(output_dir: Path, date: str) -> None:
    """删除某日期缓存文件（用于 deleted_dates 同步）。"""
    path = date_cache_path(output_dir, date)
    try:
        if path.exists():
            path.unlink()
    except Exception:
        # 缓存删除失败不应阻断主流程
        return


def normalize_cache_for_fingerprint(cache: Dict[str, Any], date: str, params_fingerprint: str) -> Dict[str, Any]:
    """若参数指纹不一致，则返回“同日期的空缓存结构”。"""
    if cache.get("params_fingerprint") != params_fingerprint:
        return _empty_cache(date=date, params_fingerprint=params_fingerprint)
    # 保障字段存在
    cache.setdefault("version", CACHE_VERSION)
    cache.setdefault("date", date)
    cache.setdefault("params_fingerprint", params_fingerprint)
    cache.setdefault("entries", {})
    return cache


def lookup_result(cache: Dict[str, Any], key: CacheKey) -> Optional[Dict[str, Any]]:
    """命中返回 result dict，否则返回 None。"""
    entries = cache.get("entries")
    if not isinstance(entries, dict):
        return None
    item = entries.get(key.rel_path)
    if not isinstance(item, dict):
        return None
    try:
        if int(item.get("size", -1)) != int(key.size):
            return None
        if int(item.get("mtime", -1)) != int(key.mtime):
            return None
    except Exception:
        return None
    result = item.get("result")
    return result if isinstance(result, dict) else None


def store_result(cache: Dict[str, Any], key: CacheKey, result: Dict[str, Any]) -> None:
    # 识别结果里可能含 numpy.ndarray（例如 unknown_encodings），直接 json 序列化会失败。
    # 缓存层做一次“可序列化净化”，保证缓存可用且不影响主流程的内存结果。
    safe_result = _sanitize_for_json(result)
    entries = cache.setdefault("entries", {})
    if not isinstance(entries, dict):
        # 不尝试修复异常结构，直接覆盖
        cache["entries"] = {}
        entries = cache["entries"]
    entries[key.rel_path] = {
        "size": int(key.size),
        "mtime": int(key.mtime),
        "result": safe_result,
    }


def _sanitize_for_json(value: Any, *, _depth: int = 0) -> Any:
    """把 value 转为可 JSON 序列化的结构。

    目标：尽量保留信息（包括 unknown_encodings），同时避免引入 numpy 依赖。
    """

    # 防御：避免极端嵌套导致递归爆栈
    if _depth > 6:
        return str(value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): _sanitize_for_json(v, _depth=_depth + 1) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(v, _depth=_depth + 1) for v in value]

    # numpy.ndarray / numpy scalar 兼容：优先用 tolist()/item()
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            return _sanitize_for_json(tolist(), _depth=_depth + 1)
        except Exception:
            return str(value)

    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _sanitize_for_json(item(), _depth=_depth + 1)
        except Exception:
            return str(value)

    # 兜底：转字符串，保证可序列化
    return str(value)


def prune_entries(cache: Dict[str, Any], keep_rel_paths: set[str]) -> None:
    """删除不再存在的条目，避免缓存无限增长。"""
    entries = cache.get("entries")
    if not isinstance(entries, dict):
        cache["entries"] = {}
        return
    for rel in list(entries.keys()):
        if rel not in keep_rel_paths:
            entries.pop(rel, None)
