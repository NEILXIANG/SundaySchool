"""
人脸识别模块
负责人脸检测、特征提取和识别
"""

import os
import logging
import numpy as np
import hashlib
import json
from pathlib import Path
from .config import DEFAULT_TOLERANCE, MIN_FACE_SIZE


try:
    import face_recognition  # type: ignore
except Exception as e:  # pragma: no cover
    _FACE_RECOGNITION_IMPORT_ERROR = e

    class _FaceRecognitionStub:
        """当 face_recognition 未安装时的占位实现。

        说明：
        - 生产环境必须安装 face_recognition。
        - 单元测试可通过 mock/patch 这些方法来避免真实依赖。
        """

        def _raise(self):
            raise ModuleNotFoundError(
                "未安装 face_recognition（人脸识别依赖）。请先安装 requirements.txt 中的依赖。"
            ) from _FACE_RECOGNITION_IMPORT_ERROR

        def load_image_file(self, *args, **kwargs):
            self._raise()

        def face_locations(self, *args, **kwargs):
            self._raise()

        def face_encodings(self, *args, **kwargs):
            self._raise()

        def compare_faces(self, *args, **kwargs):
            self._raise()

        def face_distance(self, *args, **kwargs):
            self._raise()

    face_recognition = _FaceRecognitionStub()  # type: ignore

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """人脸识别器"""
    
    def __init__(self, student_manager, tolerance=None):
        """初始化人脸识别器。

        参数：
        - student_manager：学生管理器实例，用于加载学生参考照片与学生名册
        - tolerance：人脸识别阈值（越小越严格），默认取配置 DEFAULT_TOLERANCE
        """

        if tolerance is None:
            tolerance = DEFAULT_TOLERANCE
        self.student_manager = student_manager
        self.tolerance = tolerance
        self.students_encodings = {}
        self.known_student_names = []
        self.known_encodings = []

        # 参考照增量缓存（提升速度 + 支持增删 diff）
        self._ref_cache_dir = self._resolve_ref_cache_dir()
        self._ref_snapshot_path = self._resolve_ref_snapshot_path()
        self.reference_fingerprint = ""  # 用于识别缓存失效（参考照变化即变化）
        
        # 加载所有学生的面部编码
        self.load_student_encodings()

    def _resolve_ref_cache_dir(self) -> Path:
        """参考照编码缓存目录（跟随 input_dir/logs，打包版也可用）。"""
        try:
            input_dir = Path(getattr(self.student_manager, 'input_dir'))
        except Exception:
            input_dir = Path(".")
        d = input_dir / "logs" / "reference_encodings"
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            # 缓存失败不影响主流程
            pass
        return d

    def _resolve_ref_snapshot_path(self) -> Path:
        try:
            input_dir = Path(getattr(self.student_manager, 'input_dir'))
        except Exception:
            input_dir = Path(".")
        p = input_dir / "logs" / "reference_index.json"
        return p

    def _load_ref_snapshot(self) -> dict:
        try:
            if self._ref_snapshot_path.exists():
                return json.loads(self._ref_snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def _save_ref_snapshot(self, snapshot: dict) -> None:
        try:
            self._ref_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._ref_snapshot_path.with_suffix(self._ref_snapshot_path.suffix + ".tmp")
            tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self._ref_snapshot_path)
        except Exception:
            # 缓存失败不影响主流程
            return

    def _rel_to_input(self, photo_path: str) -> str:
        try:
            input_dir = Path(getattr(self.student_manager, 'input_dir'))
            return Path(photo_path).resolve().relative_to(input_dir.resolve()).as_posix()
        except Exception:
            return Path(photo_path).as_posix()

    def _make_reference_fingerprint(self, selected_items: list[dict]) -> str:
        """基于“被采用的参考照集合”的稳定指纹（用于识别缓存失效）。"""
        payload = json.dumps(selected_items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha1(payload).hexdigest()

    def _refresh_known_faces(self):
        """刷新缓存的学生姓名和编码列表。

        多编码融合策略：known_encodings/known_student_names 按 encoding 展开对齐。
        并行识别与串行识别都会取全局最小距离，从而自然实现 min-distance。
        """
        names: list[str] = []
        encs: list[Any] = []
        for student_name in sorted(self.students_encodings.keys()):
            data = self.students_encodings[student_name]
            for enc in data.get('encodings', []) or []:
                names.append(student_name)
                encs.append(enc)
        self.known_student_names = names
        self.known_encodings = encs
    
    def load_student_encodings(self):
        """加载所有学生的面部编码。

        策略（文件夹模式 + 多编码融合）：
        - 每个学生最多使用 5 张参考照（由 StudentManager 预筛选）
        - 对每张参考照尝试提取 encoding：成功则加入该学生 encodings
        - 多编码融合（min-distance）：识别时会取全局最小距离对应的学生名
        - 增量/缓存：参考照未变化时复用上次提取的 encoding，避免重复计算
        - 允许“空数据集”：没有任何学生编码时，系统仍可运行，但识别结果会倾向未知
        """
        students = self.student_manager.get_all_students()
        loaded_count = 0
        failed_count = 0

        prev = self._load_ref_snapshot()
        prev_items_by_rel: dict[str, dict] = {}
        for student_name, items in (prev.get('students') or {}).items():
            if not isinstance(items, list):
                continue
            for it in items:
                rel = it.get('rel_path')
                if isinstance(rel, str):
                    prev_items_by_rel[rel] = it

        next_snapshot: dict = {
            'version': 1,
            'mode': 'student_folder_only',
            'max_photos_per_student': 5,
            'students': {},
        }
        selected_for_fingerprint: list[dict] = []
        
        for student_info in students:
            student_name = student_info.get('name', '')
            photo_paths = student_info.get('photo_paths', [])
            
            if not photo_paths:
                logger.warning(f"学生 {student_name} 没有参考照片")
                failed_count += 1
                continue
                
            encodings: list[Any] = []
            student_items: list[dict] = []
            for photo_path in photo_paths:
                if not os.path.exists(photo_path):
                    logger.warning(f"学生 {student_name} 的参考照片不存在: {photo_path}")
                    continue

                # 注意：某些单元测试会用 0 字节占位文件配合 mock。
                # 这里不提前 return/continue，而是仅提示并继续尝试加载；
                # 若真实文件不可解码，会在后续异常处理中被捕获并继续尝试下一张。
                try:
                    if os.path.getsize(photo_path) <= 0:
                        logger.warning(f"学生 {student_name} 的参考照片为空文件(0字节)，将尝试读取: {photo_path}")
                except Exception:
                    pass
                
                rel = self._rel_to_input(photo_path)
                try:
                    st = os.stat(photo_path)
                    mtime = int(st.st_mtime)
                    size = int(st.st_size)
                except Exception:
                    mtime = 0
                    size = 0

                selected_for_fingerprint.append({'rel_path': rel, 'mtime': mtime, 'size': size})

                prev_item = prev_items_by_rel.get(rel)
                if prev_item and int(prev_item.get('mtime', -1)) == mtime and int(prev_item.get('size', -1)) == size:
                    status = prev_item.get('status')
                    cache_file = prev_item.get('cache')
                    if status == 'ok' and isinstance(cache_file, str):
                        cache_path = self._ref_cache_dir / cache_file
                        try:
                            if cache_path.exists():
                                enc = np.load(str(cache_path))
                                encodings.append(enc)
                                student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': 'ok', 'cache': cache_file})
                                continue
                        except Exception:
                            pass
                    if status in ('no_face', 'error'):
                        # 未变化的失败参考照：直接沿用失败状态，避免重复计算
                        student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': str(status)})
                        continue

                image = None
                face_locations = None

                try:
                    image = face_recognition.load_image_file(photo_path)
                    face_locations = face_recognition.face_locations(image)

                    if not face_locations:
                        logger.warning(f"在照片中未检测到人脸: {photo_path}")
                        student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': 'no_face'})
                        if image is not None:
                            del image
                        if face_locations is not None:
                            del face_locations
                        continue

                    face_encoding = face_recognition.face_encodings(image, face_locations)[0]

                    # 写入 per-photo 缓存
                    cache_key = hashlib.sha1(f"{rel}|{mtime}|{size}".encode("utf-8")).hexdigest()
                    cache_file = f"{cache_key}.npy"
                    cache_path = self._ref_cache_dir / cache_file
                    try:
                        np.save(str(cache_path), face_encoding)
                    except Exception:
                        cache_file = ""

                    encodings.append(face_encoding)
                    student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': 'ok', 'cache': cache_file})

                except MemoryError:
                    logger.error(
                        f"处理学生 {student_name} 的照片时内存不足: {photo_path}。"
                        "请关闭其他程序或分批处理照片后重试。"
                    )
                    student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': 'error', 'error': 'memory'})
                    if image is not None:
                        del image
                    if face_locations is not None:
                        del face_locations
                    # 内存不足时不再继续尝试更多参考照（避免雪崩）
                    break
                except Exception as e:
                    logger.error(f"加载学生 {student_name} 的照片 {photo_path} 失败: {str(e)}")
                    student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': 'error', 'error': str(e)[:120]})
                    if image is not None:
                        del image
                    if face_locations is not None:
                        del face_locations
                    continue

                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations

            next_snapshot['students'][student_name] = student_items

            if encodings:
                self.students_encodings[student_name] = {
                    'name': student_name,
                    'encodings': encodings,
                }
                loaded_count += 1
            else:
                failed_count += 1
        
        self._refresh_known_faces()

        # 写入 snapshot，并生成 reference_fingerprint（用于识别缓存失效）
        self.reference_fingerprint = self._make_reference_fingerprint(selected_for_fingerprint)
        next_snapshot['reference_fingerprint'] = self.reference_fingerprint
        self._save_ref_snapshot(next_snapshot)

        logger.info(f"成功加载 {loaded_count} 名学生的面部编码，失败 {failed_count} 名")
        
        # 允许空数据集：无参考照时继续运行，后续识别将返回未知
        if loaded_count == 0:
            logger.warning("未加载到学生面部编码，将作为空数据集继续运行")
    
    def recognize_faces(self, image_path, return_details=False):
        """识别照片中的所有人脸。

        参数：
        - image_path：图片路径
        - return_details：是否返回详细状态（成功/无人脸/无匹配/错误等）

        返回：
        - return_details=False：返回识别到的学生姓名列表（去重）
        - return_details=True：返回包含 status/message/recognized_students 等字段的 dict
        """
        image = None
        face_locations = None
        face_encodings = None
        
        try:
            # 不对 0 字节文件做“提前返回”，以便测试可用占位文件 + mock。
            # 若真实文件不可解码，将由下面的异常处理返回友好错误。
            try:
                if os.path.getsize(image_path) <= 0:
                    logger.warning(f"图片文件为空(0字节)，将尝试读取: {image_path}")
            except Exception:
                pass

            # 加载图片
            image = face_recognition.load_image_file(image_path)
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                logger.debug(f"在图片中未检测到人脸: {image_path}")
                # 释放内存
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                
                if return_details:
                    return {
                        'status': 'no_faces_detected',
                        'message': '图片中未检测到人脸',
                        'recognized_students': [],
                        'total_faces': 0
                    }
                return []
            
            sizeable_locations = []
            for location in face_locations:
                top, right, bottom, left = location
                if (bottom - top) >= MIN_FACE_SIZE and (right - left) >= MIN_FACE_SIZE:
                    sizeable_locations.append(location)
                else:
                    logger.debug(
                        "忽略过小的人脸: 宽度=%s 高度=%s", (right - left), (bottom - top)
                    )

            if not sizeable_locations:
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                if return_details:
                    return {
                        'status': 'no_faces_detected',
                        'message': '检测到的人脸尺寸过小，无法识别',
                        'recognized_students': [],
                        'total_faces': 0
                    }
                return []

            # 获取所有可用人脸的编码
            face_encodings = face_recognition.face_encodings(image, sizeable_locations)
            face_locations = sizeable_locations
            
            if not self.known_encodings:
                warning_msg = "没有找到任何可用的学生面部编码"
                logger.warning(warning_msg)
                if return_details:
                    total_faces_detected = len(face_encodings)
                    return {
                        'status': 'no_matches_found',
                        'message': warning_msg,
                        'recognized_students': [],
                        'total_faces': total_faces_detected,
                        'unknown_faces': total_faces_detected
                    }
                return []

            # 识别每张人脸
            recognized_students = []
            unknown_faces_count = 0
            known_encodings = self.known_encodings
            known_names = self.known_student_names
            
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(
                    known_encodings,
                    face_encoding,
                    tolerance=self.tolerance
                )
                
                face_distances = face_recognition.face_distance(
                    known_encodings,
                    face_encoding
                )
                
                best_match_index = None
                if len(face_distances) > 0:
                    best_match_index = int(np.argmin(face_distances))
                
                if best_match_index is not None and matches[best_match_index]:
                    student_name = known_names[best_match_index]
                    if student_name not in recognized_students:
                        recognized_students.append(student_name)
                else:
                    unknown_faces_count += 1
                    logger.debug(f"在图片中识别到未知人脸: {image_path}")
            
            # 存储结果，在内存释放前返回
            result = None
            if return_details:
                status = 'success' if recognized_students else 'no_matches_found'
                total_faces_detected = len(face_encodings)
                recognized_count = len(recognized_students)
                result = {
                    'status': status,
                    'message': f'检测到{total_faces_detected}张人脸，识别到{recognized_count}名学生',
                    'recognized_students': recognized_students,
                    'total_faces': total_faces_detected,
                    'unknown_faces': unknown_faces_count
                }
            else:
                result = recognized_students
            
            # 释放内存
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            if face_encodings is not None:
                del face_encodings
            
            return result
            
        except MemoryError:
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            if face_encodings is not None:
                del face_encodings
            warning_msg = (
                f"处理图片时内存不足: {image_path}。请关闭其他程序或减少单次处理的照片数量后重试。"
            )
            logger.error(warning_msg)
            if return_details:
                return {
                    'status': 'error',
                    'message': warning_msg,
                    'recognized_students': [],
                    'total_faces': 0
                }
            return []
        except Exception as e:
            # 发生异常时也要确保释放内存
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            if face_encodings is not None:
                del face_encodings
                
            error_msg = f"识别图片 {image_path} 中的人脸失败: {str(e)}"
            logger.error(error_msg)
            if return_details:
                return {
                    'status': 'error',
                    'message': error_msg,
                    'recognized_students': [],
                    'total_faces': 0
                }
            return []
    
    def verify_student_photo(self, student_name, image_path):
        """
        验证图片中是否包含指定学生
        :param student_name: 学生姓名
        :param image_path: 图片路径
        :return: 是否包含该学生
        """
        recognized = self.recognize_faces(image_path)
        return student_name in recognized
    
    def get_recognition_confidence(self, image_path, student_name):
        """
        获取识别特定学生的置信度
        :param image_path: 图片路径
        :param student_name: 学生姓名
        :return: 置信度分数 (0-1)，越大越可能是该学生
        """
        image = None
        face_locations = None
        face_encodings = None
        
        try:
            try:
                if os.path.getsize(image_path) <= 0:
                    return 0.0
            except Exception:
                pass
            # 找到学生的编码
            if student_name not in self.students_encodings:
                return 0.0
                
            student_encoding = self.students_encodings[student_name]['encoding']
            
            # 加载图片并识别人脸
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                # 释放内存
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                return 0.0
            
            sizeable_locations = []
            for location in face_locations:
                top, right, bottom, left = location
                if (bottom - top) >= MIN_FACE_SIZE and (right - left) >= MIN_FACE_SIZE:
                    sizeable_locations.append(location)

            if not sizeable_locations:
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                return 0.0

            face_encodings = face_recognition.face_encodings(image, sizeable_locations)
            face_locations = sizeable_locations
            
            # 计算每张人脸与目标学生的距离
            if not face_encodings:
                # 释放内存
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                return 0.0
            
            distances = [
                face_recognition.face_distance([student_encoding], encoding)[0]
                for encoding in face_encodings
            ]
            
            if len(distances) == 0:
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                if face_encodings is not None:
                    del face_encodings
                return 0.0
            
            # 将距离转换为置信度 (距离越小，置信度越高)
            min_distance = min(distances)
            confidence = 1.0 - min_distance
            
            # 存储结果，在内存释放前返回
            result = max(0.0, min(1.0, confidence))
            
            # 释放内存
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            if face_encodings is not None:
                del face_encodings
            
            return result
            
        except MemoryError:
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            if face_encodings is not None:
                del face_encodings
            logger.error(
                f"计算识别置信度时内存不足: {image_path}。请关闭其他程序或分批处理后重试。"
            )
            return 0.0
        except Exception as e:
            # 发生异常时也要确保释放内存
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            if face_encodings is not None:
                del face_encodings
                
            logger.error(f"计算识别置信度失败: {str(e)}")
            return 0.0
    
    def update_student_encoding(self, student_name, new_photo_path):
        """
        更新学生的面部编码
        :param student_name: 学生姓名
        :param new_photo_path: 新的照片路径
        :return: 是否更新成功
        """
        image = None
        face_locations = None
        
        try:
            if not os.path.exists(new_photo_path):
                logger.error(f"新照片不存在: {new_photo_path}")
                return False

            try:
                if os.path.getsize(new_photo_path) <= 0:
                    logger.error(f"新照片为空文件(0字节): {new_photo_path}")
                    return False
            except Exception:
                pass
            
            # 加载新照片并获取编码
            image = face_recognition.load_image_file(new_photo_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                logger.error(f"在新照片中未检测到人脸: {new_photo_path}")
                # 释放内存
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                return False
            
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # 更新编码
            if student_name in self.students_encodings:
                self.students_encodings[student_name] = {
                    'name': student_name,
                    'encodings': [face_encoding]
                }
                self._refresh_known_faces()
                
                # 释放内存
                if image is not None:
                    del image
                if face_locations is not None:
                    del face_locations
                
                logger.info(f"成功更新学生 {student_name} 的面部编码")
                return True
            
            # 释放内存
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            
            self._refresh_known_faces()
            return False
            
        except MemoryError:
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
            logger.error(
                f"更新学生 {student_name} 面部编码时内存不足: {new_photo_path}。"
                "请关闭其他程序或降低图片分辨率后重试。"
            )
            return False
        except Exception as e:
            # 发生异常时也要确保释放内存
            if image is not None:
                del image
            if face_locations is not None:
                del face_locations
                
            logger.error(f"更新学生面部编码失败: {str(e)}")
            return False
    
    def load_reference_photos(self, input_dir):
        """加载参考照片并生成人脸编码"""
        from .utils import is_supported_nonempty_image_path

        if not input_dir.exists() or not any(is_supported_nonempty_image_path(p) for p in input_dir.iterdir()):
            logger.warning("⚠️ 输入目录为空或不存在，请检查 input/student_photos 文件夹。")
            return {}

        face_encodings = {}
        for photo in input_dir.iterdir():
            if is_supported_nonempty_image_path(photo):
                # 模拟加载人脸编码逻辑
                face_encodings[photo] = {"encoding": [0.1, 0.2, 0.3]}  # 示例编码
        
        if not face_encodings:
            logger.warning("⚠️ 未找到有效的参考照片，所有课堂照片将归类到 unknown 目录。")
        return face_encodings