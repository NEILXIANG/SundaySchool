"""并行识别（多进程）实现。

说明：
- face_recognition/dlib 主要是 CPU 密集型，适合用多进程提升吞吐。
- 为了降低每个任务的序列化成本，使用 initializer 在子进程中缓存已知编码/姓名等只读数据。
- 本模块只负责“识别”，分类/统计/落盘由主流程处理。
"""

from __future__ import annotations

import os
import sys
import logging
import warnings
import tempfile
import concurrent.futures
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Tuple

import numpy as np


logger = logging.getLogger(__name__)


# 子进程全局只读缓存（initializer 设置）
_G_KNOWN_ENCODINGS: List[Any] = []
_G_KNOWN_NAMES: List[str] = []
_G_TOLERANCE: float = 0.6
_G_MIN_FACE_SIZE: int = 50


@dataclass(frozen=True)
class ParallelConfig:
    enabled: bool
    workers: int
    chunk_size: int
    min_photos: int


def _truthy_env(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def init_worker(known_encodings: List[Any], known_names: List[str], tolerance: float, min_face_size: int) -> None:
    # 兼容历史：某些依赖可能产生噪声警告；并行下会被放大。
    warnings.filterwarnings("ignore", message=r"pkg_resources is deprecated as an API\.")

    # 修复 Matplotlib 在多进程下的竞态条件（构建字体缓存导致死锁/卡顿）
    # 强制每个子进程使用独立的 MPLCONFIGDIR
    try:
        os.environ["MPLBACKEND"] = "Agg"
        
        work_dir = os.environ.get("SUNDAY_PHOTOS_WORK_DIR", "").strip()
        if work_dir:
            base = Path(work_dir) / "logs" / ".mplconfig"
        else:
            base = Path(tempfile.gettempdir()) / "SundayPhotoOrganizer" / "mplconfig"
            
        # 使用当前子进程 PID 隔离配置目录
        cfg_dir = base / f"pid_{os.getpid()}"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(cfg_dir)
    except Exception:
        pass

    global _G_KNOWN_ENCODINGS, _G_KNOWN_NAMES, _G_TOLERANCE, _G_MIN_FACE_SIZE
    _G_KNOWN_ENCODINGS = known_encodings
    _G_KNOWN_NAMES = known_names
    _G_TOLERANCE = float(tolerance)
    _G_MIN_FACE_SIZE = int(min_face_size)


def recognize_one(image_path: str) -> Tuple[str, Dict[str, Any]]:
    """对子进程中的单张照片执行识别，返回 (path, details_dict)。"""
    # 保险起见：某些平台/路径下警告过滤可能未在 initializer 生效，这里再兜底一次。
    warnings.filterwarnings("ignore", message=r"pkg_resources is deprecated as an API\.")
    from .face_recognizer import face_recognition

    # 结果结构尽量与 FaceRecognizer.recognize_faces(return_details=True) 对齐
    try:
        if face_recognition is None:
            engine = os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND", "").strip().lower() or "insightface"
            raise ModuleNotFoundError(f"人脸识别后端依赖未就绪（SUNDAY_PHOTOS_FACE_BACKEND={engine}）")

        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            return image_path, {
                "status": "no_faces_detected",
                "message": "图片中未检测到人脸",
                "recognized_students": [],
                "total_faces": 0,
            }

        sizeable_locations = []
        for top, right, bottom, left in face_locations:
            if (bottom - top) >= _G_MIN_FACE_SIZE and (right - left) >= _G_MIN_FACE_SIZE:
                sizeable_locations.append((top, right, bottom, left))

        if not sizeable_locations:
            return image_path, {
                "status": "no_faces_detected",
                "message": "检测到的人脸尺寸过小，无法识别",
                "recognized_students": [],
                "total_faces": 0,
            }

        face_encodings = face_recognition.face_encodings(image, sizeable_locations)

        if not _G_KNOWN_ENCODINGS:
            total_faces = len(face_encodings)
            return image_path, {
                "status": "no_matches_found",
                "message": "没有找到任何可用的学生面部编码",
                "recognized_students": [],
                "total_faces": total_faces,
                "unknown_faces": total_faces,
            }

        recognized_students: List[str] = []
        unknown_faces_count = 0
        unknown_encodings = []

        known_encodings = _G_KNOWN_ENCODINGS
        known_names = _G_KNOWN_NAMES

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=_G_TOLERANCE)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            best_match_index = None
            if len(face_distances) > 0:
                best_match_index = int(np.argmin(face_distances))

            if best_match_index is not None and matches[best_match_index]:
                student_name = known_names[best_match_index]
                if student_name not in recognized_students:
                    recognized_students.append(student_name)
            else:
                unknown_faces_count += 1
                unknown_encodings.append(face_encoding)

        total_faces = len(face_encodings)
        status = "success" if recognized_students else "no_matches_found"
        return image_path, {
            "status": status,
            "message": f"检测到{total_faces}张人脸，识别到{len(recognized_students)}名学生",
            "recognized_students": recognized_students,
            "total_faces": total_faces,
            "unknown_faces": unknown_faces_count,
            "unknown_encodings": unknown_encodings,
        }

    except MemoryError:
        return image_path, {
            "status": "error",
            "message": f"处理图片时内存不足: {image_path}",
            "recognized_students": [],
            "total_faces": 0,
        }
    except Exception as e:
        logger.exception(f"并行识别图片 {image_path} 失败")
        return image_path, {
            "status": "error",
            "message": f"识别图片 {image_path} 中的人脸失败: {str(e)}",
            "recognized_students": [],
            "total_faces": 0,
        }


