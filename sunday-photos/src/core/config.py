"""
配置文件模块
集中管理应用程序的所有配置和常量
"""

import os
from pathlib import Path

# 基础路径配置
BASE_DIR = Path(__file__).parent.parent

# 默认目录配置（输入目录从 classroom 调整为 input）
DEFAULT_INPUT_DIR = "input"
DEFAULT_CLASSROOM_DIR = DEFAULT_INPUT_DIR  # 兼容旧命名
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
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

# 日志配置
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# 文件处理配置
MAX_FILE_SIZE = None              # 不限制文件大小，按需提示资源占用
IMAGE_QUALITY = 85                # 默认图像质量（如果需要压缩）

# 报告配置
CONFIDENCE_THRESHOLD = 0.7        # 高置信度阈值
LOW_CONFIDENCE_THRESHOLD = 0.5    # 低置信度阈值