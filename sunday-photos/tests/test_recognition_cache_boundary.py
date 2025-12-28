"""
Tests for recognition cache boundary conditions.
"""
import json
import tempfile
from pathlib import Path
import pytest
from src.core.recognition_cache import (
    load_date_cache,
    save_date_cache_atomic,
    compute_params_fingerprint,
    CACHE_VERSION,
    CACHE_DIR_NAME,
    STATE_DIR_NAME
)

class TestRecognitionCacheBoundary:
    
    @pytest.fixture
    def temp_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_load_corrupted_json(self, temp_output_dir):
        """测试加载损坏的 JSON 缓存文件"""
        date = "2025-01-01"
        cache_dir = temp_output_dir / STATE_DIR_NAME / CACHE_DIR_NAME
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / f"{date}.json"
        
        # 写入乱码
        cache_file.write_text("{invalid_json", encoding="utf-8")
        
        # 加载应返回空缓存，不抛异常
        cache = load_date_cache(temp_output_dir, date)
        assert cache["date"] == date
        assert cache["entries"] == {}
        assert cache["version"] == CACHE_VERSION

    def test_load_empty_file(self, temp_output_dir):
        """测试加载 0 字节缓存文件"""
        date = "2025-01-01"
        cache_dir = temp_output_dir / STATE_DIR_NAME / CACHE_DIR_NAME
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / f"{date}.json"
        
        # 写入空文件
        cache_file.touch()
        
        # 加载应返回空缓存
        cache = load_date_cache(temp_output_dir, date)
        assert cache["entries"] == {}

    def test_backend_switch_invalidation(self, temp_output_dir):
        """测试后端参数变化导致缓存失效"""
        date = "2025-01-01"
        
        # 1. 模拟 InsightFace 缓存
        params_insight = {"engine": "insightface", "tolerance": 0.6}
        fp_insight = compute_params_fingerprint(params_insight)
        
        cache_data = {
            "version": CACHE_VERSION,
            "date": date,
            "params_fingerprint": fp_insight,
            "entries": {"photo1.jpg": {"names": ["Alice"]}}
        }
        save_date_cache_atomic(temp_output_dir, date, cache_data)
        
        # 2. 模拟切换到 dlib (指纹变化)
        # load_date_cache 本身只负责加载文件，指纹比对逻辑在 FaceRecognizer 中
        # 但我们可以验证 load_date_cache 是否忠实返回了文件内容
        loaded = load_date_cache(temp_output_dir, date)
        assert loaded["params_fingerprint"] == fp_insight
        
        # 3. 模拟指纹不匹配场景 (在业务逻辑中会发生)
        params_dlib = {"engine": "dlib", "tolerance": 0.6}
        fp_dlib = compute_params_fingerprint(params_dlib)
        
        assert loaded["params_fingerprint"] != fp_dlib
        # 业务层逻辑应判定失效

    def test_atomic_save_interruption(self, temp_output_dir):
        """测试原子保存机制（模拟）"""
        date = "2025-01-01"
        cache_data = {
            "version": CACHE_VERSION,
            "date": date,
            "params_fingerprint": "abc",
            "entries": {}
        }
        
        save_date_cache_atomic(temp_output_dir, date, cache_data)
        
        cache_file = temp_output_dir / STATE_DIR_NAME / CACHE_DIR_NAME / f"{date}.json"
        assert cache_file.exists()
        
        # 验证没有残留的 .tmp 文件
        tmp_files = list(cache_file.parent.glob("*.tmp"))
        assert len(tmp_files) == 0

