#!/usr/bin/env python3
"""运行所有测试用例"""
import sys
import os
import subprocess
from pathlib import Path

# 设置路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

# 确保python命令指向虚拟环境，便于测试脚本使用
venv_python_dir = (project_root.parent / ".venv" / "bin").resolve()
if venv_python_dir.exists():
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{venv_python_dir}{os.pathsep}{current_path}"

# 自动确认交互式提示，防止测试阻塞
os.environ.setdefault("GUIDE_FORCE_AUTO", "1")

print("="*60)
print("主日学照片整理工具 - 完整测试套件")
print("="*60)

# 测试文件列表
test_files = [
    ("基础功能测试", "tests/test_basic.py"),
    ("修复验证测试", "tests/test_fixes.py"),
    ("修复验证增强测试", "tests/test_fixes_validation.py"),
    ("文件整理扩展测试", "tests/test_file_organizer_tasks.py"),
    ("集成测试", "tests/test_integration.py"),
    ("教师友好测试", "tests/test_teacher_friendly.py"),
    ("教师上手流测试", "tests/test_teacher_onboarding_flow.py"),
    ("学生规模扩展测试", "tests/test_scalability_student_manager.py"),
    ("教师帮助系统测试", "tests/test_teacher_help_system.py"),
    ("全功能测试", "tests/test_all_teacher_features.py")
]

passed = 0
failed = 0

for test_name, test_file in test_files:
    print(f"\n{'='*60}")
    print(f"运行: {test_name}")
    print(f"文件: {test_file}")
    print(f"{'='*60}")
    
    try:
        # 使用python执行测试文件
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # 输出结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✓ {test_name} - 通过")
            passed += 1
        else:
            print(f"✗ {test_name} - 失败 (退出码: {result.returncode})")
            failed += 1
            
    except subprocess.TimeoutExpired:
        print(f"✗ {test_name} - 超时")
        failed += 1
    except Exception as e:
        print(f"✗ {test_name} - 错误: {e}")
        failed += 1

# 汇总结果
print(f"\n{'='*60}")
print("测试汇总")
print(f"{'='*60}")
print(f"总测试数: {len(test_files)}")
print(f"通过: {passed}")
print(f"失败: {failed}")
print(f"成功率: {passed/len(test_files)*100:.1f}%")

if failed == 0:
    print("\n🎉 所有测试通过！项目运行正常。")
else:
    print(f"\n⚠️  {failed} 个测试失败，请检查上述输出。")

print("="*60)
sys.exit(0 if failed == 0 else 1)
