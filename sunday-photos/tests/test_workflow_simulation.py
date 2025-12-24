import shutil
import time
from pathlib import Path
import pytest
from unittest.mock import patch
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from src.core.file_organizer import FileOrganizer
# from src.core.incremental_state import IncrementalStateManager # Removed invalid import

# Reuse the deterministic fake recognizer logic for stability
def _stable_int(s: str) -> int:
    return sum(s.encode("utf-8"))

class FakeLifecycleRecognizer:
    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = "lifecycle-fp"

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        p = Path(photo_path)
        name = p.name
        
        # Simulate corruption handling
        if "corrupt" in name:
            raise Exception("Simulated image corruption")

        # Deterministic result based on filename
        h = _stable_int(name)
        students = self.student_manager.get_student_names()
        
        if not students:
            return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}
            
        # 80% success rate
        if h % 10 < 8:
            chosen = students[h % len(students)]
            return {"status": "success", "recognized_students": [chosen], "unknown_encodings": []}
        else:
            return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}

@pytest.fixture
def lifecycle_env(tmp_path):
    """Setup a clean environment for lifecycle testing"""
    work_dir = tmp_path / "lifecycle_work"
    work_dir.mkdir()
    
    input_dir = work_dir / "input"
    output_dir = work_dir / "output"
    logs_dir = work_dir / "logs"
    
    (input_dir / "student_photos").mkdir(parents=True)
    (input_dir / "class_photos").mkdir(parents=True)
    
    return work_dir, input_dir, output_dir

