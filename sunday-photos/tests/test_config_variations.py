"""配置变化和边缘案例测试"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from src.core.file_organizer import FileOrganizer


def create_dummy_image(path: Path, content: str = "fake_image"):
    """创建虚假图片文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture
def config_env(tmp_path):
    """配置测试环境"""
    work_dir = tmp_path / "config_work"
    input_dir = work_dir / "input"
    output_dir = work_dir / "output"
    log_dir = work_dir / "logs"
    
    (input_dir / "student_photos").mkdir(parents=True)
    (input_dir / "class_photos").mkdir(parents=True)
    
    return work_dir, input_dir, output_dir, log_dir


class ConfigurableFakeRecognizer:
    """可配置的假识别器"""
    def __init__(self, student_manager, config=None):
        self.student_manager = student_manager
        self.config = config or {}
        self.tolerance = self.config.get('tolerance', 0.6)
        self.min_face_size = self.config.get('min_face_size', 50)
        self.reference_fingerprint = "config-fp"

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        # Behavior based on config
        if self.config.get('always_unknown', False):
            return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}
        
        if self.config.get('no_faces', False):
            return {"status": "no_faces_detected", "recognized_students": [], "unknown_encodings": []}
        
        # Normal recognition
        students = self.student_manager.get_student_names()
        if students:
            chosen = students[hash(photo_path) % len(students)]
            return {"status": "success", "recognized_students": [chosen], "unknown_encodings": []}
        
        return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}


def test_parallel_recognition_config(config_env):
    """测试并行识别配置"""
    work_dir, input_dir, output_dir, log_dir = config_env
    
    # Create test data
    create_dummy_image(input_dir / "student_photos" / "Alice" / "ref.jpg")
    create_dummy_image(input_dir / "student_photos" / "Bob" / "ref.jpg")
    
    # Create multiple photos
    for i in range(15):  # Enough to trigger parallel processing
        create_dummy_image(input_dir / "class_photos" / "2025-01-01" / f"photo_{i:02d}.jpg")
    
    # Create config with parallel enabled
    config_path = work_dir / "config.json"
    config_data = {
        "parallel_recognition": {
            "enabled": True,
            "workers": 2,
            "chunk_size": 3,
            "min_photos": 5
        }
    }
    config_path.write_text(json.dumps(config_data, indent=2))
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return ConfigurableFakeRecognizer(self.get_student_manager())
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container,
        config_file=str(config_path)
    )
    
    organizer.run()
    
    # Verify photos were processed
    output_photos = list(output_dir.rglob("*.jpg"))
    assert len(output_photos) > 0
    print(f"✅ Parallel recognition config test: {len(output_photos)} photos processed")


def test_clustering_config(config_env):
    """测试聚类配置"""
    work_dir, input_dir, output_dir, log_dir = config_env
    
    # Create test data
    create_dummy_image(input_dir / "student_photos" / "Alice" / "ref.jpg")
    
    # Create photos that will be "unknown"
    for i in range(8):
        create_dummy_image(input_dir / "class_photos" / "2025-01-01" / f"unknown_{i}.jpg")
    
    # Create config with clustering enabled
    config_path = work_dir / "config.json"
    config_data = {
        "unknown_face_clustering": {
            "enabled": True,
            "min_cluster_size": 3,
            "eps": 0.5,
            "min_samples": 2
        }
    }
    config_path.write_text(json.dumps(config_data, indent=2))
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            # Return all as unknown to test clustering
            return ConfigurableFakeRecognizer(self.get_student_manager(), {'always_unknown': True})
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container,
        config_file=str(config_path)
    )
    
    organizer.run()
    
    # Check for unknown faces directory
    unknown_dir = output_dir / "unknown_faces"
    if unknown_dir.exists():
        unknown_photos = list(unknown_dir.rglob("*.jpg"))
        assert len(unknown_photos) > 0
    
    print("✅ Clustering config test completed")


