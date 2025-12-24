"""压力测试和边缘场景测试"""
import pytest
import time
from pathlib import Path
from unittest.mock import patch
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from src.core.file_organizer import FileOrganizer


class StressFaceRecognizer:
    """压力测试用的识别器"""
    def __init__(self, student_manager, failure_rate=0.1, slow_mode=False):
        self.student_manager = student_manager
        self.failure_rate = failure_rate
        self.slow_mode = slow_mode
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = "stress-fp"
        self.call_count = 0

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        self.call_count += 1
        
        if self.slow_mode:
            time.sleep(0.01)  # Simulate slow recognition
            
        # Simulate failures based on failure rate
        if self.call_count % int(1 / self.failure_rate) == 0:
            # Don't raise exception, return error status instead
            return {"status": "error", "recognized_students": [], "unknown_encodings": [], "error": f"Simulated failure for {photo_path}"}
            
        # Simple deterministic result
        students = self.student_manager.get_student_names()
        if students:
            chosen = students[hash(photo_path) % len(students)]
            return {"status": "success", "recognized_students": [chosen], "unknown_encodings": []}
        else:
            return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}


def create_test_photo(path: Path, size_kb: int = 1):
    """创建指定大小的测试图片"""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "x" * (size_kb * 1024)  # Create content of specified size
    path.write_text(content)


@pytest.fixture
def stress_env(tmp_path):
    """压力测试环境"""
    work_dir = tmp_path / "stress_work"
    input_dir = work_dir / "input"
    output_dir = work_dir / "output"
    log_dir = work_dir / "logs"
    
    # Create structure
    (input_dir / "student_photos").mkdir(parents=True)
    (input_dir / "class_photos").mkdir(parents=True)
    
    return work_dir, input_dir, output_dir, log_dir


def test_large_dataset_processing(stress_env):
    """测试大数据集处理"""
    work_dir, input_dir, output_dir, log_dir = stress_env
    
    # Create many students (50)
    for i in range(50):
        student_name = f"Student_{i:02d}"
        create_test_photo(input_dir / "student_photos" / student_name / "ref.jpg")
    
    # Create many photos across multiple dates (200 photos)
    for date_idx in range(10):  # 10 dates
        date_str = f"2025-01-{date_idx+1:02d}"
        for photo_idx in range(20):  # 20 photos per date
            create_test_photo(input_dir / "class_photos" / date_str / f"photo_{photo_idx:03d}.jpg")
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return StressFaceRecognizer(self.get_student_manager())
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    # Should complete without crashing
    organizer.run()
    
    # Verify some photos were processed
    output_photos = list(output_dir.rglob("*.jpg"))
    assert len(output_photos) > 0
    print(f"✅ Processed large dataset: {len(output_photos)} photos organized")


def test_error_resilience(stress_env):
    """测试错误恢复能力"""
    work_dir, input_dir, output_dir, log_dir = stress_env
    
    # Create test data
    create_test_photo(input_dir / "student_photos" / "Alice" / "ref.jpg")
    create_test_photo(input_dir / "student_photos" / "Bob" / "ref.jpg")
    
    # Create photos that will trigger failures
    for i in range(10):
        create_test_photo(input_dir / "class_photos" / "2025-01-01" / f"photo_{i}.jpg")
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            # 30% failure rate
            return StressFaceRecognizer(self.get_student_manager(), failure_rate=0.3)
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    # Should complete despite recognition failures
    organizer.run()
    
    # Some photos should still be processed successfully
    output_photos = list(output_dir.rglob("*.jpg"))
    assert len(output_photos) > 0
    print(f"✅ Error resilience test: {len(output_photos)} photos processed despite failures")


def test_empty_directories_handling(stress_env):
    """测试空目录处理"""
    work_dir, input_dir, output_dir, log_dir = stress_env
    
    # Create empty student and class directories
    (input_dir / "student_photos").mkdir(parents=True, exist_ok=True)
    (input_dir / "class_photos").mkdir(parents=True, exist_ok=True)
    
    # Create some empty date directories
    (input_dir / "class_photos" / "2025-01-01").mkdir()
    (input_dir / "class_photos" / "2025-01-02").mkdir()
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return StressFaceRecognizer(self.get_student_manager())
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container
    )
    
    # Should complete without errors
    organizer.run()
    
    # Should handle empty directories gracefully
    print("✅ Empty directories handled gracefully")


def test_mixed_file_sizes(stress_env):
    """测试混合文件大小处理"""
    work_dir, input_dir, output_dir, log_dir = stress_env
    
    # Create students
    create_test_photo(input_dir / "student_photos" / "Alice" / "ref.jpg")
    
    # Create photos of various sizes
    sizes = [0, 1, 10, 100, 1000]  # 0KB to 1MB
    for i, size_kb in enumerate(sizes):
        if size_kb == 0:
            # Create empty file
            path = input_dir / "class_photos" / "2025-01-01" / f"empty_{i}.jpg"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        else:
            create_test_photo(input_dir / "class_photos" / "2025-01-01" / f"photo_{i}.jpg", size_kb)
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return StressFaceRecognizer(self.get_student_manager())
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
    
    # Non-empty files should be processed (empty files are typically ignored)
    output_photos = list(output_dir.rglob("*.jpg"))
    assert len(output_photos) >= len(sizes) - 1  # Exclude empty file
    print(f"✅ Mixed file sizes handled: {len(output_photos)} files processed")


def test_unicode_filenames(stress_env):
    """测试Unicode文件名处理"""
    work_dir, input_dir, output_dir, log_dir = stress_env
    
    # Create students with unicode names
    unicode_names = ["张三", "李四", "王五", "赵六"]
    for name in unicode_names:
        create_test_photo(input_dir / "student_photos" / name / "参考照.jpg")
    
    # Create class photos with unicode names
    unicode_photos = ["合影照片.jpg", "课堂活动.jpg", "集体照.jpg"]
    for photo_name in unicode_photos:
        create_test_photo(input_dir / "class_photos" / "2025-01-01" / photo_name)
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return StressFaceRecognizer(self.get_student_manager())
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
    
    # Should handle unicode filenames correctly
    output_photos = list(output_dir.rglob("*.jpg"))
    assert len(output_photos) > 0
    
    # Check that unicode student directories were created
    student_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name in unicode_names]
    assert len(student_dirs) > 0
    
    print(f"✅ Unicode filenames handled: {len(student_dirs)} student dirs, {len(output_photos)} photos")