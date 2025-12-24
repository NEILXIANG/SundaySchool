import pytest
from pathlib import Path
from src.core.utils import safe_join_under, UnsafePathError
from src.core.file_organizer import FileOrganizer

class TestSecurityPathSafety:
    """测试路径安全机制，防止 Path Traversal 攻击。"""

    def test_safe_join_under_valid(self, tmp_path):
        """测试合法的路径拼接。"""
        base = tmp_path / "output"
        base.mkdir()
        
        # 正常拼接
        result = safe_join_under(base, "Alice", "2025-12-23")
        expected = base / "Alice" / "2025-12-23"
        assert result == expected

    def test_safe_join_under_traversal_dots(self, tmp_path):
        """测试包含 '..' 的路径逃逸尝试。"""
        base = tmp_path / "output"
        base.mkdir()
        
        # 尝试逃逸到 output 的上级
        with pytest.raises(UnsafePathError):
            safe_join_under(base, "..", "System")
            
        with pytest.raises(UnsafePathError):
            safe_join_under(base, "Alice", "../../etc")

    def test_safe_join_under_absolute_path(self, tmp_path):
        """测试包含绝对路径的注入尝试。"""
        base = tmp_path / "output"
        base.mkdir()
        
        # 尝试注入绝对路径
        with pytest.raises(UnsafePathError):
            safe_join_under(base, "/etc/passwd")

    def test_file_organizer_prevents_escape(self, tmp_path):
        """集成测试：FileOrganizer 应拒绝恶意学生名。"""
        output_dir = tmp_path / "output"
        organizer = FileOrganizer(output_dir=output_dir)
        
        # 模拟恶意识别结果
        malicious_student = "../../Hacker"
        recognition_results = {
            str(tmp_path / "photo.jpg"): [malicious_student]
        }
        
        # 构造一个假的 photo.jpg
        (tmp_path / "photo.jpg").touch()
        
        stats = organizer.organize_photos(
            input_dir=tmp_path,
            recognition_results=recognition_results,
            unknown_photos=[],
            unknown_clusters={}
        )
        
        # 预期：处理失败，且未在 output 之外创建文件
        assert stats['failed'] == 1
        assert stats['copied'] == 0
        assert not (tmp_path / "Hacker").exists()

    def test_file_organizer_prevents_cluster_escape(self, tmp_path):
        """集成测试：FileOrganizer 应拒绝恶意聚类名。"""
        output_dir = tmp_path / "output"
        organizer = FileOrganizer(output_dir=output_dir)
        
        # 模拟恶意聚类
        malicious_cluster = "../../EvilCluster"
        unknown_clusters = {
            malicious_cluster: [str(tmp_path / "unknown.jpg")]
        }
        
        # 构造假的 unknown.jpg
        (tmp_path / "unknown.jpg").touch()
        
        stats = organizer.organize_photos(
            input_dir=tmp_path,
            recognition_results={},
            unknown_photos=[str(tmp_path / "unknown.jpg")],
            unknown_clusters=unknown_clusters
        )
        
        # 预期：处理失败
        assert stats['failed'] == 1
        assert not (tmp_path / "EvilCluster").exists()
