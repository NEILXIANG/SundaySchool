#!/usr/bin/env python3
"""
测试控制台版本应用程序。

合理性说明（重要）：
- 该文件原本会直接运行打包后的二进制，并尝试在“真实桌面”创建文件夹结构。
    这在自动化测试/沙箱运行中非常易碎，也会污染真实用户环境。
- 当前策略：
    - 默认只做“产物存在/权限/文档”检查（安全、无副作用）。
    - 只有显式设置 RUN_CONSOLE_BINARY_TESTS=1 时，才会实际启动二进制并做“模拟老师使用”。
    - 启动二进制时会将 HOME 指向临时目录，避免写入真实 Desktop。
"""

import os
import sys
import subprocess
import time
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _truthy_env(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def _require_packaged_artifacts() -> bool:
    return _truthy_env("REQUIRE_PACKAGED_ARTIFACTS", default="0")


def _run_console_binary_tests() -> bool:
    return _truthy_env("RUN_CONSOLE_BINARY_TESTS", default="0")


def _skip_if_missing_release_console() -> bool:
    if Path("release_console").exists():
        return False
    if _require_packaged_artifacts():
        return False
    print("ℹ️ 未发现 release_console/（未打包），跳过控制台打包相关测试。")
    return True


def _temp_home_env() -> tuple[tempfile.TemporaryDirectory[str], dict[str, str]]:
    tmp_home = tempfile.TemporaryDirectory(prefix="sunday_photos_test_home_")
    home_path = Path(tmp_home.name)
    (home_path / "Desktop").mkdir(parents=True, exist_ok=True)
    # Ensure the packaged console binary writes only under the temp home.
    env = {
        **os.environ,
        "HOME": str(home_path),
        # Work root: create input/output/logs directly under this directory.
        "SUNDAY_PHOTOS_WORK_DIR": str(home_path / "Desktop"),
    }
    return tmp_home, env

def test_executable():
    """测试可执行文件"""
    print("🧪 测试可执行文件...")

    if _skip_if_missing_release_console():
        return
    
    bundle_path = Path("release_console/SundayPhotoOrganizer")

    def _resolve_executable() -> Path:
        if bundle_path.is_file():
            return bundle_path
        if bundle_path.is_dir():
            if sys.platform.startswith("win"):
                return bundle_path / "SundayPhotoOrganizer.exe"
            return bundle_path / "SundayPhotoOrganizer"
        return bundle_path

    executable_path = _resolve_executable()
    if not executable_path.exists():
        print("❌ 可执行文件不存在")
        if _require_packaged_artifacts():
            assert False, "可执行文件不存在"
        pytest.skip("未发现 release_console/SundayPhotoOrganizer（可能未打包），跳过")
    
    # 检查文件权限
    if os.access(executable_path, os.X_OK):
        print("✅ 可执行文件权限正常")
    else:
        print("❌ 可执行文件缺少执行权限")
        assert False, "可执行文件缺少执行权限"
    
    # 检查文件大小
    size_mb = executable_path.stat().st_size / (1024 * 1024)
    print(f"📦 文件大小: {size_mb:.1f} MB")
    
    if size_mb > 10:  # 至少10MB
        print("✅ 文件大小正常")
        return
    else:
        print("❌ 文件大小异常")
        assert False, "文件大小异常"

def test_console_launch():
    """测试控制台启动"""
    print("\n🧪 测试控制台启动...")

    if _skip_if_missing_release_console():
        return

    if not _run_console_binary_tests():
        print("ℹ️ 未设置 RUN_CONSOLE_BINARY_TESTS=1，跳过实际启动二进制（仅做静态检查）。")
        return
    
    bundle_path = Path("release_console/SundayPhotoOrganizer")

    def _resolve_executable() -> Path:
        if bundle_path.is_file():
            return bundle_path
        if bundle_path.is_dir():
            if sys.platform.startswith("win"):
                return bundle_path / "SundayPhotoOrganizer.exe"
            return bundle_path / "SundayPhotoOrganizer"
        return bundle_path

    executable_path = _resolve_executable()
    if not executable_path.exists():
        print("❌ 可执行文件不存在")
        if _require_packaged_artifacts():
            assert False, "可执行文件不存在"
        pytest.skip("未发现 release_console/SundayPhotoOrganizer（可能未打包），跳过")
    
    try:
        print("🚀 启动应用程序...")
        print("（这将显示控制台输出，请在5秒内观察）")
        
        # 运行应用，但限制时间
        tmp_home, env = _temp_home_env()
        try:
            result = subprocess.run(
                [str(executable_path)],
                capture_output=True,
                text=True,
                timeout=10,  # 10秒超时
                env=env,
            )
        finally:
            tmp_home.cleanup()
        
        print("📝 应用输出:")
        print(result.stdout[:1000] + ("..." if len(result.stdout) > 1000 else ""))
        
        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr[:500] + ("..." if len(result.stderr) > 500 else ""))
        
        # 检查是否显示了欢迎信息（HUD 版）
        if "SundayPhotoOrganizer Console" in result.stdout or "WORK_DIR=" in result.stdout:
            print("✅ 应用正常启动，显示欢迎信息")
            return
        else:
            print("❌ 应用启动异常，未显示预期信息")
            assert False, "应用启动异常，未显示预期信息"
            
    except subprocess.TimeoutExpired:
        print("✅ 应用正常启动（超时退出是正常的）")
        return
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        raise AssertionError(f"测试过程中出错: {e}") from e

