"""
人脸识别模块
负责人脸检测、特征提取和识别
"""

import os
import logging
import warnings
import contextlib
import io
import numpy as np
import hashlib
import json
from pathlib import Path
from typing import Any
from .config import DEFAULT_TOLERANCE, MIN_FACE_SIZE

# InsightFace 的部分依赖（如 albumentations）在导入时可能尝试联网检查版本，离线/打包环境会产生噪声警告。
# 注意：该 warning 的 message 可能以换行开头，因此用 \s* 兼容。
warnings.filterwarnings("ignore", message=r"\s*Error fetching version info.*")

try:
    from insightface.app import FaceAnalysis  # type: ignore
except Exception as e:  # pragma: no cover
    _INSIGHTFACE_IMPORT_ERROR = e
    FaceAnalysis = None  # type: ignore


def _normalize_face_backend_engine(raw: str) -> str:
    v = (raw or "").strip().lower()
    if v in ("insightface", "insight", "arcface"):
        return "insightface"
    if v in ("dlib", "face_recognition", "facerecognition"):
        return "dlib"
    return "insightface"


def _get_selected_face_backend_engine() -> str:
    return _normalize_face_backend_engine(os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND", ""))


def _safe_key(s: str) -> str:
    out = []
    for ch in (s or ""):
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        else:
            out.append("_")
    v = "".join(out).strip("_")
    return v or "default"


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance in [0, 2]. Smaller is more similar."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    an = float(np.linalg.norm(a) + 1e-12)
    bn = float(np.linalg.norm(b) + 1e-12)
    return float(1.0 - (np.dot(a, b) / (an * bn)))


def _normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v) + 1e-12)
    return v / n


