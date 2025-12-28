"""通用工具函数。

本模块集中放置：
- 日志初始化（文件日志 + 可选彩色控制台）
- 日期推断（优先目录名 YYYY-MM-DD，其次 EXIF，其次文件 mtime）
- 文件/目录相关的通用检查

注意：
- 0 字节图片在扫描/增量快照阶段会被视为无效而忽略，避免误报与无意义异常。
"""
import os
import re
import logging
from datetime import datetime
from datetime import date as _date
from pathlib import Path
from typing import List, Optional, Pattern
from .config import LOG_FORMAT, LOG_MAX_BYTES, LOG_BACKUP_COUNT, SUPPORTED_IMAGE_EXTENSIONS

# Console should be teacher-friendly: keep it message-only.
# File logs still use LOG_FORMAT for diagnostics.
CONSOLE_LOG_FORMAT = "%(message)s"

# ANSI 颜色码
COLORS = {
    'DEBUG': '\033[94m',    # 蓝
    'INFO': '\033[92m',     # 绿
    'WARNING': '\033[93m',  # 黄
    'ERROR': '\033[91m',    # 红
    'CRITICAL': '\033[95m', # 紫
    'RESET': '\033[0m'
}

class ColorFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    def format(self, record):
        levelname = record.levelname
        color = COLORS.get(levelname, COLORS['RESET'])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"

class ColoredConsoleHandler(logging.StreamHandler):
    """彩色控制台日志处理器"""

    def __init__(self, enable_color=True):
        super().__init__()
        self.enable_color = enable_color
        if enable_color:
            self.setFormatter(ColorFormatter(CONSOLE_LOG_FORMAT))
        else:
            self.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT))

def setup_logger(log_dir=None, enable_color_console=False):
    """设置日志记录器。

    设计：
    - 文件日志始终输出到 logs 目录（UTF-8，无颜色，便于归档）
    - 控制台日志可选彩色输出（提高教师/操作者可读性）

    说明：
    - 这里会配置 root logger，并清理已存在的 handler，避免重复打印。
    """
    from .config import DEFAULT_LOG_DIR
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR
        
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"photo_organizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 避免重复添加handler
    if logger.handlers:
        for h in logger.handlers[:]:
            logger.removeHandler(h)

    # 文件日志（始终无颜色）
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(fh)
    
    # 控制台日志（可选彩色）
    ch = ColoredConsoleHandler(enable_color=enable_color_console)
    logger.addHandler(ch)
    
    return logging.getLogger(__name__)

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


def is_ignored_fs_entry(path: Path) -> bool:
    """Return True for OS-generated metadata/hidden entries.

    Purpose: avoid treating platform junk files as real photos/folders.

    Examples:
    - macOS zip metadata: __MACOSX/, .DS_Store, Icon\r, ._AppleDouble files
    - Windows Explorer metadata: Thumbs.db, desktop.ini
    """
    name = path.name
    if not name:
        return False
    if name.startswith('.'):
        return True

    lower = name.lower()
    if lower in {"__macosx", ".ds_store", "thumbs.db", "desktop.ini"}:
        return True
    # AppleDouble sidecar files can look like images (e.g. ._IMG_0001.jpg)
    if lower.startswith("._"):
        return True
    # Finder custom icon marker in some archives
    if name == "Icon\r":
        return True

    return False


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

def ensure_directory_exists(directory):
    """确保目录存在（mkdir -p 语义）。"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_file_extension(filename):
    """获取文件扩展名"""
    return Path(filename).suffix.lower()

def is_supported_image_file(filename):
    """检查是否为支持的图片格式"""
    return get_file_extension(filename) in SUPPORTED_IMAGE_EXTENSIONS


def is_supported_nonempty_image_path(path) -> bool:
    """检查路径是否为支持的且非空的图片文件。

    说明：老师可能会误放 0 字节文件或损坏文件。
    - 0 字节文件：在处理与增量快照中视为“无效图片”，直接忽略。
    - 其他损坏文件：仍可能在后续读取时抛异常，由调用方捕获并跳过。
    """
    try:
        p = Path(path)
        if is_ignored_fs_entry(p):
            return False
        if not p.is_file():
            return False
        if p.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            return False
        return p.stat().st_size > 0
    except Exception:
        return False


class UnsafePathError(ValueError):
    """路径安全检查失败（试图逃逸出基准目录）。"""
    pass


def safe_join_under(base_dir: Path, *segments: str) -> Path:
    """安全地拼接路径，确保结果在 base_dir 之下。

    防止 Path Traversal 攻击（如 ".." 或绝对路径）。
    
    Args:
        base_dir: 基准目录（必须是绝对路径或安全的可信路径）
        *segments: 待拼接的路径片段（如学生姓名、日期等）
    
    Returns:
        Path: 拼接后的绝对路径
    
    Raises:
        UnsafePathError: 如果拼接后的路径不在 base_dir 之下
    """
    base = Path(base_dir).resolve()
    
    # 检查片段中是否包含绝对路径（Path.joinpath 会重置根目录）
    for seg in segments:
        if Path(seg).is_absolute():
            raise UnsafePathError(f"Absolute path segment not allowed: {seg}")
            
    # 拼接并解析（resolve 处理 ".." 和符号链接）
    # 注意：resolve(strict=False) 允许路径不存在
    target = base.joinpath(*segments).resolve()
    
    try:
        # 检查 target 是否以 base 开头
        target.relative_to(base)
    except ValueError:
        raise UnsafePathError(f"Path traversal attempt: {target} is outside {base}")
        
    return target


def ensure_resolved_under(base_dir: Path, target_path: Path) -> None:
    """确保 target_path resolve 后仍在 base_dir 之下。

    用途：删除/清理等“危险操作”前的防护，避免符号链接导致越界。

    Raises:
        UnsafePathError: 如果 resolve 后不在 base_dir 之下
    """
    base = Path(base_dir).resolve()
    try:
        resolved = Path(target_path).resolve(strict=False)
    except Exception as e:
        raise UnsafePathError(f"Failed to resolve path: {target_path}: {e}")

    try:
        resolved.relative_to(base)
    except ValueError:
        raise UnsafePathError(f"Resolved path escapes base_dir: {resolved} is outside {base}")
