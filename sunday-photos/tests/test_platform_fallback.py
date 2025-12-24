import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from src.core.platform_paths import get_default_work_root_dir

def test_work_dir_fallback_logic(tmp_path, monkeypatch):
    """Test that we fallback to Desktop/Home if the program dir is not writable."""
    
    # 1. Simulate writable program dir (Happy Path)
    program_dir = tmp_path / "app_dir"
    program_dir.mkdir()
    
    # Mock sys.executable or whatever get_program_dir uses
    # Actually get_default_work_root_dir uses get_program_dir which uses sys.executable or __file__
    # We'll mock get_program_dir directly
    
    with patch("src.core.platform_paths.get_program_dir", return_value=program_dir):
        # Mock os.access to return True (Writable)
        with patch("os.access", return_value=True):
            work_dir = get_default_work_root_dir()
            assert work_dir == program_dir
            
    # 2. Simulate READ-ONLY program dir (Fallback Path)
    with patch("src.core.platform_paths.get_program_dir", return_value=program_dir):
        # Mock os.access to return False (Not Writable)
        # Note: _is_writable_dir uses mkdir/write/unlink, not os.access directly.
        # We need to patch _is_writable_dir in src.core.platform_paths
        
        with patch("src.core.platform_paths._is_writable_dir") as mock_writable:
            # First call (program_dir) -> False
            # Second call (desktop) -> True
            # Third call (home) -> True
            mock_writable.side_effect = [False, True, True]
            
            # Mock Path.home()
            fake_home = tmp_path / "fake_home"
            fake_home.mkdir()
            (fake_home / "Desktop").mkdir()
            
            with patch("pathlib.Path.home", return_value=fake_home):
                # Also need to patch get_desktop_dir to return our fake desktop
                with patch("src.core.platform_paths.get_desktop_dir", return_value=fake_home / "Desktop"):
                    work_dir = get_default_work_root_dir()
                    # Should fallback to Desktop
                    assert work_dir == fake_home / "Desktop"

def test_env_var_override(tmp_path):
    """Test that SUNDAY_PHOTOS_WORK_DIR env var overrides everything."""
    custom_dir = tmp_path / "custom_work"
    
    with patch.dict(os.environ, {"SUNDAY_PHOTOS_WORK_DIR": str(custom_dir)}):
        work_dir = get_default_work_root_dir()
        assert work_dir == custom_dir