class _InsightFaceCompat:
    """A minimal face_recognition-like API backed by InsightFace.

    目标：尽量不改动上层业务逻辑，保持 FaceRecognizer 的对外行为。
    """

    def __init__(self) -> None:
        if FaceAnalysis is None:
            raise ModuleNotFoundError(
                "未安装 InsightFace（人脸识别依赖）。请先安装 requirements.txt 中的依赖。"
            ) from _INSIGHTFACE_IMPORT_ERROR
        self._app = None

    def _get_app(self):
        if self._app is not None:
            return self._app

        # 默认静默 InsightFace/onnxruntime 的模型加载噪声输出（会破坏 tqdm 进度条）。
        # 需要排障时可设置：SUNDAY_PHOTOS_DIAG_ENV=1
        diag_enabled = os.environ.get("SUNDAY_PHOTOS_DIAG_ENV", "").strip().lower() in ("1", "true", "yes")
        quiet_models = os.environ.get("SUNDAY_PHOTOS_QUIET_MODELS", "1").strip().lower() in ("1", "true", "yes")
        suppress_output = bool(quiet_models and (not diag_enabled))

        # 额外：尽力降低 onnxruntime 的 logger 噪声（不同版本 API/环境变量略有差异）
        # - ORT_LOG_SEVERITY_LEVEL: 0-4 (verbose/info/warning/error/fatal)
        # - 我们用 3=error，尽量只保留真正错误
        if suppress_output:
            os.environ.setdefault("ORT_LOG_SEVERITY_LEVEL", "3")
            try:
                import onnxruntime as ort  # type: ignore

                try:
                    ort.set_default_logger_severity(3)
                except Exception:
                    pass
            except Exception:
                pass

        # Model storage:
        # - Default: ~/.insightface
        # - Optional override via env for portable/offline deployments
        model_root = os.environ.get("SUNDAY_PHOTOS_INSIGHTFACE_HOME", "").strip() or None
        model_name = os.environ.get("SUNDAY_PHOTOS_INSIGHTFACE_MODEL", "").strip() or "buffalo_l"

        # 注意：InsightFace 的 FaceAnalysis 不接受 root=None（会触发 TypeError）。
        # - 未提供 override 时，直接省略 root 参数，让其使用默认 ~/.insightface。
        # InsightFace 内部会 print 模型信息（find model / Applied providers）。这里对初始化阶段做输出重定向。
        sink = io.StringIO()
        redir = contextlib.nullcontext()
        if suppress_output:
            redir = contextlib.redirect_stdout(sink)
        with redir:
            redir_err = contextlib.nullcontext()
            if suppress_output:
                redir_err = contextlib.redirect_stderr(sink)
            with redir_err:
                if model_root is None:
                    app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
                else:
                    app = FaceAnalysis(name=model_name, root=model_root, providers=["CPUExecutionProvider"])
                # det_size affects detection quality/speed; keep a sensible default.
                app.prepare(ctx_id=0, det_size=(640, 640))
        self._app = app
        return app

    def load_image_file(self, image_path: str):
        # Keep behavior consistent: return RGB ndarray
        try:
            from PIL import Image, ImageOps

            with Image.open(image_path) as im:
                im = ImageOps.exif_transpose(im)
                im = im.convert("RGB")
                return np.asarray(im)
        except Exception as e:
            # Mirror previous behavior: bubble up for caller to handle
            raise

    def _detect(self, image_rgb: np.ndarray):
        app = self._get_app()
        # InsightFace expects BGR
        image_bgr = image_rgb[:, :, ::-1]
        faces = app.get(image_bgr) or []
        return faces

    def face_locations(self, image, *args, **kwargs):
        faces = self._detect(np.asarray(image))
        locs = []
        for f in faces:
            try:
                x1, y1, x2, y2 = f.bbox
                top = int(round(y1))
                right = int(round(x2))
                bottom = int(round(y2))
                left = int(round(x1))
                locs.append((top, right, bottom, left))
            except Exception:
                continue
        return locs

    def face_encodings(self, image, face_locations=None, *args, **kwargs):
        faces = self._detect(np.asarray(image))
        if not faces:
            return []

        # Map requested locations to nearest detected bbox (stable enough for our usage).
        requested = list(face_locations or [])
        if not requested:
            requested = []
            for f in faces:
                x1, y1, x2, y2 = f.bbox
                requested.append((int(round(y1)), int(round(x2)), int(round(y2)), int(round(x1))))

        encs = []
        det_boxes = []
        for f in faces:
            x1, y1, x2, y2 = f.bbox
            det_boxes.append((int(round(y1)), int(round(x2)), int(round(y2)), int(round(x1)), f))

        for (top, right, bottom, left) in requested:
            best = None
            best_score = None
            for (dt, dr, db, dl, f) in det_boxes:
                score = abs(dt - top) + abs(dr - right) + abs(db - bottom) + abs(dl - left)
                if best_score is None or score < best_score:
                    best_score = score
                    best = f
            if best is None:
                continue
            try:
                encs.append(_normalize(best.embedding))
            except Exception:
                continue
        return encs

    def face_distance(self, known_encodings, face_encoding):
        if known_encodings is None:
            return np.asarray([], dtype=np.float32)
        fe = np.asarray(face_encoding, dtype=np.float32).reshape(-1)
        out = []
        for ke in known_encodings:
            ke_arr = np.asarray(ke, dtype=np.float32).reshape(-1)
            # 兼容旧缓存（dlib/face_recognition 常见为 128 维；InsightFace 常见为 512 维）。
            # 维度不一致时，返回最大距离，避免崩溃并确保不会误匹配。
            if ke_arr.shape != fe.shape:
                out.append(2.0)
                continue
            out.append(_cosine_distance(ke_arr, fe))
        return np.asarray(out, dtype=np.float32)

    def compare_faces(self, known_encodings, face_encoding, tolerance=0.6):
        d = self.face_distance(known_encodings, face_encoding)
        tol = float(tolerance)
        return [bool(x <= tol) for x in d.tolist()]


