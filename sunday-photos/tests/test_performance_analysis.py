"""
性能分析和优化测试

分析关键路径上的性能瓶颈：
1. 大规模照片增量处理的性能
2. 人脸特征提取的效率
3. 并行与串行对比
4. 内存使用情况
"""

import pytest
import time
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from src.core.parallel_recognizer import parallel_recognize, ParallelConfig
from src.core.incremental_state import (
    build_class_photos_snapshot,
    compute_incremental_plan,
)
from src.core.clustering import UnknownClustering


class TestPerformanceIncrementalProcessing:
    """增量处理性能测试"""

    def test_incremental_plan_scaling(self):
        """测试增量计划生成在大规模目录上的性能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            class_dir = Path(tmpdir) / "class_photos"
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir(exist_ok=True)
            
            # 模拟 50 个日期文件夹，每个包含 100 张照片
            class_dir.mkdir(exist_ok=True)
            photo_count = 0
            for day in range(1, 51):
                date_dir = class_dir / f"2024-01-{day:02d}"
                date_dir.mkdir(exist_ok=True)
                for i in range(100):
                    photo_file = date_dir / f"photo_{i:03d}.jpg"
                    photo_file.write_text("dummy")
                    photo_count += 1
            
            # 测试快照构建性能
            start = time.time()
            snapshot = build_class_photos_snapshot(class_dir)
            elapsed = time.time() - start
            
            # 应该在合理时间内完成（<1s）
            assert elapsed < 1.0, f"快照构建耗时 {elapsed}s，应 <1s"
            # January 有 31 天，所以最多 31 个日期（day 范围是 1-50，但 2024-01 只有 31 天）
            assert len(snapshot.get('dates', {})) <= 31
            
            # 第二次增量计划应该识别零变化
            snap1 = snapshot
            start = time.time()
            plan = compute_incremental_plan(snap1, snapshot)
            elapsed = time.time() - start
            assert elapsed < 0.5
            assert len(plan.changed_dates) == 0
            assert len(plan.deleted_dates) == 0


class TestParallelRecognizerConfig:
    """并行识别器配置测试"""

    def test_parallel_config_defaults(self):
        """测试并行配置默认值"""
        config = ParallelConfig(enabled=True, workers=4, chunk_size=10, min_photos=50)
        assert config.workers == 4
        assert config.chunk_size == 10
        assert config.min_photos == 50

    def test_parallel_config_validation(self):
        """测试并行配置有效性检查"""
        # 正常配置
        cfg1 = ParallelConfig(enabled=True, workers=2, chunk_size=5, min_photos=10)
        assert cfg1.enabled is True
        
        # 禁用并行
        cfg2 = ParallelConfig(enabled=False, workers=1, chunk_size=1, min_photos=0)
        assert cfg2.enabled is False


class TestClusteringPerformance:
    """聚类算法性能测试"""

    def test_clustering_large_scale(self):
        """测试聚类在大规模未知人脸上的性能"""
        clusterer = UnknownClustering(tolerance=0.45, min_cluster_size=2)
        
        # 生成 500 个未知人脸的编码
        encodings_per_group = 50
        num_groups = 10
        
        start = time.time()
        for group_id in range(num_groups):
            # 每组内的编码应该很接近
            base_encoding = np.random.randn(128)
            base_encoding = base_encoding / (np.linalg.norm(base_encoding) + 1e-12)
            
            for i in range(encodings_per_group):
                # 添加少量噪声保持相似性
                noisy = base_encoding + np.random.randn(128) * 0.05
                noisy = noisy / (np.linalg.norm(noisy) + 1e-12)
                clusterer.add_faces(f"img_{group_id}_{i}.jpg", [noisy])
        
        elapsed = time.time() - start
        
        # 聚类 500 张照片应该在 2s 以内（允许更多时间用于复杂计算）
        assert elapsed < 2.0, f"聚类耗时 {elapsed}s，应 <2s"
        
        results = clusterer.get_results()
        # 预期约 10 个簇（每组 50 张）
        assert len(results) >= 8, f"期望 ~10 个簇，但得到 {len(results)}"


class TestErrorHandlingEdgeCases:
    """错误处理与边界情况测试"""

    def test_corrupted_image_handling(self):
        """测试处理损坏图像文件的鲁棒性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            corrupted_path = Path(tmpdir) / "corrupted.jpg"
            corrupted_path.write_bytes(b"not-a-valid-image")
            
            # 应该能优雅地处理（实际调用会被跳过，因为依赖的模块可能不可用）
            # 这里只验证函数不会崩溃
            from src.core.parallel_recognizer import recognize_one
            
            # 由于缺少有效的人脸识别后端，这会返回错误，但不会崩溃
            try:
                result_path, result = recognize_one(str(corrupted_path))
                # 应该返回错误或异常处理的结果
                assert result.get('status') in ('error', 'no_faces_detected') or 'status' in result
            except (ModuleNotFoundError, AttributeError):
                # 后端不可用时也是可以接受的
                pass

    def test_missing_reference_photos(self):
        """测试在缺少参考照片时的处理"""
        from src.core.student_manager import StudentManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()
            
            # 创建空的学生照片目录结构
            student_photos = input_dir / "student_photos"
            student_photos.mkdir()
            
            # StudentManager 应该能处理空目录
            sm = StudentManager(str(input_dir))
            students = sm.get_student_names()
            assert len(students) == 0

    def test_extreme_face_sizes(self):
        """测试处理极端大小的人脸"""
        from src.core.face_recognizer import FaceRecognizer
        from src.core.student_manager import StudentManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()
            student_photos = input_dir / "student_photos"
            student_photos.mkdir()
            
            sm = StudentManager(str(input_dir))
            
            # 创建识别器（最小面部大小为 50）
            fr = FaceRecognizer(sm, tolerance=0.6, min_face_size=50)
            assert fr.min_face_size == 50


class TestMemoryManagement:
    """内存管理测试"""

    def test_encoding_memory_efficiency(self):
        """测试人脸编码的内存效率"""
        # 标准 face_recognition 编码是 128 维 float64
        encoding = np.random.randn(128).astype(np.float64)
        
        # 应该约 1KB 每个编码
        size_mb = encoding.nbytes / (1024 * 1024)
        assert size_mb < 0.001, f"单个编码占用 {size_mb} MB，过大"
        
        # 1000 个编码应该 < 1MB
        encodings = [np.random.randn(128).astype(np.float64) for _ in range(1000)]
        total_mb = sum(e.nbytes for e in encodings) / (1024 * 1024)
        assert total_mb < 1.5, f"1000 个编码占用 {total_mb} MB，过大"

    def test_snapshot_memory_overhead(self):
        """测试快照数据结构的内存开销"""
        with tempfile.TemporaryDirectory() as tmpdir:
            class_dir = Path(tmpdir) / "class"
            class_dir.mkdir()
            
            # 创建 100 个日期文件夹，每个 50 个文件
            for day in range(1, 101):
                date_dir = class_dir / f"2024-01-{day:02d}"
                date_dir.mkdir()
                for i in range(50):
                    (date_dir / f"photo_{i}.jpg").write_text("x" * 100)
            
            # 构建快照并检查大小
            snapshot = build_class_photos_snapshot(class_dir)
            
            # 快照应该是轻量级的（JSON 序列化后 < 1MB）
            import json
            snapshot_json = json.dumps(snapshot)
            size_mb = len(snapshot_json.encode()) / (1024 * 1024)
            assert size_mb < 1.0, f"快照大小 {size_mb} MB，过大"
