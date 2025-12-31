"""
Logger utilities.
"""
import os
import logging
from datetime import datetime
from ..config import LOG_FORMAT

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
    from ..config import DEFAULT_LOG_DIR
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR

    # Teacher mode: keep console output clean.
    # - Do not add console handlers.
    # - Do not wipe existing file handlers (e.g., packaged console launcher may add one early).
    teacher_mode = os.environ.get("SUNDAY_PHOTOS_TEACHER_MODE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )
    if teacher_mode:
        enable_color_console = False
        
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"photo_organizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 避免重复添加 handler
    # - Default (dev): clear all handlers to keep output deterministic.
    # - Teacher mode: keep file handlers; only remove non-file stream handlers to avoid console spam.
    if logger.handlers:
        if teacher_mode:
            for h in logger.handlers[:]:
                # FileHandler is also a StreamHandler; keep it.
                if isinstance(h, logging.FileHandler):
                    continue
                if isinstance(h, logging.StreamHandler):
                    logger.removeHandler(h)
        else:
            for h in logger.handlers[:]:
                logger.removeHandler(h)

    # 文件日志（始终无颜色）；teacher mode 下如果已有 FileHandler 则复用
    has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    if not has_file_handler:
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(fh)
    
    # 控制台日志（可选彩色；teacher mode 下默认关闭）
    if enable_color_console and (not teacher_mode):
        ch = ColoredConsoleHandler(enable_color=enable_color_console)
        logger.addHandler(ch)
    
    return logging.getLogger(__name__)