class _DlibFaceRecognitionCompat:
    """A minimal face_recognition-like API backed by face_recognition/dlib."""

    def __init__(self) -> None:
        try:
            import face_recognition as fr  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ModuleNotFoundError(
                "未安装 face_recognition/dlib（人脸识别后端）。如需使用 dlib 后端，请先安装 face_recognition 与 dlib。"
            ) from e
        self._fr = fr

    def load_image_file(self, image_path: str):
        # 统一行为：返回 RGB ndarray，并处理 EXIF 方向
        try:
            from PIL import Image, ImageOps

            with Image.open(image_path) as im:
                im = ImageOps.exif_transpose(im)
                im = im.convert("RGB")
                return np.asarray(im)
        except Exception:
            # 回退到 face_recognition 自带实现
            return self._fr.load_image_file(image_path)

    def face_locations(self, image, number_of_times_to_upsample=0, model="hog"):
        try:
            return self._fr.face_locations(
                image,
                number_of_times_to_upsample=number_of_times_to_upsample,
                model=model,
            )
        except TypeError:
            # 兼容旧签名
            return self._fr.face_locations(image)

    def face_encodings(self, image, face_locations=None, *args, **kwargs):
        try:
            return self._fr.face_encodings(image, known_face_locations=face_locations)
        except TypeError:
            # 兼容旧签名
            return self._fr.face_encodings(image, face_locations)

    def face_distance(self, known_encodings, face_encoding):
        return self._fr.face_distance(known_encodings, face_encoding)

    def compare_faces(self, known_encodings, face_encoding, tolerance=0.6):
        return self._fr.compare_faces(known_encodings, face_encoding, tolerance=tolerance)


def _get_backend_model_name(engine: str) -> str:
    if engine == "insightface":
        return os.environ.get("SUNDAY_PHOTOS_INSIGHTFACE_MODEL", "").strip() or "buffalo_l"
    return "face_recognition"


def _get_backend_embedding_dim(engine: str) -> int:
    # 约定：InsightFace ArcFace embedding 常见 512 维；dlib/face_recognition 常见 128 维。
    return 512 if engine == "insightface" else 128


_FACE_BACKEND_INIT_ERROR: Exception | None = None
_FACE_BACKEND_SINGLETON: Any | None = None


def _init_face_backend():
    global _FACE_BACKEND_INIT_ERROR
    engine = _get_selected_face_backend_engine()
    try:
        if engine == "dlib":
            return _DlibFaceRecognitionCompat()
        return _InsightFaceCompat()
    except Exception as e:  # pragma: no cover
        _FACE_BACKEND_INIT_ERROR = e
        return None


def _get_face_backend_singleton():
    """Lazily initialize the selected backend and cache it.

    Why lazy?
    - Import-time initialization can be expensive (dlib loads native libs; InsightFace loads model zoo).
    - In multiprocessing spawn children, import-time init can cause hangs/timeouts.
    """
    global _FACE_BACKEND_SINGLETON
    if _FACE_BACKEND_SINGLETON is not None:
        return _FACE_BACKEND_SINGLETON
    _FACE_BACKEND_SINGLETON = _init_face_backend()
    return _FACE_BACKEND_SINGLETON


class _LazyFaceBackend:
    """A lightweight proxy that behaves like the old module-level `face_recognition`.

    It initializes the real backend upon first attribute access.
    """

    def _ensure(self):
        backend = _get_face_backend_singleton()
        if backend is None:
            engine = _get_selected_face_backend_engine()
            raise ModuleNotFoundError(
                f"人脸识别后端依赖未就绪（SUNDAY_PHOTOS_FACE_BACKEND={engine}）"
            ) from _FACE_BACKEND_INIT_ERROR
        return backend

    def __getattr__(self, item: str):
        backend = self._ensure()
        return getattr(backend, item)


