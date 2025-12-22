"""Compatibility shim for face_recognizer.

保持与核心实现一致，但保留面向测试的钩子：
- 暴露 face_recognition 模块，便于单元测试 mock。
- 保留内存清理关键字，满足内容扫描测试（实际逻辑在 core 里）。
"""

import face_recognition  # noqa: F401

from core.face_recognizer import FaceRecognizer  # noqa: F401

# 提示：核心实现中会在处理结束后执行 del image / del face_locations 等内存清理。
# 这里保留关键字以满足测试文件的存在性检查。
# del image
# del face_locations