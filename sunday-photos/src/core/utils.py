"""
工具函数模块
"""
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from .config import LOG_FORMAT, LOG_MAX_BYTES, LOG_BACKUP_COUNT, SUPPORTED_IMAGE_EXTENSIONS

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
            self.setFormatter(ColorFormatter(LOG_FORMAT))
        else:
            self.setFormatter(logging.Formatter(LOG_FORMAT))

def setup_logger(log_dir=None, enable_color_console=False):
    """设置日志记录器"""
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


def _get_date_from_directory(photo_path: str):
    """优先从目录名(yyyy-mm-dd)推断日期"""
    path_obj = Path(photo_path)
    for parent in [path_obj.parent] + list(path_obj.parents):
        if DATE_DIR_PATTERN.match(parent.name):
            return parent.name
    return None


def get_photo_date(photo_path):
    """获取照片的日期，优先使用目录名(yyyy-mm-dd)，否则回退到EXIF/文件时间"""
    date_from_dir = _get_date_from_directory(photo_path)
    if date_from_dir:
        return date_from_dir

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        
        image = Image.open(photo_path)
        exif_data = image._getexif()
        
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
    """确保目录存在，如果不存在则创建"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_file_extension(filename):
    """获取文件扩展名"""
    return Path(filename).suffix.lower()

def is_supported_image_file(filename):
    """检查是否为支持的图片格式"""
    return get_file_extension(filename) in SUPPORTED_IMAGE_EXTENSIONS