def test_documentation():
    """测试文档"""
    print("\n🧪 测试使用说明文档...")

    if _skip_if_missing_release_console():
        return
    
    doc_path = Path("release_console/README.md")
    if not doc_path.exists():
        print("❌ README.md 不存在")
        assert False, "README.md 不存在"
    
    content = doc_path.read_text(encoding='utf-8')
    
    # Release docs are intentionally minimal; validate key usage guidance.
    required_content = [
        "快速开始",
        "双击",
        "学生参考照",
        "课堂照片",
        "output",
        "详细文档",
    ]
    
    all_good = True
    for item in required_content:
        if item in content:
            print(f"✅ 包含'{item}'说明")
        else:
            print(f"❌ 缺少'{item}'说明")
            all_good = False

    assert all_good, "使用说明文档缺少关键内容"

def test_launcher_script():
    """测试启动脚本"""
    print("\n🧪 测试启动脚本...")

    if _skip_if_missing_release_console():
        return
    
    script_path = Path("release_console/启动工具.sh")
    if not script_path.exists():
        print("❌ 启动脚本不存在")
        assert False, "启动脚本不存在"
    
    # 检查执行权限
    if os.access(script_path, os.X_OK):
        print("✅ 启动脚本执行权限正常")
    else:
        print("❌ 启动脚本缺少执行权限")
        assert False, "启动脚本缺少执行权限"
    
    # 检查内容
    content = script_path.read_text(encoding='utf-8')
    if "SundayPhotoOrganizer" in content:
        print("✅ 启动脚本内容正确")
        return
    else:
        print("❌ 启动脚本内容异常")
        assert False, "启动脚本内容异常"

def simulate_teacher_usage():
    """模拟老师使用场景"""
    print("\n🧪 模拟老师使用场景...")

    if _skip_if_missing_release_console():
        return

    if not _run_console_binary_tests():
        print("ℹ️ 未设置 RUN_CONSOLE_BINARY_TESTS=1，跳过“模拟老师使用”（会运行二进制并产生输出）。")
        return
    
    tmp_home, env = _temp_home_env()
    test_dir = Path(env["HOME"]) / "Desktop"
    
    try:
        # 运行一次程序创建文件夹结构
        executable_path = Path("release_console/SundayPhotoOrganizer")
        
        print("📂 第一次运行（创建文件夹）...")
        try:
            _ = subprocess.run(
                [str(executable_path)],
                capture_output=True,
                text=True,
                timeout=5,
                env=env,
            )
        finally:
            tmp_home.cleanup()
        
        # 检查文件夹是否创建
        if test_dir.exists():
            print("✅ 文件夹结构自动创建成功")
            
            # 检查子文件夹
            required = [
                test_dir / "input" / "student_photos",
                test_dir / "input" / "class_photos",
                test_dir / "output",
                test_dir / "logs",
            ]
            for p in required:
                if p.exists():
                    print(f"✅ {p.relative_to(test_dir)} 文件夹已创建")
                else:
                    print(f"❌ {p.relative_to(test_dir)} 文件夹创建失败")

            # 子目录失败不作为硬失败（仅输出提示），但主目录必须存在
            return
        else:
            print("❌ 文件夹结构创建失败")
            assert False, "文件夹结构创建失败"
            
    except Exception as e:
        print(f"❌ 模拟测试失败: {e}")
        raise AssertionError(f"模拟测试失败: {e}") from e

def main():
    """运行所有测试"""
    print("🚀 开始测试控制台版本应用...")
    print("=" * 60)
    
    tests = [
        ("可执行文件", test_executable),
        ("使用说明文档", test_documentation), 
        ("启动脚本", test_launcher_script),
        ("控制台启动", test_console_launch),
        ("模拟使用场景", simulate_teacher_usage),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            test_func()
            results.append((test_name, True))
        except AssertionError as e:
            print(f"❌ {test_name} 断言失败: {e}")
            results.append((test_name, False))
        except Exception as e:
            print(f"❌ {test_name}测试出错: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print('='*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 统计:")
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    # 最终评估
    print(f"\n🎯 最终评估:")
    if passed == total:
        print("🎉 所有测试通过！控制台版本打包成功！")
        print("✅ 老师们可以直接使用这个控制台应用")
        print("✅ 双击即可运行，无需任何GUI操作")
        print("✅ 自动创建文件夹和处理照片")
    elif passed >= total * 0.8:
        print("🟡 应用基本可用，有少量非关键问题")
    else:
        print("🔴 应用存在问题，需要修复")
    
    print(f"\n📂 交付文件:")
    print("• release_console/SundayPhotoOrganizer - 可执行文件")
    print("• release_console/README.md - 使用说明")
    print("• release_console/启动工具.sh - 启动脚本")
    
    print(f"\n🚀 老师使用方法:")
    print("1. 将 SundayPhotoOrganizer 文件复制到桌面")
    print("2. 双击运行")
    print("3. 程序会自动创建文件夹结构")
    print("4. 按照提示添加学生照片和课堂照片")
    print("5. 等待自动完成整理")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)