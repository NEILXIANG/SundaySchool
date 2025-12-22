#!/usr/bin/env python3
"""
面向零基础老师的上手流测试：
- 在非交互环境下自动选择默认选项，不阻塞
- 自动创建课堂/输出目录并生成默认配置
- 友好错误信息保持完整
"""
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

# 确保可以导入src模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)

from teacher_helper import TeacherHelper
from interactive_guide import InteractiveGuide


class TeacherOnboardingFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="onboarding_input_"))
        # 保持环境干净
        self.original_cwd = Path.cwd()
        os.chdir(self.temp_dir)
        # 为指南提供最小的src占位，模拟老师拿到的打包目录
        (self.temp_dir / "src").mkdir(parents=True, exist_ok=True)
        # 让指南自动选择默认值
        os.environ["GUIDE_FORCE_AUTO"] = "1"

    def tearDown(self):
        os.chdir(self.original_cwd)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        os.environ.pop("GUIDE_FORCE_AUTO", None)

    def test_non_tty_auto_selection(self):
        """模拟无交互终端，确认自动选择默认，不抛异常。"""
        guide = InteractiveGuide()
        with patch("sys.stdin.isatty", return_value=False):
            # check_directories 应该自动创建课堂/输出文件夹
            created = guide.check_directories()
            self.assertTrue(created)
            self.assertTrue((self.temp_dir / "input").exists())
            self.assertTrue((self.temp_dir / "input" / "student_photos").exists())
            self.assertTrue((self.temp_dir / "input" / "class_photos").exists())
            self.assertTrue((self.temp_dir / "output").exists())

    def test_configuration_auto_creation(self):
        """无配置时自动生成默认 config.json，且内容可读。"""
        guide = InteractiveGuide()
        with patch("sys.stdin.isatty", return_value=False):
            ok = guide.check_configuration()
        self.assertTrue(ok)
        cfg_path = self.temp_dir / "config.json"
        self.assertTrue(cfg_path.exists())
        content = cfg_path.read_text(encoding="utf-8")
        self.assertIn("input", content)
        self.assertIn("output", content)

    def test_friendly_error_contains_solutions(self):
        """老师看得懂的错误提示应包含表情和解决方案。"""
        helper = TeacherHelper()
        msg = helper.get_friendly_error(FileNotFoundError("missing"), "测试上下文")
        self.assertIn("📁", msg)
        self.assertIn("💡", msg)
        self.assertIn("测试上下文", msg)


if __name__ == "__main__":
    unittest.main()
