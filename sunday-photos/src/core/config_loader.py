"""
配置加载器模块
提供从文件加载配置的功能
"""

import os
import json
import logging
from pathlib import Path
from .config import DEFAULT_INPUT_DIR

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器，支持从JSON文件加载配置"""
    
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.config_data = {}
        
        # 默认配置文件位置：项目根目录的 config.json（sunday-photos/config.json）
        # 说明：本文件位于 src/core/，上溯两级为项目根目录。
        if not self.config_file:
            self.config_file = Path(__file__).resolve().parents[2] / "config.json"
        
        # 尝试加载配置文件
        self.load_config()
    
    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                logger.info(f"已加载配置文件: {self.config_file}")
            else:
                logger.info(f"配置文件不存在: {self.config_file}，使用默认配置")
                self.config_data = {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            self.config_data = {}
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config_data.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config_data[key] = value
    
    def update(self, data):
        """更新配置"""
        self.config_data.update(data)
    
    def get_input_dir(self):
        """获取输入数据目录配置"""
        return self.get('input_dir', DEFAULT_INPUT_DIR)
    
    def get_output_dir(self):
        """获取输出目录配置"""
        return self.get('output_dir', 'output')
    
    def get_log_dir(self):
        """获取日志目录配置"""
        return self.get('log_dir', 'logs')
    
    def get_tolerance(self):
        """获取人脸识别阈值配置"""
        return self.get('tolerance', 0.6)

    def get_parallel_recognition(self):
        """获取并行识别配置。

        约定：
        - 未配置时使用保守默认值
        - 环境变量 SUNDAY_PHOTOS_NO_PARALLEL=1 可强制关闭（便于排障/低内存机器）
        """
        raw = self.get('parallel_recognition', {}) or {}
        try:
            enabled = bool(raw.get('enabled', False))
            workers = int(raw.get('workers', 4))
            chunk_size = int(raw.get('chunk_size', 12))
            min_photos = int(raw.get('min_photos', 30))
        except Exception:
            enabled, workers, chunk_size, min_photos = False, 4, 12, 30

        if os.environ.get('SUNDAY_PHOTOS_NO_PARALLEL', '').strip().lower() in ('1', 'true', 'yes', 'y', 'on'):
            enabled = False

        # 最小保护
        if workers < 1:
            workers = 1
        if chunk_size < 1:
            chunk_size = 1
        if min_photos < 0:
            min_photos = 0

        return {
            'enabled': enabled,
            'workers': workers,
            'chunk_size': chunk_size,
            'min_photos': min_photos,
        }
    
    def get_all_config(self):
        """获取所有配置"""
        return self.config_data