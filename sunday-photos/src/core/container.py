"""
Dependency Injection Container.
"""
from pathlib import Path

class ServiceContainer:
    """
    依赖注入容器，统一管理核心服务实例。
    支持自定义mock和解耦对象创建，便于测试和扩展。
    """
    def __init__(self, config=None):
        self._services = {}
        self.config = config

    def get_student_manager(self):
        if 'student_manager' not in self._services:
            from .student_manager import StudentManager
            input_dir = self.config.get('input_dir') if self.config else None
            self._services['student_manager'] = StudentManager(input_dir)
        return self._services['student_manager']

    def get_face_recognizer(self):
        if 'face_recognizer' not in self._services:
            from .face_recognizer import FaceRecognizer
            sm = self.get_student_manager()
            tolerance = self.config.get('tolerance') if self.config else None
            min_face_size = self.config.get('min_face_size') if self.config else None
            log_dir = self.config.get('log_dir') if self.config else None
            # Prefer a single explicit interface: FaceRecognizer(..., log_dir=...).
            # Backward-compat: if a stub/older class does not accept log_dir, fall back.
            try:
                fr = FaceRecognizer(
                    sm,
                    tolerance=tolerance,
                    min_face_size=min_face_size,
                    log_dir=log_dir,
                )
            except TypeError:
                fr = FaceRecognizer(sm, tolerance, min_face_size)

                # Best-effort injection for legacy objects.
                try:
                    if log_dir and hasattr(fr, "_resolve_ref_cache_dir") and hasattr(fr, "_resolve_ref_snapshot_path"):
                        setattr(fr, "_log_dir", Path(str(log_dir)))
                        setattr(fr, "_ref_cache_dir", fr._resolve_ref_cache_dir())
                        setattr(fr, "_ref_snapshot_path", fr._resolve_ref_snapshot_path())
                except Exception:
                    pass

            self._services['face_recognizer'] = fr
        return self._services['face_recognizer']

    def get_file_organizer(self):
        if 'file_organizer' not in self._services:
            from .file_organizer import FileOrganizer
            output_dir = self.config.get('output_dir') if self.config else None
            self._services['file_organizer'] = FileOrganizer(output_dir)
        return self._services['file_organizer']