# Module-level proxy (keeps old import sites working)
face_recognition = _LazyFaceBackend()  # type: ignore

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """人脸识别器"""
    
    def __init__(self, student_manager, tolerance=None, min_face_size=None):
        """初始化人脸识别器。

        参数：
        - student_manager：学生管理器实例，用于加载学生参考照片与学生名册
        - tolerance：人脸识别阈值（越小越严格），默认取配置 DEFAULT_TOLERANCE
        """

        if tolerance is None:
            tolerance = DEFAULT_TOLERANCE
        if min_face_size is None:
            min_face_size = MIN_FACE_SIZE
        self.student_manager = student_manager
        self.tolerance = tolerance
        self.min_face_size = int(min_face_size)
        self.students_encodings = {}
        self.known_student_names = []
        self.known_encodings = []

        # 后端选择（用于缓存隔离与兼容判断）
        self._backend_engine = _get_selected_face_backend_engine()
        self._backend_model = _get_backend_model_name(self._backend_engine)
        self._backend_embedding_dim = _get_backend_embedding_dim(self._backend_engine)

        # 参考照增量缓存（提升速度 + 支持增删 diff）
        self._ref_cache_dir = self._resolve_ref_cache_dir()
        self._ref_snapshot_path = self._resolve_ref_snapshot_path()
        self.reference_fingerprint = ""  # 用于识别缓存失效（参考照变化即变化）

        if face_recognition is None:  # pragma: no cover
            engine = self._backend_engine
            if engine == "dlib":
                msg = (
                    "人脸识别后端(dlib/face_recognition)依赖未就绪。"
                    "如需使用 dlib 后端，请先安装 face_recognition 与 dlib，"
                    "或将 SUNDAY_PHOTOS_FACE_BACKEND 设置为 insightface。"
                )
            else:
                msg = (
                    "人脸识别后端(InsightFace)依赖未就绪。请先安装 requirements.txt 并确保可导入 insightface/onnxruntime。"
                )
            if _FACE_BACKEND_INIT_ERROR is not None:
                raise ModuleNotFoundError(msg) from _FACE_BACKEND_INIT_ERROR
            raise ModuleNotFoundError(msg)
        
        # 加载所有学生的面部编码
        self.load_student_encodings()

    def _load_image_with_exif_fix(self, image_path: str):
        """加载图片并尽量修正 EXIF 方向。

        说明：不少手机照片“视觉上是正的”，但实际像素是旋转的，方向信息写在 EXIF 里。
        dlib/face_recognition 的检测是基于像素数组的；如果不先转正，可能会出现“有脸但检测不到”。
        """

        # 为了可测试性：统一委托给 face_recognition.load_image_file。
        # InsightFace 兼容层内部已处理 EXIF 转正与 RGB 输出。
        return face_recognition.load_image_file(image_path)

    def _face_locations_for_reference(self, image):
        """参考照的人脸检测策略：更偏向“尽量找出来”，允许更慢一点。

        参考照数量通常较少；提高参考照编码成功率比节省这几秒更重要。
        """

        # 1) 默认（hog + upsample=0）
        try:
            locs = face_recognition.face_locations(image)
        except TypeError:
            # 兼容极老版本签名
            locs = face_recognition.face_locations(image)

        if locs:
            return locs

        # 2) 放大再找（对小脸/远景更有效）
        try:
            locs = face_recognition.face_locations(image, number_of_times_to_upsample=1)
            if locs:
                return locs
            locs = face_recognition.face_locations(image, number_of_times_to_upsample=2)
            if locs:
                return locs
        except TypeError:
            pass

        # 3) 最后回退：cnn（更准但更慢；只用于参考照阶段）
        try:
            locs = face_recognition.face_locations(image, number_of_times_to_upsample=1, model="cnn")
            if locs:
                return locs
        except Exception:
            pass

        return []

    def _resolve_ref_cache_dir(self) -> Path:
        """参考照编码缓存目录（跟随 input_dir/logs，打包版也可用）。"""
        try:
            input_dir = Path(getattr(self.student_manager, 'input_dir'))
        except Exception:
            input_dir = Path(".")
        engine = _safe_key(getattr(self, "_backend_engine", _get_selected_face_backend_engine()))
        model = _safe_key(getattr(self, "_backend_model", _get_backend_model_name(_get_selected_face_backend_engine())))
        d = input_dir / "logs" / "reference_encodings" / engine / model
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
        engine = _safe_key(getattr(self, "_backend_engine", _get_selected_face_backend_engine()))
        model = _safe_key(getattr(self, "_backend_model", _get_backend_model_name(_get_selected_face_backend_engine())))
        p = input_dir / "logs" / "reference_index" / engine / f"{model}.json"
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

        # 参考照编码缓存兼容：
        # - 旧版本可能来自 face_recognition/dlib（128 维）
        # - 新版本改用 InsightFace（常见 512 维）
        # 若 snapshot 缺少引擎元信息或 embedding_dim 不一致，则视为“引擎升级”，自动失效并重建缓存。
        prev = self._load_ref_snapshot()

        current_engine = getattr(self, "_backend_engine", _get_selected_face_backend_engine())
        current_model = getattr(self, "_backend_model", _get_backend_model_name(current_engine))
        current_embedding_dim = int(getattr(self, "_backend_embedding_dim", _get_backend_embedding_dim(current_engine)))

        prev_engine = str(prev.get("engine") or "").strip()
        prev_model = str(prev.get("engine_model") or "").strip()
        prev_dim_raw = prev.get("embedding_dim")
        try:
            prev_dim = int(prev_dim_raw) if prev_dim_raw is not None else None
        except Exception:
            prev_dim = None

        cache_compatible = (
            prev.get("version") == 2
            and prev_engine == current_engine
            and prev_model == current_model
            and prev_dim == current_embedding_dim
        )

        prev_items_by_rel: dict[str, dict] = {}
        if cache_compatible:
            for student_name, items in (prev.get('students') or {}).items():
                if not isinstance(items, list):
                    continue
                for it in items:
                    rel = it.get('rel_path')
                    if isinstance(rel, str):
                        prev_items_by_rel[rel] = it

        next_snapshot: dict = {
            'version': 2,
            'mode': 'student_folder_only',
            'max_photos_per_student': 5,
            'engine': current_engine,
            'engine_model': current_model,
            'embedding_dim': current_embedding_dim,
            'students': {},
        }
        selected_for_fingerprint: list[dict] = []

        # 汇总：参考照中“检测不到人脸/异常”的文件清单，便于老师快速替换
        no_face_by_student: dict[str, list[str]] = {}
        error_by_student: dict[str, list[str]] = {}
        
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
                        if status == 'no_face':
                            no_face_by_student.setdefault(student_name, []).append(rel)
                        elif status == 'error':
                            error_by_student.setdefault(student_name, []).append(rel)
                        continue

                image = None
                face_locations = None

                try:
                    image = self._load_image_with_exif_fix(photo_path)
                    face_locations = self._face_locations_for_reference(image)

                    if not face_locations:
                        logger.warning(f"在照片中未检测到人脸: {photo_path}")
                        student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': 'no_face'})
                        no_face_by_student.setdefault(student_name, []).append(rel)
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
                    error_by_student.setdefault(student_name, []).append(rel)
                    if image is not None:
                        del image
                    if face_locations is not None:
                        del face_locations
                    # 内存不足时不再继续尝试更多参考照（避免雪崩）
                    break
                except Exception as e:
                    logger.error(f"加载学生 {student_name} 的照片 {photo_path} 失败: {str(e)}")
                    student_items.append({'rel_path': rel, 'mtime': mtime, 'size': size, 'status': 'error', 'error': str(e)[:120]})
                    error_by_student.setdefault(student_name, []).append(rel)
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

            # 参考照失败汇总提示：
            # - 无编码：WARNING（会显著影响该学生识别准确率）
            # - 有编码但部分失败：INFO（给出替换/裁剪建议）
            no_face_list = no_face_by_student.get(student_name, [])
            err_list = error_by_student.get(student_name, [])
            if (not encodings) or no_face_list or err_list:
                def _fmt(items: list[str]) -> str:
                    shown = items[:5]
                    suffix = "" if len(items) <= 5 else f" ...（还有 {len(items) - 5} 张）"
                    if not shown:
                        return ""
                    return "\n".join([f"    - {p}" for p in shown]) + suffix

                if not encodings:
                    header = (
                        f"学生 {student_name} 没有生成任何可用的人脸编码：该学生在课堂照中将更容易被误识别或进入 unknown。"
                    )
                else:
                    header = (
                        f"学生 {student_name} 的参考照部分不可用：成功编码 {len(encodings)} 张；"
                        f"检测不到人脸 {len(no_face_list)} 张；读取/编码异常 {len(err_list)} 张。"
                    )

                msg_lines = [
                    header,
                    "建议：为该学生补 3–5 张清晰、单人、正脸、无遮挡的近照（尽量与课堂照年代接近）；避免侧脸/模糊/滤镜重/脸太小。",
                ]
                if no_face_list:
                    msg_lines.append("以下参考照检测不到人脸（优先替换/裁剪成单人正脸）：")
                    msg_lines.append(_fmt(no_face_list))
                if err_list:
                    msg_lines.append("以下参考照读取/编码异常（可尝试重新导出为 JPG/PNG 后替换）：")
                    msg_lines.append(_fmt(err_list))

                if not encodings:
                    logger.warning("\n".join(msg_lines))
                elif no_face_list or err_list:
                    logger.info("\n".join(msg_lines))
        
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

            # 加载图片（修正 EXIF 方向，减少“有脸但检测不到”）
            image = self._load_image_with_exif_fix(image_path)
            
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
                if (bottom - top) >= self.min_face_size and (right - left) >= self.min_face_size:
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
            unknown_encodings = []
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
                    unknown_encodings.append(face_encoding)
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
                    'unknown_faces': unknown_faces_count,
                    'unknown_encodings': unknown_encodings
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
            # 找到学生的编码（支持多编码）
            if student_name not in self.students_encodings:
                return 0.0
                
            student_encodings = self.students_encodings[student_name]['encodings']
            if not student_encodings:
                return 0.0
            
            # 加载图片并识别人脸
            image = self._load_image_with_exif_fix(image_path)
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
            
            # 对每个参考编码和每个检测到的人脸计算距离，取全局最小值
            all_distances = []
            for face_encoding in face_encodings:
                for student_encoding in student_encodings:
                    distance = face_recognition.face_distance([student_encoding], face_encoding)[0]
                    all_distances.append(distance)
            
            distances = all_distances
            
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
            image = self._load_image_with_exif_fix(new_photo_path)
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
                
                # 持久化更新：保存到缓存文件和snapshot
                try:
                    rel = self._rel_to_input(new_photo_path)
                    st = os.stat(new_photo_path)
                    mtime = int(st.st_mtime)
                    size = int(st.st_size)
                    
                    # 写入 per-photo 缓存
                    cache_key = hashlib.sha1(f"{rel}|{mtime}|{size}".encode("utf-8")).hexdigest()
                    cache_file = f"{cache_key}.npy"
                    cache_path = self._ref_cache_dir / cache_file
                    np.save(str(cache_path), face_encoding)
                    
                    # 重新加载snapshot并更新
                    prev = self._load_ref_snapshot()
                    students_data = prev.get('students', {}) if prev else {}
                    students_data[student_name] = [{
                        'rel_path': rel,
                        'mtime': mtime,
                        'size': size,
                        'status': 'ok',
                        'cache': cache_file
                    }]
                    
                    # 重新计算fingerprint
                    selected_for_fingerprint = [{'rel_path': rel, 'mtime': mtime, 'size': size}]
                    self.reference_fingerprint = self._make_reference_fingerprint(selected_for_fingerprint)
                    
                    next_snapshot = {
                        'version': 1,
                        'mode': 'student_folder_only',
                        'max_photos_per_student': 5,
                        'students': students_data,
                        'reference_fingerprint': self.reference_fingerprint
                    }
                    self._save_ref_snapshot(next_snapshot)
                    
                    logger.debug(f"已持久化学生 {student_name} 的更新编码")
                except Exception as e:
                    logger.debug(f"持久化编码失败（不影响当前会话）: {e}")
                
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