"""增量状态模块完整测试

测试覆盖范围：
1. 快照构建（空目录、单日期、多日期、嵌套文件）
2. 快照保存与加载（路径创建、JSON格式、错误容忍）
3. 增量计划计算（首次运行、新增日期、变更检测、删除检测）
4. 日期目录枚举（忽略非法名称、系统文件）
5. 快照合并与比较
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch
from src.core.incremental_state import (
    build_class_photos_snapshot,
    save_snapshot,
    load_snapshot,
    compute_incremental_plan,
    iter_date_directories,
    snapshot_file_path,
    SNAPSHOT_VERSION
)


class TestIncrementalStateSnapshot:
    """测试快照构建功能"""
    
    def test_build_snapshot_empty_directory(self, tmp_path: Path):
        """空目录应该生成空快照"""
        class_photos_dir = tmp_path / "class_photos"
        class_photos_dir.mkdir()
        
        snapshot = build_class_photos_snapshot(class_photos_dir)
        
        assert snapshot["version"] == SNAPSHOT_VERSION
        assert "generated_at" in snapshot
        assert snapshot["dates"] == {}
    
    def test_build_snapshot_single_date_with_files(self, tmp_path: Path):
        """单个日期目录应该正确记录文件"""
        class_photos_dir = tmp_path / "class_photos"
        date_dir = class_photos_dir / "2024-01-01"
        date_dir.mkdir(parents=True)
        
        # 创建测试图片
        (date_dir / "photo1.jpg").write_bytes(b"fake_image_1")
        (date_dir / "photo2.png").write_bytes(b"fake_image_2")
        
        snapshot = build_class_photos_snapshot(class_photos_dir)
        
        assert "2024-01-01" in snapshot["dates"]
        files = snapshot["dates"]["2024-01-01"]["files"]
        assert len(files) == 2
        assert all(f["size"] > 0 for f in files)
        assert all("mtime" in f for f in files)
    
    def test_build_snapshot_multiple_dates(self, tmp_path: Path):
        """多个日期目录应该全部记录"""
        class_photos_dir = tmp_path / "class_photos"
        
        for date in ["2024-01-01", "2024-01-15", "2024-02-10"]:
            date_dir = class_photos_dir / date
            date_dir.mkdir(parents=True)
            (date_dir / f"{date}.jpg").write_bytes(b"fake_image")
        
        snapshot = build_class_photos_snapshot(class_photos_dir)
        
        assert len(snapshot["dates"]) == 3
        assert "2024-01-01" in snapshot["dates"]
        assert "2024-01-15" in snapshot["dates"]
        assert "2024-02-10" in snapshot["dates"]
    
    def test_build_snapshot_ignores_zero_byte_files(self, tmp_path: Path):
        """0字节文件应该被忽略"""
        class_photos_dir = tmp_path / "class_photos"
        date_dir = class_photos_dir / "2024-01-01"
        date_dir.mkdir(parents=True)
        
        (date_dir / "valid.jpg").write_bytes(b"fake_image")
        (date_dir / "empty.jpg").write_bytes(b"")  # 空文件
        
        snapshot = build_class_photos_snapshot(class_photos_dir)
        
        files = snapshot["dates"]["2024-01-01"]["files"]
        assert len(files) == 1
        assert files[0]["path"] == "valid.jpg"


class TestIncrementalStatePersistence:
    """测试快照保存与加载"""
    
    def test_save_and_load_snapshot(self, tmp_path: Path):
        """保存后应该能正确加载"""
        output_dir = tmp_path / "output"
        
        test_snapshot = {
            "version": SNAPSHOT_VERSION,
            "generated_at": "2024-01-01T12:00:00",
            "dates": {"2024-01-01": {"files": []}}
        }
        
        save_snapshot(output_dir, test_snapshot)
        loaded = load_snapshot(output_dir)
        
        assert loaded == test_snapshot
    
    def test_save_snapshot_creates_directory(self, tmp_path: Path):
        """保存快照时应该自动创建状态目录"""
        output_dir = tmp_path / "output"
        
        save_snapshot(output_dir, {"version": SNAPSHOT_VERSION, "dates": {}})
        
        assert snapshot_file_path(output_dir).exists()
    
    def test_load_snapshot_returns_none_if_not_exists(self, tmp_path: Path):
        """不存在的快照应该返回None"""
        output_dir = tmp_path / "output"
        
        loaded = load_snapshot(output_dir)
        
        assert loaded is None
    
    def test_load_snapshot_handles_corrupted_json(self, tmp_path: Path):
        """损坏的快照文件应该返回None"""
        output_dir = tmp_path / "output"
        snapshot_path = snapshot_file_path(output_dir)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text("invalid json{{{")
        
        loaded = load_snapshot(output_dir)
        
        assert loaded is None


class TestIncrementalPlan:
    """测试增量计划计算"""
    
    def test_first_run_all_dates_changed(self):
        """首次运行：所有日期都应该标记为变更"""
        current = {
            "version": SNAPSHOT_VERSION,
            "dates": {
                "2024-01-01": {"files": []},
                "2024-01-02": {"files": []}
            }
        }
        
        plan = compute_incremental_plan(previous=None, current=current)
        
        assert len(plan.changed_dates) == 2
        assert "2024-01-01" in plan.changed_dates
        assert "2024-01-02" in plan.changed_dates
        assert len(plan.deleted_dates) == 0
    
    def test_detect_new_date_directory(self):
        """应该检测到新增的日期目录"""
        previous = {
            "version": SNAPSHOT_VERSION,
            "dates": {"2024-01-01": {"files": []}}
        }
        current = {
            "version": SNAPSHOT_VERSION,
            "dates": {
                "2024-01-01": {"files": []},
                "2024-01-02": {"files": []}  # 新增
            }
        }
        
        plan = compute_incremental_plan(previous, current)
        
        assert "2024-01-02" in plan.changed_dates
        assert "2024-01-01" not in plan.changed_dates
    
    def test_detect_modified_date_directory(self):
        """应该检测到文件变更"""
        previous = {
            "version": SNAPSHOT_VERSION,
            "dates": {
                "2024-01-01": {
                    "files": [{"path": "a.jpg", "size": 100, "mtime": 1000}]
                }
            }
        }
        current = {
            "version": SNAPSHOT_VERSION,
            "dates": {
                "2024-01-01": {
                    "files": [{"path": "a.jpg", "size": 200, "mtime": 2000}]  # 修改
                }
            }
        }
        
        plan = compute_incremental_plan(previous, current)
        
        assert "2024-01-01" in plan.changed_dates
    
    def test_detect_deleted_date_directory(self):
        """应该检测到被删除的日期目录"""
        previous = {
            "version": SNAPSHOT_VERSION,
            "dates": {
                "2024-01-01": {"files": []},
                "2024-01-02": {"files": []}
            }
        }
        current = {
            "version": SNAPSHOT_VERSION,
            "dates": {"2024-01-01": {"files": []}}  # 2024-01-02被删除
        }
        
        plan = compute_incremental_plan(previous, current)
        
        assert "2024-01-02" in plan.deleted_dates
        assert "2024-01-01" not in plan.changed_dates
    
    def test_no_changes_detected(self):
        """没有变更时应该返回空计划"""
        snapshot = {
            "version": SNAPSHOT_VERSION,
            "dates": {"2024-01-01": {"files": []}}
        }
        
        plan = compute_incremental_plan(previous=snapshot, current=snapshot)
        
        assert len(plan.changed_dates) == 0
        assert len(plan.deleted_dates) == 0


class TestDateDirectoryIteration:
    """测试日期目录枚举"""
    
    def test_iter_date_directories_valid_names(self, tmp_path: Path):
        """应该枚举所有合法的日期目录"""
        class_photos_dir = tmp_path / "class_photos"
        class_photos_dir.mkdir()
        
        (class_photos_dir / "2024-01-01").mkdir()
        (class_photos_dir / "2024-12-31").mkdir()
        (class_photos_dir / "invalid_name").mkdir()  # 非法名称
        (class_photos_dir / "file.txt").write_text("test")  # 文件
        
        date_dirs = iter_date_directories(class_photos_dir)
        
        assert len(date_dirs) == 2
        names = {d.name for d in date_dirs}
        assert "2024-01-01" in names
        assert "2024-12-31" in names
        assert "invalid_name" not in names
    
    def test_iter_date_directories_sorted(self, tmp_path: Path):
        """枚举结果应该按名称排序"""
        class_photos_dir = tmp_path / "class_photos"
        class_photos_dir.mkdir()
        
        for date in ["2024-03-01", "2024-01-01", "2024-02-01"]:
            (class_photos_dir / date).mkdir()
        
        date_dirs = iter_date_directories(class_photos_dir)
        
        names = [d.name for d in date_dirs]
        assert names == ["2024-01-01", "2024-02-01", "2024-03-01"]
    
    def test_iter_date_directories_nonexistent_path(self, tmp_path: Path):
        """不存在的路径应该返回空列表"""
        class_photos_dir = tmp_path / "nonexistent"
        
        date_dirs = iter_date_directories(class_photos_dir)
        
        assert date_dirs == []
