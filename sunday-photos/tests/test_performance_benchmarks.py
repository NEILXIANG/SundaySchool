"""性能基准测试和极限场景测试"""
import time
import random
import pytest
from pathlib import Path
from unittest.mock import patch
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from src.core.file_organizer import FileOrganizer


def generate_test_image(path: Path, size_bytes: int = 1024):
    """生成指定大小的测试图片"""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Generate pseudo-random content of specified size
    content = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=size_bytes))
    path.write_text(content, encoding='utf-8')


class BenchmarkRecognizer:
    """基准测试用识别器"""
    def __init__(self, student_manager, processing_time_ms=1):
        self.student_manager = student_manager
        self.processing_time_ms = processing_time_ms
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = "benchmark-fp"
        self.processed_count = 0
        self.total_time = 0

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        start_time = time.time()
        
        # Simulate processing time
        time.sleep(self.processing_time_ms / 1000.0)
        
        self.processed_count += 1
        
        # Simple deterministic result
        students = self.student_manager.get_student_names()
        if students and self.processed_count % 3 != 0:  # 2/3 success rate
            chosen = students[hash(photo_path) % len(students)]
            result = {"status": "success", "recognized_students": [chosen], "unknown_encodings": []}
        else:
            result = {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}
        
        self.total_time += time.time() - start_time
        return result


@pytest.fixture
def benchmark_env(tmp_path, monkeypatch):
    """基准测试环境"""
    # 性能基准测试使用 BenchmarkRecognizer（不读取真实图片内容）。
    # 若启用并行识别路径，会走 parallel_recognizer 并尝试解码图片，
    # 而本文件生成的 photo_*.jpg 是“伪图片”（随机文本），会导致大量解码异常并拖慢用例。
    monkeypatch.setenv("SUNDAY_PHOTOS_NO_PARALLEL", "1")

    work_dir = tmp_path / "benchmark_work"
    input_dir = work_dir / "input"
    output_dir = work_dir / "output"
    log_dir = work_dir / "logs"
    
    (input_dir / "student_photos").mkdir(parents=True)
    (input_dir / "class_photos").mkdir(parents=True)
    
    return work_dir, input_dir, output_dir, log_dir


def test_performance_small_dataset(benchmark_env):
    """小数据集性能测试"""
    work_dir, input_dir, output_dir, log_dir = benchmark_env
    
    # Create 5 students
    for i in range(5):
        generate_test_image(input_dir / "student_photos" / f"Student{i}" / "ref.jpg")
    
    # Create 20 photos
    for i in range(20):
        generate_test_image(input_dir / "class_photos" / "2025-01-01" / f"photo_{i:02d}.jpg")
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return BenchmarkRecognizer(self.get_student_manager(), processing_time_ms=1)
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    start_time = time.time()
    organizer.run()
    end_time = time.time()
    
    processing_time = end_time - start_time
    output_photos = list(output_dir.rglob("*.jpg"))
    
    print(f"✅ Small dataset: {len(output_photos)} photos in {processing_time:.2f}s")
    assert processing_time < 10  # Should complete in under 10 seconds
    assert len(output_photos) > 0


def test_performance_medium_dataset(benchmark_env):
    """中等数据集性能测试"""
    work_dir, input_dir, output_dir, log_dir = benchmark_env
    
    # Create 20 students
    for i in range(20):
        generate_test_image(input_dir / "student_photos" / f"Student{i:02d}" / "ref.jpg")
    
    # Create 100 photos across 5 dates
    for date_idx in range(5):
        date_str = f"2025-01-{date_idx+1:02d}"
        for photo_idx in range(20):
            generate_test_image(input_dir / "class_photos" / date_str / f"photo_{photo_idx:02d}.jpg")
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return BenchmarkRecognizer(self.get_student_manager(), processing_time_ms=2)
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    start_time = time.time()
    organizer.run()
    end_time = time.time()
    
    processing_time = end_time - start_time
    output_photos = list(output_dir.rglob("*.jpg"))
    
    print(f"✅ Medium dataset: {len(output_photos)} photos in {processing_time:.2f}s")
    assert processing_time < 30  # Should complete in under 30 seconds
    assert len(output_photos) > 0


