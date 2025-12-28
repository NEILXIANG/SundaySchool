"""兼容层（shim）：保持历史导入路径不变。

历史上部分脚本会从 `incremental_state` 导入增量快照相关函数。
当前权威实现位于 `core.incremental_state`。
"""

from core.incremental_state import (  # noqa: F401
    IncrementalPlan,
    build_class_photos_snapshot,
    compute_incremental_plan,
    iter_date_directories,
    load_snapshot,
    save_snapshot,
    snapshot_file_path,
)
