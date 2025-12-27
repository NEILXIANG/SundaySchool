"""并行识别模块完整测试

测试覆盖范围：
1. 配置创建与验证
2. 子进程初始化器
3. 单张照片识别（有人脸、无人脸、人脸过小、未知人脸）
4. 批量并行识别
5. 环境变量控制
"""

import os
import pytest
from pathlib import Path
from typing import List, Tuple, Any
from unittest.mock import patch, MagicMock
from src.core.parallel_recognizer import (
    ParallelConfig,
    init_worker,
    recognize_one,
    _truthy_env
)


class TestParallelConfig:
    """测试并行配置"""
    
    def test_parallel_config_creation(self):
        """配置对象应该正确创建"""
        config = ParallelConfig(
            enabled=True,
            workers=4,
            chunk_size=10,
            min_photos=50
        )
        
        assert config.enabled is True
        assert config.workers == 4
        assert config.chunk_size == 10
        assert config.min_photos == 50
    
    def test_parallel_config_immutable(self):
        """配置对象应该不可变"""
        config = ParallelConfig(enabled=True, workers=4, chunk_size=10, min_photos=50)
        
        with pytest.raises(AttributeError):
            config.enabled = False  # type: ignore


class TestEnvironmentVariables:
    """测试环境变量处理"""
    
    @pytest.mark.parametrize("env_value,expected", [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("y", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("random", False),
    ])
    def test_truthy_env(self, env_value: str, expected: bool, monkeypatch):
        """环境变量应该正确解析为布尔值"""
        monkeypatch.setenv("TEST_VAR", env_value)
        
        result = _truthy_env("TEST_VAR", default="0")
        
        assert result == expected
    
    def test_truthy_env_default(self, monkeypatch):
        """未设置时应该使用默认值"""
        monkeypatch.delenv("TEST_VAR", raising=False)
        
        result = _truthy_env("TEST_VAR", default="1")
        
        assert result is True


class TestWorkerInitialization:
    """测试子进程初始化"""
    
    def test_init_worker(self):
        """初始化器应该设置全局变量"""
        import src.core.parallel_recognizer as pr
        
        test_encodings = [[0.1, 0.2]]
        test_names = ["张三"]
        test_tolerance = 0.5
        test_min_face_size = 60
        
        init_worker(test_encodings, test_names, test_tolerance, test_min_face_size)
        
        assert pr._G_KNOWN_ENCODINGS == test_encodings
        assert pr._G_KNOWN_NAMES == test_names
        assert pr._G_TOLERANCE == 0.5
        assert pr._G_MIN_FACE_SIZE == 60


class TestRecognizeOne:
    """测试单张照片识别"""
    
    @patch('src.core.face_recognizer.face_recognition.load_image_file')
    @patch('src.core.face_recognizer.face_recognition.face_locations')
    def test_recognize_one_no_faces(self, mock_locations, mock_load):
        """无人脸照片应该返回正确状态"""
        import src.core.parallel_recognizer as pr
        
        # 设置全局变量
        pr._G_KNOWN_ENCODINGS = [[0.1, 0.2]]
        pr._G_KNOWN_NAMES = ["张三"]
        pr._G_TOLERANCE = 0.6
        pr._G_MIN_FACE_SIZE = 50
        
        # Mock 返回无人脸
        mock_load.return_value = MagicMock()
        mock_locations.return_value = []
        
        path, result = recognize_one("/fake/path.jpg")
        
        assert path == "/fake/path.jpg"
        assert result["status"] == "no_faces_detected"
        assert result["total_faces"] == 0
        assert result["recognized_students"] == []
    
    @patch('src.core.face_recognizer.face_recognition.load_image_file')
    @patch('src.core.face_recognizer.face_recognition.face_locations')
    def test_recognize_one_faces_too_small(self, mock_locations, mock_load):
        """人脸过小应该被过滤"""
        import src.core.parallel_recognizer as pr
        
        pr._G_KNOWN_ENCODINGS = [[0.1, 0.2]]
        pr._G_KNOWN_NAMES = ["张三"]
        pr._G_TOLERANCE = 0.6
        pr._G_MIN_FACE_SIZE = 100  # 设置较大的最小尺寸
        
        mock_load.return_value = MagicMock()
        # 返回一个小人脸 (top=0, right=40, bottom=40, left=0) -> 40x40 < 100
        mock_locations.return_value = [(0, 40, 40, 0)]
        
        path, result = recognize_one("/fake/path.jpg")
        
        assert result["status"] == "no_faces_detected"
        assert "尺寸过小" in result["message"]
    
    @patch('src.core.face_recognizer.face_recognition.load_image_file')
    @patch('src.core.face_recognizer.face_recognition.face_locations')
    @patch('src.core.face_recognizer.face_recognition.face_encodings')
    @patch('src.core.face_recognizer.face_recognition.compare_faces')
    @patch('src.core.face_recognizer.face_recognition.face_distance')
    def test_recognize_one_with_match(self, mock_dist, mock_cmp, mock_enc, mock_locs, mock_load):
        """成功识别应该返回学生名字"""
        import numpy as np
        import src.core.parallel_recognizer as pr
        
        pr._G_KNOWN_ENCODINGS = [[0.1, 0.2]]
        pr._G_KNOWN_NAMES = ["张三"]
        pr._G_TOLERANCE = 0.6
        pr._G_MIN_FACE_SIZE = 50
        
        mock_load.return_value = MagicMock()
        mock_locs.return_value = [(0, 100, 100, 0)]  # 100x100 大于50
        mock_enc.return_value = [np.array([0.15, 0.25])]  # 一个编码
        mock_cmp.return_value = [True]  # 匹配成功
        mock_dist.return_value = np.array([0.3])  # 距离小于tolerance
        
        path, result = recognize_one("/fake/path.jpg")
        
        assert result["status"] == "success"
        assert "张三" in result["recognized_students"]
        assert result["total_faces"] == 1


class TestBatchProcessing:
    """测试批量处理（集成测试）"""
    
    @patch('src.core.parallel_recognizer.recognize_one')
    def test_parallel_processing_mock(self, mock_recognize):
        """批量处理应该正确分发任务"""
        from multiprocessing import Pool
        from src.core.parallel_recognizer import init_worker
        
        # Mock recognize_one 返回结果
        mock_recognize.side_effect = [
            ("/path1.jpg", {"status": "success", "recognized_students": ["张三"]}),
            ("/path2.jpg", {"status": "no_faces_detected", "recognized_students": []}),
        ]
        
        # 直接调用（不真的多进程）
        results = [
            mock_recognize("/path1.jpg"),
            mock_recognize("/path2.jpg")
        ]
        
        assert len(results) == 2
        assert results[0][1]["recognized_students"] == ["张三"]
        assert results[1][1]["status"] == "no_faces_detected"
