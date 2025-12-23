"""兼容层（shim）：保持历史导入路径不变。

历史上有些脚本会直接从 `input_validator` 导入 `InputValidator` / `validator`。
当前权威实现位于 `ui.input_validator`。

本文件只负责 re-export，避免出现“双实现漂移”。
"""

from ui.input_validator import InputValidator, show_operation_guide, validator  # noqa: F401

__all__ = ["InputValidator", "show_operation_guide", "validator"]