"""
学生信息管理模块
负责读取和管理学生信息数据
"""

import os
from pathlib import Path
import logging
from collections import defaultdict
from .config import STUDENT_PHOTOS_DIR, SUPPORTED_IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)


class StudentManager:
    """学生信息管理器（默认使用 input/student_photos，兼容旧 classroom 命名）"""
    
    def __init__(self, input_dir=None, classroom_dir=None):
        from .config import DEFAULT_INPUT_DIR
        if input_dir is None:
            # 兼容旧的 classroom_dir 参数
            input_dir = classroom_dir if classroom_dir is not None else DEFAULT_INPUT_DIR
            
        self.input_dir = Path(input_dir)
        self.students_photos_dir = self.input_dir / STUDENT_PHOTOS_DIR
        self.students_data = {}  # {学生姓名: [照片路径1, 照片路径2, ...]}
        
        # 确保目录存在
        self.students_photos_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载学生数据
        self.load_students()
    
    def load_students(self):
        """从 student_photos 目录加载学生信息，按文件名前缀识别学生"""
        try:
            if not self.students_photos_dir.exists():
                logger.warning(f"student_photos目录不存在: {self.students_photos_dir}")
                return
            
            # 按学生姓名分组照片路径
            student_photos = defaultdict(list)
            
            for img_path in self.students_photos_dir.iterdir():
                if img_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS and img_path.is_file():
                    stem = img_path.stem
                    # 文件名格式: 学生姓名_任意字符.jpg
                    if '_' in stem:
                        student_name = stem.split('_')[0]
                    else:
                        student_name = stem
                    student_photos[student_name].append(img_path)
            
            # 存入 self.students_data
            for name, paths in student_photos.items():
                self.students_data[name] = {
                    'name': name,
                    'photo_paths': [str(p) for p in paths],
                    'encoding': None  # 将在人脸识别模块中加载
                }
            
            logger.info(f"成功加载 {len(self.students_data)} 名学生信息")
            
        except Exception as e:
            logger.error(f"加载学生信息失败: {str(e)}")
            raise
    
    def get_all_students(self):
        """获取所有学生信息"""
        return list(self.students_data.values())
    
    def get_student_by_name(self, name):
        """根据姓名获取学生信息"""
        return self.students_data.get(name)
    
    def get_student_names(self):
        """获取所有学生姓名列表"""
        return list(self.students_data.keys())
    
    def check_student_photos(self):
        """检查学生参考照片是否存在"""
        missing = []
        for name, info in self.students_data.items():
            for p in info['photo_paths']:
                if not os.path.exists(p):
                    missing.append((name, p))
        if missing:
            logger.warning(f"以下学生的参考照片不存在:")
            for name, p in missing:
                logger.warning(f"  - {name}: {p}")
        else:
            logger.info("所有学生的参考照片都存在")
        return missing