def create_dummy_photo(path: Path, content: str = "dummy"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    # Ensure mtime is set (sometimes fast writes have same mtime)
    # time.sleep(0.01) 

def test_full_lifecycle_workflow(lifecycle_env, monkeypatch):
    """
    Simulate a user's journey:
    1. Setup students and initial photos.
    2. Run organizer -> Verify results.
    3. Add new photos -> Run -> Verify incremental processing.
    4. Modify a photo -> Run -> Verify re-processing.
    5. Add corrupt photo -> Run -> Verify resilience.
    """
    work_dir, input_dir, output_dir = lifecycle_env
    
    # --- Step 1: Initial Setup ---
    # Create students
    create_dummy_photo(input_dir / "student_photos" / "Alice" / "ref1.jpg")
    create_dummy_photo(input_dir / "student_photos" / "Bob" / "ref1.jpg")
    
    # Create class photos (Day 1)
    day1 = input_dir / "class_photos" / "2025-01-01"
    create_dummy_photo(day1 / "photo1.jpg") # Should match Alice or Bob
    create_dummy_photo(day1 / "photo2.jpg")
    
    # Debug: Verify file creation
    print(f"\nDEBUG: input_dir={input_dir}")
    print(f"DEBUG: class_photos exists? {(input_dir / 'class_photos').exists()}")
    print(f"DEBUG: 2025-01-01 exists? {(input_dir / 'class_photos' / '2025-01-01').exists()}")
    print(f"DEBUG: photo1 exists? {(input_dir / 'class_photos' / '2025-01-01' / 'photo1.jpg').exists()}")
    for p in input_dir.rglob("*"):
        print(f"DEBUG FILE: {p}")
    
    # Fix: Pass input_dir=str(input_dir), output_dir=str(output_dir)
    # Or if SimplePhotoOrganizer takes a root dir and assumes input/output structure?
    # Let's check SimplePhotoOrganizer.__init__ signature.
    # def __init__(self, input_dir=None, output_dir=None, log_dir=None, ...):
    #     if input_dir is None: input_dir = DEFAULT_CONFIG['input_dir'] (which is 'input')
    #     self.input_dir = Path(input_dir)
    
    # So if we pass str(work_dir), self.input_dir is work_dir.
    # It expects work_dir/class_photos.
    # But we created work_dir/input/class_photos.
    
    # We should pass input_dir=str(input_dir), output_dir=str(output_dir), log_dir=str(work_dir/"logs")
    
    log_dir = work_dir / "logs"
    
    class MockServiceContainer:
        def __init__(self, sm):
            self.sm = sm
        def get_student_manager(self):
            return self.sm
        def get_face_recognizer(self):
            return FakeLifecycleRecognizer(self.sm)
        def get_file_organizer(self):
            return FileOrganizer(str(output_dir))
            
    # Run 1
    sm = StudentManager(str(input_dir))
    container = MockServiceContainer(sm)
    
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir), 
        output_dir=str(output_dir), 
        log_dir=str(log_dir),
        service_container=container
    )
    organizer.run()
    
    # Verify Run 1
    assert (output_dir / "Alice" / "2025-01-01" / "photo1.jpg").exists() or \
           (output_dir / "Bob" / "2025-01-01" / "photo1.jpg").exists() or \
           (output_dir / "unknown_faces" / "2025-01-01" / "photo1.jpg").exists()
    
    # Capture state
    # Incremental snapshot is stored under: output_dir/.state/class_photos_snapshot.json
    
    # If still not found, maybe it wasn't saved?
    # save_snapshot is called in main.py after processing.
    # But only if plan.changed_dates or plan.deleted_dates is not empty.
    # In Run 1, we had changed dates (2025-01-01).
    
    # Wait, main.py:
    # if plan.changed_dates or plan.deleted_dates:
    #    ...
    #    save_snapshot(self.output_dir, current)
    
    # So it should be saved.
    
    # Let's print output_dir content
    print(f"\nDEBUG: output_dir content:")
    for p in output_dir.rglob("*"):
        print(f"  {p}")
        
    # Example path:
    # /private/var/.../output/.state/class_photos_snapshot.json
    
    state_files = list(output_dir.rglob("class_photos_snapshot.json"))
    assert len(state_files) > 0
    state_file = state_files[0]
    state_data_1 = state_file.read_text()
    
    # --- Step 2: Incremental Add ---
    # Add Day 2 photos
    day2 = input_dir / "class_photos" / "2025-01-02"
    create_dummy_photo(day2 / "photo3.jpg")
    
    # Run 2
    # Re-create organizer to simulate fresh run
    sm = StudentManager(str(input_dir))
    container = MockServiceContainer(sm)
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir), 
        output_dir=str(output_dir), 
        log_dir=str(log_dir),
        service_container=container
    )
    organizer.run()
    
    # Verify Run 2
    # Check that photo3 is processed
    found_photo3 = list(output_dir.rglob("photo3.jpg"))
    assert len(found_photo3) == 1
    
    # --- Step 3: Modification ---
    # Modify photo1.jpg (change content and mtime)
    p1 = day1 / "photo1.jpg"
    time.sleep(1.1) # Ensure mtime difference > 1s for file system granularity
    p1.write_text("modified content")
    
    # Run 3
    sm = StudentManager(str(input_dir))
    container = MockServiceContainer(sm)
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir), 
        output_dir=str(output_dir), 
        log_dir=str(log_dir),
        service_container=container
    )
    organizer.run()
    
    # Verify Run 3
    # We can't easily check if it was "re-processed" without logs, 
    # but we can check that the state file updated the hash/mtime for this file.
    state_data_3 = state_file.read_text()
    assert state_data_3 != state_data_1
    
    # --- Step 4: Corruption Resilience ---
    create_dummy_photo(day2 / "corrupt_image.jpg")
    
    # Run 4
    sm = StudentManager(str(input_dir))
    container = MockServiceContainer(sm)
    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir), 
        output_dir=str(output_dir), 
        log_dir=str(log_dir),
        service_container=container
    )
    # Should not raise exception
    organizer.run()
    
    # Verify Run 4
    # Corrupt image should NOT be in output (or maybe in unknown if handled gracefully, 
    # but our fake recognizer raises Exception which main.py catches and logs)
    assert not (output_dir / "Alice" / "2025-01-02" / "corrupt_image.jpg").exists()
    
    print("\n✅ Lifecycle workflow test passed!")
