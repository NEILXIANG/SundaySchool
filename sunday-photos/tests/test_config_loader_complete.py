"""ConfigLoader 完整测试覆盖"""
import os
import json
import pytest
from pathlib import Path
from src.core.config_loader import ConfigLoader


def test_config_loader_defaults(tmp_path):
    """测试默认配置加载"""
    cl = ConfigLoader(config_file=tmp_path / "nonexistent.json", base_dir=tmp_path)
    
    assert cl.get("tolerance") == 0.6
    assert cl.get("input_dir") == "input"
    assert cl.get_tolerance() == 0.6


def test_config_loader_custom_file(tmp_path):
    """测试自定义配置文件加载"""
    config_file = tmp_path / "custom_config.json"
    config_file.write_text(json.dumps({
        "tolerance": 0.7,
        "input_dir": "my_input"
    }))
    
    cl = ConfigLoader(config_file=config_file, base_dir=tmp_path)
    
    assert cl.get_tolerance() == 0.7
    assert cl.get("input_dir") == "my_input"


def test_config_loader_parallel_env_enable(tmp_path, monkeypatch):
    """测试环境变量启用并行"""
    monkeypatch.setenv("SUNDAY_PHOTOS_PARALLEL", "1")
    
    cl = ConfigLoader(base_dir=tmp_path)
    pr = cl.get_parallel_recognition()
    
    assert pr["enabled"] is True


def test_config_loader_parallel_env_disable(tmp_path, monkeypatch):
    """测试环境变量禁用并行（优先级最高）"""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "parallel_recognition": {"enabled": True}
    }))
    
    monkeypatch.setenv("SUNDAY_PHOTOS_NO_PARALLEL", "1")
    
    cl = ConfigLoader(config_file=config_file, base_dir=tmp_path)
    pr = cl.get_parallel_recognition()
    
    # 环境变量优先级最高，覆盖配置文件
    assert pr["enabled"] is False


def test_config_loader_parallel_priority(tmp_path, monkeypatch):
    """测试并行配置优先级：NO_PARALLEL > PARALLEL > config.json"""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "parallel_recognition": {"enabled": True}
    }))
    
    # 同时设置两个环境变量，NO_PARALLEL 应该优先
    monkeypatch.setenv("SUNDAY_PHOTOS_PARALLEL", "1")
    monkeypatch.setenv("SUNDAY_PHOTOS_NO_PARALLEL", "1")
    
    cl = ConfigLoader(config_file=config_file, base_dir=tmp_path)
    pr = cl.get_parallel_recognition()
    
    assert pr["enabled"] is False


def test_config_loader_save_config(tmp_path):
    """测试保存配置"""
    config_file = tmp_path / "config.json"
    
    cl = ConfigLoader(config_file=config_file, base_dir=tmp_path)
    cl.set("tolerance", 0.8)
    cl.set("custom_field", "test_value")
    
    result = cl.save_config()
    assert result is True
    assert config_file.exists()
    
    # 重新加载验证
    cl2 = ConfigLoader(config_file=config_file, base_dir=tmp_path)
    assert cl2.get("tolerance") == 0.8
    assert cl2.get("custom_field") == "test_value"


def test_config_loader_update(tmp_path):
    """测试批量更新配置"""
    cl = ConfigLoader(base_dir=tmp_path)
    
    cl.update({
        "tolerance": 0.55,
        "new_field": "new_value"
    })
    
    assert cl.get("tolerance") == 0.55
    assert cl.get("new_field") == "new_value"


def test_config_loader_get_all_config(tmp_path):
    """测试获取完整配置"""
    cl = ConfigLoader(base_dir=tmp_path)
    
    all_config = cl.get_all_config()
    
    assert isinstance(all_config, dict)
    assert "tolerance" in all_config
    assert "parallel_recognition" in all_config


def test_config_loader_parallel_workers_validation(tmp_path):
    """测试并行worker数量验证"""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "parallel_recognition": {
            "enabled": True,
            "workers": 0,  # 无效值
            "chunk_size": -5,  # 无效值
            "min_photos": "invalid"  # 无效类型
        }
    }))
    
    cl = ConfigLoader(config_file=config_file, base_dir=tmp_path)
    pr = cl.get_parallel_recognition()
    
    # 应该回退到默认值并修正为有效值
    assert pr["workers"] >= 1
    assert pr["chunk_size"] >= 1
    assert pr["min_photos"] >= 0


def test_config_loader_tolerance_validation(tmp_path):
    """测试tolerance值验证"""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "tolerance": "invalid_string"
    }))
    
    cl = ConfigLoader(config_file=config_file, base_dir=tmp_path)
    
    # 应该回退到默认值
    assert cl.get_tolerance() == 0.6


def test_config_loader_path_resolution(tmp_path):
    """测试路径解析"""
    cl = ConfigLoader(base_dir=tmp_path)
    
    # 相对路径应该基于base_dir解析
    input_dir = cl.get_input_dir()
    assert str(tmp_path / "input") in input_dir or input_dir == "input"
