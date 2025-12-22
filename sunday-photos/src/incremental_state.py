"""Compatibility shim for incremental_state."""

from core.incremental_state import (  # noqa: F401
    IncrementalPlan,
    build_class_photos_snapshot,
    compute_incremental_plan,
    iter_date_directories,
    load_snapshot,
    save_snapshot,
    snapshot_file_path,
)