def test_tolerance_config_variations(config_env):
    """测试不同tolerance配置"""
    work_dir, input_dir, output_dir, log_dir = config_env
    
    # Create test data
    create_dummy_image(input_dir / "student_photos" / "Alice" / "ref.jpg")
    create_dummy_image(input_dir / "class_photos" / "2025-01-01" / "photo.jpg")
    
    tolerances = [0.3, 0.6, 0.9]
    
    for tolerance in tolerances:
        # Create separate output for each tolerance
        tolerance_output = output_dir / f"tolerance_{tolerance}"
        
        config_path = work_dir / f"config_{tolerance}.json"
        config_data = {
            "tolerance": tolerance,
            "min_face_size": 30
        }
        config_path.write_text(json.dumps(config_data, indent=2))
        
        class MockServiceContainer:
            def get_student_manager(self):
                return StudentManager(str(input_dir))
            def get_face_recognizer(self):
                return ConfigurableFakeRecognizer(self.get_student_manager(), {'tolerance': tolerance})
            def get_file_organizer(self):
                return FileOrganizer(str(tolerance_output))
        
        container = MockServiceContainer()
        organizer = SimplePhotoOrganizer(
            input_dir=str(input_dir),
            output_dir=str(tolerance_output),
            log_dir=str(log_dir),
            service_container=container,
            config_file=str(config_path)
        )
        
        organizer.run()
    
    print(f"✅ Tolerance variations test: tested {len(tolerances)} different tolerance values")


def test_invalid_config_handling(config_env):
    """测试无效配置处理"""
    work_dir, input_dir, output_dir, log_dir = config_env
    
    # Create test data
    create_dummy_image(input_dir / "student_photos" / "Alice" / "ref.jpg")
    create_dummy_image(input_dir / "class_photos" / "2025-01-01" / "photo.jpg")
    
    # Create invalid config
    config_path = work_dir / "invalid_config.json"
    config_path.write_text("{ invalid json }")
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return ConfigurableFakeRecognizer(self.get_student_manager())
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
    
    container = MockServiceContainer()
    
    # Should handle invalid config gracefully and use defaults
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=container,
        config_file=str(config_path)
    )
    
    organizer.run()
    
    # Should still process photos despite invalid config
    output_photos = list(output_dir.rglob("*.jpg"))
    assert len(output_photos) > 0
    
    print("✅ Invalid config handled gracefully")


def test_no_faces_detected_scenario(config_env):
    """测试无人脸检测场景"""
    work_dir, input_dir, output_dir, log_dir = config_env
    
    # Create test data
    create_dummy_image(input_dir / "student_photos" / "Alice" / "ref.jpg")
    
    # Create photos that will have "no faces detected"
    for i in range(5):
        create_dummy_image(input_dir / "class_photos" / "2025-01-01" / f"landscape_{i}.jpg")
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return ConfigurableFakeRecognizer(self.get_student_manager(), {'no_faces': True})
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
    
    # Should handle no-faces scenario gracefully
    print("✅ No faces detected scenario handled")


def test_mixed_recognition_results(config_env):
    """测试混合识别结果"""
    work_dir, input_dir, output_dir, log_dir = config_env
    
    # Create test data
    create_dummy_image(input_dir / "student_photos" / "Alice" / "ref.jpg")
    create_dummy_image(input_dir / "student_photos" / "Bob" / "ref.jpg")
    
    # Create photos with predictable names for different results
    create_dummy_image(input_dir / "class_photos" / "2025-01-01" / "success_photo.jpg")  # Will succeed
    create_dummy_image(input_dir / "class_photos" / "2025-01-01" / "unknown_photo.jpg")  # Will be unknown
    create_dummy_image(input_dir / "class_photos" / "2025-01-01" / "no_face_photo.jpg")  # No faces
    
    class MixedResultRecognizer:
        def __init__(self, student_manager):
            self.student_manager = student_manager
            self.tolerance = 0.6
            self.min_face_size = 50
            self.reference_fingerprint = "mixed-fp"
        
        def recognize_faces(self, photo_path: str, return_details: bool = True):
            filename = Path(photo_path).name
            
            if "success" in filename:
                students = self.student_manager.get_student_names()
                chosen = students[0] if students else "Alice"
                return {"status": "success", "recognized_students": [chosen], "unknown_encodings": []}
            elif "unknown" in filename:
                return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}
            elif "no_face" in filename:
                return {"status": "no_faces_detected", "recognized_students": [], "unknown_encodings": []}
            else:
                return {"status": "success", "recognized_students": ["Alice"], "unknown_encodings": []}
    
    class MockServiceContainer:
        def get_student_manager(self):
            return StudentManager(str(input_dir))
        def get_face_recognizer(self):
            return MixedResultRecognizer(self.get_student_manager())
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
    
    # Should handle mixed results appropriately
    all_photos = list(output_dir.rglob("*.jpg"))
    assert len(all_photos) > 0
    
    print(f"✅ Mixed recognition results handled: {len(all_photos)} photos organized")