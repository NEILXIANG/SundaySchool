"""
File system utilities.
"""
import os
from pathlib import Path
from ..config import SUPPORTED_IMAGE_EXTENSIONS


def is_ignored_fs_entry(path: Path) -> bool:
    """Return True for OS-generated metadata/hidden entries.

    Purpose: avoid treating platform junk files as real photos/folders.

    Examples:
    - macOS zip metadata: __MACOSX/, .DS_Store, Icon\r, ._AppleDouble files
    - Windows Explorer metadata: Thumbs.db, desktop.ini
    """
    name = path.name
    if not name:
        return False
    if name.startswith('.'):
        return True

    lower = name.lower()
    if lower in {"__macosx", ".ds_store", "thumbs.db", "desktop.ini"}:
        return True
    # AppleDouble sidecar files can look like images (e.g. ._IMG_0001.jpg)
    if lower.startswith("._"):
        return True
    # Finder custom icon marker in some archives
    if name == "Icon\r":
        return True

    return False


def ensure_directory_exists(directory: str | Path) -> None:
    """确保目录存在（mkdir -p 语义）。"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_file_extension(filename: str | Path) -> str:
    """获取文件扩展名（小写）。"""
    return Path(filename).suffix.lower()

def is_supported_image_file(filename: str | Path) -> bool:
    """检查是否为支持的图片格式。"""
    return get_file_extension(filename) in SUPPORTED_IMAGE_EXTENSIONS


def is_supported_nonempty_image_path(path) -> bool:
    """检查路径是否为支持的且非空的图片文件。

    说明：老师可能会误放 0 字节文件或损坏文件。
    - 0 字节文件：在处理与增量快照中视为“无效图片”，直接忽略。
    - 其他损坏文件：仍可能在后续读取时抛异常，由调用方捕获并跳过。
    """
    try:
        p = Path(path)
        if is_ignored_fs_entry(p):
            return False
        if not p.is_file():
            return False
        if p.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            return False
        return p.stat().st_size > 0
    except Exception:
        return False


class UnsafePathError(ValueError):
    """路径安全检查失败（试图逃逸出基准目录）。"""
    pass


def safe_join_under(base_dir: Path, *segments: str) -> Path:
    """安全地拼接路径，确保结果在 base_dir 之下。

    防止 Path Traversal 攻击（如 ".." 或绝对路径）。
    
    Args:
        base_dir: 基准目录（必须是绝对路径或安全的可信路径）
        *segments: 待拼接的路径片段（如学生姓名、日期等）
    
    Returns:
        Path: 拼接后的绝对路径
    
    Raises:
        UnsafePathError: 如果拼接后的路径不在 base_dir 之下
    """
    base = Path(base_dir).resolve()
    
    # 检查片段中是否包含绝对路径（Path.joinpath 会重置根目录）
    for seg in segments:
        if Path(seg).is_absolute():
            raise UnsafePathError(f"Absolute path segment not allowed: {seg}")
            
    # 拼接并解析（resolve 处理 ".." 和符号链接）
    # 注意：resolve(strict=False) 允许路径不存在
    target = base.joinpath(*segments).resolve()
    
    try:
        # 检查 target 是否以 base 开头
        target.relative_to(base)
    except ValueError:
        raise UnsafePathError(f"Path traversal attempt: {target} is outside {base}")
        
    return target


def ensure_resolved_under(base_dir: Path, target_path: Path) -> None:
    """确保 target_path resolve 后仍在 base_dir 之下。

    用途：删除/清理等“危险操作”前的防护，避免符号链接导致越界。

    Raises:
        UnsafePathError: 如果 resolve 后不在 base_dir 之下
    """
    base = Path(base_dir).resolve()
    try:
        resolved = Path(target_path).resolve(strict=False)
    except Exception as e:
        raise UnsafePathError(f"Failed to resolve path: {target_path}: {e}")

    try:
        resolved.relative_to(base)
    except ValueError:
        raise UnsafePathError(f"Resolved path escapes base_dir: {resolved} is outside {base}")
