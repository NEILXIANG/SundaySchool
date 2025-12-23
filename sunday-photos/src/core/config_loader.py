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
    DEFAULT_PARALLEL_RECOGNITION,
    DEFAULT_TOLERANCE,
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
        except Exception:
            logger.exception("加载配置文件失败，使用默认配置")
            self.config_data = dict(DEFAULT_CONFIG)

    def save_config(self) -> bool:
        """保存配置到文件。"""

        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到: {self.config_file}")
            return True
        except Exception:
            logger.exception("保存配置文件失败")
            return False

    def _merge_with_defaults(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(DEFAULT_CONFIG)
        merged.update(raw or {})

        # 确保并行配置结构完整
        pr = dict(DEFAULT_PARALLEL_RECOGNITION)
        pr.update(merged.get("parallel_recognition", {}) or {})
        merged["parallel_recognition"] = pr
        return merged

    def get(self, key: str, default=None):
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
        try:
            return float(self.get("tolerance", DEFAULT_TOLERANCE))
        except Exception:
            return DEFAULT_TOLERANCE

    def get_parallel_recognition(self) -> Dict[str, Any]:
        """获取并行识别配置，支持环境变量智能控制。"""

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

        # 最小保护
        try:
            pr["workers"] = max(1, int(pr.get("workers", DEFAULT_PARALLEL_RECOGNITION["workers"])))
            pr["chunk_size"] = max(1, int(pr.get("chunk_size", DEFAULT_PARALLEL_RECOGNITION["chunk_size"])))
            pr["min_photos"] = max(0, int(pr.get("min_photos", DEFAULT_PARALLEL_RECOGNITION["min_photos"])))
            pr["enabled"] = bool(pr.get("enabled", False))
        except Exception:
            pr = dict(DEFAULT_PARALLEL_RECOGNITION)

        return pr

    def get_all_config(self) -> Dict[str, Any]:
        return dict(self.config_data)