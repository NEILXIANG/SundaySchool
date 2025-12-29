"""
Date parsing utilities.
"""
import os
import re
from datetime import datetime
from datetime import date as _date
from typing import List, Optional, Pattern
from pathlib import Path

DATE_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date_from_text(text: str) -> Optional[str]:
    """从文本中解析日期，并返回标准格式 YYYY-MM-DD。

    兼容老师常见的日期文件夹写法（不引入歧义）：
    - 2025-12-23
    - 2025.12.23
    - 2025_12_23
    - 20251223
    - 2025年12月23日（或不带“日”）
    - Dec 23 2025 / December 23, 2025
    - 23 Dec 2025
    - 2025 Dec 23

    说明：不支持月/日/年（如 12-23-2025）以避免地区歧义。
    """
    if not text:
        return None
    s = text.strip()

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    month_token = (
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
        r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    )

    patterns: List[Pattern] = [
        # 允许常见分隔符：- . _ /
        re.compile(r"(?P<y>\d{4})[-_./](?P<m>\d{1,2})[-_./](?P<d>\d{1,2})"),
        re.compile(r"(?P<y>\d{4})年(?P<m>\d{1,2})月(?P<d>\d{1,2})(?:日)?"),
        re.compile(r"^(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})$"),
    ]

    for pat in patterns:
        m = pat.search(s)
        if not m:
            continue
        try:
            y = int(m.group("y"))
            mo = int(m.group("m"))
            d = int(m.group("d"))
            _date(y, mo, d)  # validate
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except Exception:
            continue

    month_name_patterns: List[Pattern] = [
        # Dec 23 2025 / December 23, 2025
        re.compile(
            rf"\b(?P<mon>{month_token})\b[\s._/-]+(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\b[\s,._/-]+(?P<y>\d{{4}})\b",
            re.IGNORECASE,
        ),
        # 23 Dec 2025
        re.compile(
            rf"\b(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\b[\s._/-]+\b(?P<mon>{month_token})\b[\s,._/-]+(?P<y>\d{{4}})\b",
            re.IGNORECASE,
        ),
        # 2025 Dec 23
        re.compile(
            rf"\b(?P<y>\d{{4}})\b[\s._/-]+\b(?P<mon>{month_token})\b[\s._/-]+(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\b",
            re.IGNORECASE,
        ),
    ]

    for pat in month_name_patterns:
        m = pat.search(s)
        if not m:
            continue
        try:
            y = int(m.group("y"))
            d = int(m.group("d"))
            mon_raw = (m.group("mon") or "").strip().lower()
            mon_key = mon_raw[:3]
            mo = month_map.get(mon_key)
            if not mo:
                continue
            _date(y, mo, d)  # validate
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except Exception:
            continue

    return None


def _get_date_from_directory(photo_path: str):
    """优先从目录名(yyyy-mm-dd)推断日期"""
    path_obj = Path(photo_path)
    for parent in [path_obj.parent] + list(path_obj.parents):
        normalized = parse_date_from_text(parent.name)
        if normalized:
            return normalized

        # 兼容三层目录：YYYY/MM/DD（例如 2025/12/23/img.jpg）
        # 注意：这里 parent 可能是 DD，parent.parent 是 MM，parent.parent.parent 是 YYYY
        try:
            d = int(parent.name)
            mo = int(parent.parent.name)
            y = int(parent.parent.parent.name)
            _date(y, mo, d)  # validate
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except Exception:
            pass
    return None


def get_photo_date(photo_path):
    """获取照片日期。

    优先级：
    1) 从父目录中推断：若路径任意上层目录名匹配 YYYY-MM-DD，直接使用
    2) 读取 EXIF DateTimeOriginal
    3) 使用文件 mtime

    这样做的原因：
    - 教师通常会把课堂照片按日期放到文件夹中；目录名往往最可靠
    - EXIF 在转发/压缩后可能缺失
    """
    date_from_dir = _get_date_from_directory(photo_path)
    if date_from_dir:
        return date_from_dir

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        image = Image.open(photo_path)
        try:
            exif_data = image._getexif()
        finally:
            try:
                image.close()
            except Exception:
                pass
        
        if exif_data:
            for tag, value in exif_data.items():
                if TAGS.get(tag) == 'DateTimeOriginal':
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S').strftime('%Y-%m-%d')
    except Exception:
        pass
    
    try:
        mtime = os.path.getmtime(photo_path)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')
