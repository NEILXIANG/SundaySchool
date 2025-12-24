"""配置与默认常量（统一入口）。"""

from pathlib import Path

# 基础路径配置
# 本文件位于：<project>/src/core/config.py
# BASE_DIR 约定为项目根目录（即 <project>/），这样 config.json 与打包/文档口径一致。
BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_FILE_NAME = "config.json"
CONFIG_FILE_PATH = BASE_DIR / CONFIG_FILE_NAME

# 默认目录配置
DEFAULT_INPUT_DIR = "input"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_LOG_DIR = "logs"

# 目录结构常量
STUDENT_PHOTOS_DIR = "student_photos"  # 存放学生参考照片的目录名
CLASS_PHOTOS_DIR = "class_photos"     # 存放课堂合照的目录名
UNSORTED_PHOTOS_DIR = "unsorted_photos"  # 存放待整理照片的目录名
UNKNOWN_PHOTOS_DIR = "unknown_photos"     # 存放无法识别照片的目录名

# 文件名配置
REPORT_FILE = "整理报告.txt"
SMART_REPORT_FILE = "智能分析报告.txt"

# 人脸识别配置
DEFAULT_TOLERANCE = 0.6  # 默认人脸识别阈值
MIN_FACE_SIZE = 50       # 最小人脸尺寸（像素）

# 支持的图片格式
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

# 日志配置
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# 文件处理配置
MAX_FILE_SIZE = None              # 不限制文件大小，按需提示资源占用
IMAGE_QUALITY = 85                # 默认图像质量（如果需要压缩）

# 报告配置
CONFIDENCE_THRESHOLD = 0.7        # 高置信度阈值
LOW_CONFIDENCE_THRESHOLD = 0.5    # 低置信度阈值

# 并行识别默认配置
DEFAULT_PARALLEL_RECOGNITION = {
	"enabled": False,
	"workers": 4,
	"chunk_size": 12,
	"min_photos": 30,
}

# 未知人脸聚类默认配置（v0.4.0）
DEFAULT_UNKNOWN_FACE_CLUSTERING = {
	"enabled": True,
	"threshold": 0.45,
	"min_cluster_size": 2,
}

# 统一默认配置（覆盖策略：用户配置优先）
DEFAULT_CONFIG = {
	"input_dir": DEFAULT_INPUT_DIR,
	"output_dir": DEFAULT_OUTPUT_DIR,
	"log_dir": DEFAULT_LOG_DIR,
	"tolerance": DEFAULT_TOLERANCE,
	"min_face_size": MIN_FACE_SIZE,
	"parallel_recognition": DEFAULT_PARALLEL_RECOGNITION,
	"unknown_face_clustering": DEFAULT_UNKNOWN_FACE_CLUSTERING,
	"class_photos_dir": CLASS_PHOTOS_DIR,
	"student_photos_dir": STUDENT_PHOTOS_DIR,
}


def resolve_path(path_value, base_dir: Path = BASE_DIR) -> Path:
	"""将相对路径解析为基于项目根目录的绝对路径。"""

	if path_value is None:
		return base_dir

	candidate = Path(path_value)
	return candidate if candidate.is_absolute() else (base_dir / candidate)


# 增量状态常量
STATE_DIR_NAME = ".state"
CLASS_PHOTOS_SNAPSHOT_FILENAME = "class_photos_snapshot.json"
SNAPSHOT_VERSION = 1

# 日期模式
DATE_DIR_PATTERN = r"^\d{4}-\d{2}-\d{2}$"