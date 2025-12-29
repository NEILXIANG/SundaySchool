"""配置加载器模块：加载、合并、解析配置。"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict

from .config import (
    BASE_DIR,
    CONFIG_FILE_PATH,
    DEFAULT_CONFIG,
    DEFAULT_INPUT_DIR,
    DEFAULT_LOG_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_UNKNOWN_FACE_CLUSTERING,
    DEFAULT_PARALLEL_RECOGNITION,
    DEFAULT_TOLERANCE,
    MIN_FACE_SIZE,
    resolve_path,
)

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器，支持从 JSON 文件加载并与默认值合并。"""

    def __init__(self, config_file: Path | str | None = None, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.config_file = Path(config_file) if config_file else CONFIG_FILE_PATH
        self.config_data: Dict[str, Any] = {}

        # 尝试加载配置文件
        self.load_config()

    def load_config(self) -> None:
        """从文件加载配置，失败则回退默认值。"""

        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                logger.info(f"已加载配置文件: {self.config_file}")
            else:
                logger.info(f"配置文件不存在: {self.config_file}，使用默认配置")
                raw = {}

            self.config_data = self._merge_with_defaults(raw)
        except (OSError, IOError) as e:
            # 文件读取错误（权限、不存在等）
            logger.error(f"配置文件读取失败: {e}，使用默认配置")
            self.config_data = dict(DEFAULT_CONFIG)
        except (json.JSONDecodeError, ValueError) as e:
            # JSON 解析错误（语法错误、格式错误）
            logger.error(f"配置文件格式错误: {e}，使用默认配置")
            self.config_data = dict(DEFAULT_CONFIG)
        except Exception as e:
            # 未预期错误（应该记录完整堆栈以便排查）
            logger.exception(f"加载配置文件时发生未预期错误: {e}")
            self.config_data = dict(DEFAULT_CONFIG)

    def save_config(self) -> bool:
        """保存配置到文件。"""

        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到: {self.config_file}")
            return True
        except (OSError, IOError) as e:
            # 文件写入错误（权限、磁盘空间等）
            logger.error(f"配置文件保存失败: {e}")
            return False
        except Exception as e:
            # 未预期错误
            logger.exception(f"保存配置时发生未预期错误: {e}")
            return False

    def _merge_with_defaults(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(DEFAULT_CONFIG)
        merged.update(raw or {})

        # 兼容字段提升（历史/打包版曾生成 face_recognition.*）：
        # 默认配置会让顶层 tolerance/min_face_size 永远存在。
        # 为了让兼容字段真正生效，这里在“用户未显式设置顶层字段”时，将其提升到顶层。
        try:
            raw_dict = raw or {}
            fr = raw_dict.get("face_recognition", {}) or {}
            if isinstance(fr, dict):
                if raw_dict.get("tolerance", None) is None and fr.get("tolerance", None) is not None:
                    merged["tolerance"] = fr.get("tolerance")
                if raw_dict.get("min_face_size", None) is None and fr.get("min_face_size", None) is not None:
                    merged["min_face_size"] = fr.get("min_face_size")
        except Exception:
            # 兼容提升失败不应阻断正常加载
            pass

        # 确保并行配置结构完整
        pr: Dict[str, Any] = dict(DEFAULT_PARALLEL_RECOGNITION)
        pr_config = merged.get("parallel_recognition", {}) or {}
        if isinstance(pr_config, dict):
            pr.update(pr_config)
        merged["parallel_recognition"] = pr

        # 确保未知聚类配置结构完整
        uc: Dict[str, Any] = dict(DEFAULT_UNKNOWN_FACE_CLUSTERING)
        uc_config = merged.get("unknown_face_clustering", {}) or {}
        if isinstance(uc_config, dict):
            uc.update(uc_config)
        merged["unknown_face_clustering"] = uc
        return merged

    def get(self, key: str, default: Any = None) -> Any:
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config_data[key] = value

    def update(self, data: Dict[str, Any]) -> None:
        self.config_data.update(data)

    def get_input_dir(self) -> str:
        return str(resolve_path(self.get("input_dir", DEFAULT_INPUT_DIR), self.base_dir))

    def get_output_dir(self) -> str:
        return str(resolve_path(self.get("output_dir", DEFAULT_OUTPUT_DIR), self.base_dir))

    def get_log_dir(self) -> str:
        return str(resolve_path(self.get("log_dir", DEFAULT_LOG_DIR), self.base_dir))

    def get_tolerance(self) -> float:
        # 兼容两种写法：
        # 1) 顶层 tolerance（推荐，文档口径）
        # 2) face_recognition.tolerance（历史/打包版曾生成过）
        raw = self.get("tolerance", None)
        if raw is None:
            fr = self.get("face_recognition", {}) or {}
            if isinstance(fr, dict):
                raw = fr.get("tolerance", None)
        try:
            return float(raw if raw is not None else DEFAULT_TOLERANCE)
        except Exception:
            return DEFAULT_TOLERANCE

    def get_min_face_size(self) -> int:
        """获取最小人脸尺寸（像素）。"""

        # 兼容两种写法：
        # 1) 顶层 min_face_size（推荐，文档口径）
        # 2) face_recognition.min_face_size（示例 config.json 中使用）
        raw = self.get("min_face_size", None)
        if raw is None:
            fr = self.get("face_recognition", {}) or {}
            if isinstance(fr, dict):
                raw = fr.get("min_face_size", None)
        try:
            return int(raw if raw is not None else MIN_FACE_SIZE)
        except Exception:
            return int(MIN_FACE_SIZE)

    def get_unknown_face_clustering(self) -> Dict[str, Any]:
        """获取未知人脸聚类配置（unknown_face_clustering）。"""

        uc = dict(self.config_data.get("unknown_face_clustering", DEFAULT_UNKNOWN_FACE_CLUSTERING))

        # 最小保护与类型归一
        try:
            uc["enabled"] = bool(uc.get("enabled", DEFAULT_UNKNOWN_FACE_CLUSTERING["enabled"]))
            uc["threshold"] = float(uc.get("threshold", DEFAULT_UNKNOWN_FACE_CLUSTERING["threshold"]))
            uc["min_cluster_size"] = max(1, int(uc.get("min_cluster_size", DEFAULT_UNKNOWN_FACE_CLUSTERING["min_cluster_size"])))
        except Exception:
            uc = dict(DEFAULT_UNKNOWN_FACE_CLUSTERING)

        return uc

    def get_parallel_recognition(self) -> Dict[str, Any]:
        """获取并行识别配置，支持环境变量开关与参数覆盖。"""

        pr = dict(self.config_data.get("parallel_recognition", DEFAULT_PARALLEL_RECOGNITION))

        # 环境变量智能控制：支持强制开启或关闭
        # 优先级：环境变量 > config.json
        env_disable = os.environ.get("SUNDAY_PHOTOS_NO_PARALLEL", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )
        env_enable = os.environ.get("SUNDAY_PHOTOS_PARALLEL", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )
        
        if env_disable:
            pr["enabled"] = False
        elif env_enable:
            pr["enabled"] = True

        # 可选：通过环境变量覆盖并行启用阈值（便于调试/临时加速）
        # - SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS=0  表示“只要 workers>=2 就允许并行”
        env_min_photos = os.environ.get("SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS", "").strip()
        if env_min_photos:
            try:
                pr["min_photos"] = max(0, int(env_min_photos))
            except Exception:
                pass

        # 最小保护（不做“智能拉高”，仅做合理的范围校验与 CPU 上限约束）
        try:
            requested_workers = max(1, int(pr.get("workers", DEFAULT_PARALLEL_RECOGNITION["workers"])))
            cpu_cores = max(1, int(os.cpu_count() or 1))

            # 上限：不超过 CPU 核心数（避免过量进程造成系统抖动）
            pr["workers"] = min(requested_workers, cpu_cores)
            pr["chunk_size"] = max(1, int(pr.get("chunk_size", DEFAULT_PARALLEL_RECOGNITION["chunk_size"])))
            pr["min_photos"] = max(0, int(pr.get("min_photos", DEFAULT_PARALLEL_RECOGNITION["min_photos"])))
            pr["enabled"] = bool(pr.get("enabled", False))
        except Exception:
            pr = dict(DEFAULT_PARALLEL_RECOGNITION)

        return pr

    def get_all_config(self) -> Dict[str, Any]:
        return dict(self.config_data)

    def get_face_backend_engine(self) -> str:
        """获取人脸识别后端引擎。

        支持：
        - 环境变量：SUNDAY_PHOTOS_FACE_BACKEND（优先级最高）
        - config.json：face_backend.engine 或 face_backend（字符串简写）

        允许值（大小写不敏感）：
        - insightface / insight / arcface
        - dlib / face_recognition
        """

        env = os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND", "").strip().lower()
        raw: str
        if env:
            raw = env
        else:
            raw_value = self.get("face_backend", None)
            if isinstance(raw_value, dict):
                engine_val = raw_value.get("engine")
                raw = str(engine_val).strip().lower() if engine_val else ""
            elif isinstance(raw_value, str):
                raw = raw_value.strip().lower()
            else:
                raw = ""

        if raw in ("insightface", "insight", "arcface"):
            return "insightface"
        if raw in ("dlib", "face_recognition", "facerecognition"):
            return "dlib"

        # 默认：InsightFace（当前主方案）
        return "insightface"