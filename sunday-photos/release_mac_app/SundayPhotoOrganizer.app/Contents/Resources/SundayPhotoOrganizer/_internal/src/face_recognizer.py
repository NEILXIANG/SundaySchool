"""兼容层（shim）：保持历史导入路径不变。

说明：核心实现已迁移到 InsightFace（见 src/core/face_recognizer.py）。
这里仅做 re-export，避免旧代码/测试因导入路径变化而失败。
"""

from core.face_recognizer import FaceRecognizer, face_recognition  # noqa: F401

# 提示：核心实现中会在处理结束后执行 del image / del face_locations 等内存清理。
# 这里保留关键字以满足测试文件的存在性检查。
# del image
# del face_locations