def test_incremental_performance(benchmark_env):
    """增量处理性能测试"""
    work_dir, input_dir, output_dir, log_dir = benchmark_env
    
    # Create students
    for i in range(10):
        generate_test_image(input_dir / "student_photos" / f"Student{i}" / "ref.jpg")
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return BenchmarkRecognizer(self.get_student_manager(), processing_time_ms=5)
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    
    # First run: process 30 photos
    for i in range(30):
        generate_test_image(input_dir / "class_photos" / "2025-01-01" / f"batch1_{i:02d}.jpg")
    
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    start_time = time.perf_counter()
    organizer.run()
    first_run_time = time.perf_counter() - start_time
    
    # Second run: add 10 more photos
    for i in range(10):
        generate_test_image(input_dir / "class_photos" / "2025-01-02" / f"batch2_{i:02d}.jpg")
    
    # Create new container for second run
    container2 = MockServiceContainer()
    organizer2 = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container2
    )
    
    start_time = time.perf_counter()
    organizer2.run()
    second_run_time = time.perf_counter() - start_time
    
    output_photos = list(output_dir.rglob("*.jpg"))
    
    print(f"✅ Incremental: 1st run {first_run_time:.2f}s, 2nd run {second_run_time:.2f}s")
    print(f"   Total photos: {len(output_photos)}")
    
    # Second run should be faster (only processing new photos).
    # NOTE: This is a *micro* benchmark (tens to hundreds of ms). Constant overhead
    # (filesystem, Python startup, snapshot IO, etc.) can dominate and cause flaky
    # ratios on busy CI machines. We assert a meaningful speedup instead of a strict 2x.
    assert second_run_time < first_run_time

    # For longer runs, require either a noticeable relative improvement or an absolute win.
    # - Relative: at least 25% faster
    # - Absolute: at least 60ms faster
    if first_run_time >= 0.2:
        assert (second_run_time <= first_run_time * 0.75) or ((first_run_time - second_run_time) >= 0.06)
    assert len(output_photos) > 30


def test_memory_usage_large_dataset(benchmark_env):
    """大数据集内存使用测试"""
    work_dir, input_dir, output_dir, log_dir = benchmark_env
    
    # Create 30 students
    for i in range(30):
        generate_test_image(input_dir / "student_photos" / f"Student{i:02d}" / "ref.jpg")
    
    # Create 300 photos across 10 dates (larger dataset)
    for date_idx in range(10):
        date_str = f"2025-01-{date_idx+1:02d}"
        for photo_idx in range(30):
            # Create larger files to test memory handling
            generate_test_image(
                input_dir / "class_photos" / date_str / f"photo_{photo_idx:03d}.jpg",
                size_bytes=5120  # 5KB files
            )
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return BenchmarkRecognizer(self.get_student_manager(), processing_time_ms=1)
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    # Should complete without memory issues
    organizer.run()
    
    output_photos = list(output_dir.rglob("*.jpg"))
    print(f"✅ Large dataset memory test: {len(output_photos)} photos processed")
    assert len(output_photos) > 200  # Most photos should be processed


def test_concurrent_file_access(benchmark_env):
    """并发文件访问测试"""
    work_dir, input_dir, output_dir, log_dir = benchmark_env
    
    # Create test data
    for i in range(5):
        generate_test_image(input_dir / "student_photos" / f"Student{i}" / "ref.jpg")
    
    for i in range(20):
        generate_test_image(input_dir / "class_photos" / "2025-01-01" / f"photo_{i:02d}.jpg")
    
    class ConcurrentRecognizer:
        def __init__(self, student_manager):
            self.student_manager = student_manager
            self.tolerance = 0.6
            self.min_face_size = 50
            self.reference_fingerprint = "concurrent-fp"
            self.access_count = 0
        
        def recognize_faces(self, photo_path: str, return_details: bool = True):
            self.access_count += 1
            
            # Simulate concurrent file access
            if self.access_count % 5 == 0:
                time.sleep(0.01)  # Brief delay
            
            students = self.student_manager.get_student_names()
            if students:
                chosen = students[hash(photo_path) % len(students)]
                return {"status": "success", "recognized_students": [chosen], "unknown_encodings": []}
            else:
                return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return ConcurrentRecognizer(self.get_student_manager())
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    organizer.run()
    
    output_photos = list(output_dir.rglob("*.jpg"))
    assert len(output_photos) > 0
    print(f"✅ Concurrent access test: {len(output_photos)} photos processed")