def parallel_recognize(
    photo_paths: List[str],
    *,
    known_encodings: List[Any],
    known_names: List[str],
    tolerance: float,
    min_face_size: int,
    workers: int,
    chunk_size: int,
) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """并行识别入口。返回一个迭代器，逐个产出 (path, details)。"""

    # 强制禁用：便于排障
    if _truthy_env("SUNDAY_PHOTOS_NO_PARALLEL", default="0"):
        for p in photo_paths:
            yield recognize_one(p)
        return

    if workers <= 1 or len(photo_paths) <= 1:
        for p in photo_paths:
            yield recognize_one(p)
        return

    # Strategy selection.
    #
    # Why:
    # - In macOS PyInstaller frozen builds, multiprocessing spawn can look like a hang
    #   because each worker process re-imports heavy deps and may contend on resources.
    # - For packaged teacher builds, a thread pool is often more stable (no spawn).
    #
    # Override:
    # - SUNDAY_PHOTOS_PARALLEL_STRATEGY=threads|processes
    strategy = (os.environ.get("SUNDAY_PHOTOS_PARALLEL_STRATEGY", "") or "").strip().lower()
    if strategy not in ("threads", "processes"):
        is_frozen = bool(getattr(sys, "frozen", False))
        if is_frozen and sys.platform == "darwin":
            strategy = "threads"
        else:
            strategy = "processes"

    if strategy == "threads":
        # Initialize globals once in the main process. recognize_one reads these.
        init_worker(known_encodings, known_names, float(tolerance), int(min_face_size))

        # threads: keep chunksize semantics simple; we still yield as soon as futures complete.
        max_workers = int(max(2, workers))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(recognize_one, p): p for p in photo_paths}
            for fut in concurrent.futures.as_completed(futures):
                p = futures[fut]
                try:
                    yield fut.result()
                except Exception as e:
                    logger.exception("并行识别线程任务失败: %s", p)
                    yield p, {
                        "status": "error",
                        "message": f"并行识别线程任务失败: {str(e)}",
                        "recognized_students": [],
                        "total_faces": 0,
                    }
        return

    import multiprocessing as mp

    # 进度条“卡住”的常见原因：Pool.imap_unordered 的 chunksize 偏大时，结果会按批次回传。
    # 为了让控制台进度条更丝滑（老师能持续看到在运行），这里对实际 chunksize 做上限。
    # 说明：chunksize 越小，调度开销越高；但通常 1~2 能显著改善“长时间不动”。
    effective_chunksize = int(max(1, min(int(chunk_size), 2)))

    ctx = mp.get_context("spawn")
    with ctx.Pool(
        processes=int(workers),
        initializer=init_worker,
        initargs=(known_encodings, known_names, float(tolerance), int(min_face_size)),
    ) as pool:
        for item in pool.imap_unordered(recognize_one, photo_paths, chunksize=effective_chunksize):
            yield item
