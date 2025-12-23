"""
学生信息管理模块
负责读取和管理学生信息数据
"""

import os
from pathlib import Path
import logging
from .config import STUDENT_PHOTOS_DIR, SUPPORTED_IMAGE_EXTENSIONS
from .utils import is_ignored_fs_entry

logger = logging.getLogger(__name__)


class StudentPhotosLayoutError(ValueError):
    """学生参考照目录结构错误。

    仅支持：student_photos/<学生名>/*.jpg|png...
    不支持：student_photos 根目录直接放图片；不支持更深层嵌套。
    """


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
        """从 student_photos 目录加载学生信息。

        单一输入规范（老师唯一用法）：
        - input/student_photos/<学生名>/*.jpg|jpeg|png

        规则：
        - 学生名取一级子文件夹名；文件名不参与归组
        - 每个学生最多使用 5 张参考照（超过则仅使用“最近修改时间”最新的 5 张）
        - student_photos 根目录禁止直接放图片；发现即报错
        - 第一版不支持更深层嵌套目录
        """
        try:
            if not self.students_photos_dir.exists():
                logger.warning(f"student_photos目录不存在: {self.students_photos_dir}")
                return

            def _list_images(dir_path: Path) -> list[Path]:
                imgs: list[Path] = []
                for p in dir_path.iterdir():
                    if is_ignored_fs_entry(p):
                        continue
                    if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                        imgs.append(p)
                return imgs

            def _sort_images_for_selection(imgs: list[Path]) -> list[Path]:
                # 规则：优先取“最近修改时间”最新的照片；mtime 相同时按文件名升序保证稳定。
                def _key(p: Path):
                    try:
                        mtime = p.stat().st_mtime
                    except OSError:
                        mtime = 0
                    return (-mtime, p.name)

                return sorted(imgs, key=_key)

            # 1) 根目录禁止直接放图片（避免两套规则并存）
            root_images = _list_images(self.students_photos_dir)
            if root_images:
                examples = "\n".join([f"  - {p.name}" for p in sorted(root_images)[:8]])
                raise StudentPhotosLayoutError(
                    "学生参考照目录结构不正确：检测到 student_photos 根目录存在图片文件。\n"
                    "\n"
                    "✅ 唯一正确方式：为每个学生建立文件夹，再把该学生照片放进去：\n"
                    "  student_photos/Alice(Senior)/any_name.jpg\n"
                    "  student_photos/Bob(Junior)/a.png\n"
                    "\n"
                    "❌ 目前发现这些根目录图片（请移动到对应学生文件夹）：\n"
                    f"{examples}"
                )

            # 2) 读取一级子文件夹作为学生列表
            student_dirs = [
                p for p in self.students_photos_dir.iterdir() if p.is_dir() and not is_ignored_fs_entry(p)
            ]
            student_dirs.sort(key=lambda p: p.name)
            if not student_dirs:
                # 允许没有任何参考照：程序仍可运行（所有课堂照片将进入 unknown）。
                # 由上层入口（如 console_launcher）决定是否强制要求老师提供参考照。
                logger.warning(
                    "student_photos 里没有找到任何学生文件夹；将视为未提供学生参考照（可继续运行，识别结果会全部归入 unknown）。"
                )
                self.students = []
                return

            empty_students: list[str] = []
            self.students_data = {}
            for student_dir in student_dirs:
                # 第一版：不支持更深层嵌套目录
                nested_dirs = [p for p in student_dir.iterdir() if p.is_dir() and not is_ignored_fs_entry(p)]
                if nested_dirs:
                    raise StudentPhotosLayoutError(
                        f"发现嵌套目录：{student_dir.name}/ 下还有子文件夹。\n\n"
                        "✅ 参考照必须直接放在 student_photos/学生名/ 下，不要再建更深一层文件夹。"
                    )

                images = _list_images(student_dir)
                if not images:
                    empty_students.append(student_dir.name)
                    continue

                # 稳定策略：按“最近修改时间”倒序，最多取前 5 张
                images = _sort_images_for_selection(images)
                selected = images[:5]
                if len(images) > 5:
                    logger.warning(
                        "学生 %s 参考照 %s 张，超过上限 5 张，将仅使用最近修改时间最新的 5 张",
                        student_dir.name,
                        len(images),
                    )

                self.students_data[student_dir.name] = {
                    'name': student_dir.name,
                    'photo_paths': [str(p) for p in selected],
                    'encoding': None,  # 兼容旧字段：实际编码由 FaceRecognizer 生成
                }

            if empty_students:
                shown = "\n".join([f"  - {n}" for n in empty_students[:12]])
                more = "" if len(empty_students) <= 12 else f"\n  ... 还有 {len(empty_students) - 12} 个"
                raise StudentPhotosLayoutError(
                    "以下学生文件夹里没有任何图片，请为每个学生至少放 1 张清晰正脸参考照：\n"
                    f"{shown}{more}"
                )

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