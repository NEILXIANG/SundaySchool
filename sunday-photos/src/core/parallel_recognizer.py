"""并行识别（多进程）实现。

说明：
- face_recognition/dlib 主要是 CPU 密集型，适合用多进程提升吞吐。
- 为了降低每个任务的序列化成本，使用 initializer 在子进程中缓存已知编码/姓名等只读数据。
- 本模块只负责“识别”，分类/统计/落盘由主流程处理。
"""

from __future__ import annotations

import os
import logging
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
    global _G_KNOWN_ENCODINGS, _G_KNOWN_NAMES, _G_TOLERANCE, _G_MIN_FACE_SIZE
    _G_KNOWN_ENCODINGS = known_encodings
    _G_KNOWN_NAMES = known_names
    _G_TOLERANCE = float(tolerance)
    _G_MIN_FACE_SIZE = int(min_face_size)


def recognize_one(image_path: str) -> Tuple[str, Dict[str, Any]]:
    """对子进程中的单张照片执行识别，返回 (path, details_dict)。"""
    import face_recognition  # pyright: ignore[reportMissingImports]

    # 结果结构尽量与 FaceRecognizer.recognize_faces(return_details=True) 对齐
    try:
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

    import multiprocessing as mp

    ctx = mp.get_context("spawn")
    with ctx.Pool(
        processes=int(workers),
        initializer=init_worker,
        initargs=(known_encodings, known_names, float(tolerance), int(min_face_size)),
    ) as pool:
        for item in pool.imap_unordered(recognize_one, photo_paths, chunksize=int(max(1, chunk_size))):
            yield item
