#!/usr/bin/env python3
"""
测试控制台打包产物（release_console）。

合理性说明：
- 该文件验证的是“打包交付物”是否齐全/权限是否正确。
- 在日常开发/CI（尤其是沙箱化测试）中，未必每次都先生成 release_console 产物。
    因此默认策略是：若未发现发布产物，则“跳过”而不是失败。
- 如需强制要求打包产物存在（例如发布前验收），设置环境变量：
    - REQUIRE_PACKAGED_ARTIFACTS=1
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)

RELEASE_DIR = PROJECT_ROOT / "release_console"
EXECUTABLE = RELEASE_DIR / "SundayPhotoOrganizer"
DOC_PATH = RELEASE_DIR / "使用说明.txt"
LAUNCHER = RELEASE_DIR / "启动工具.sh"


def _truthy_env(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def _require_packaged_artifacts() -> bool:
    return _truthy_env("REQUIRE_PACKAGED_ARTIFACTS", default="0")


def _skip_if_missing_release_dir() -> bool:
    if RELEASE_DIR.exists():
        return False
    if _require_packaged_artifacts():
        return False
    print("ℹ️ 未发现 release_console/（未打包），跳过打包产物测试。")
    return True


def test_artifacts_exist():
    """检查控制台发布目录和关键文件是否存在"""
    print("🧪 检查控制台发布产物...")
    if _skip_if_missing_release_dir():
        return True

    required_items = [RELEASE_DIR, EXECUTABLE, DOC_PATH, LAUNCHER]
    all_good = True

    for item in required_items:
        if item.exists():
            print(f"✅ 找到 {item.relative_to(PROJECT_ROOT)}")
        else:
            print(f"❌ 缺少 {item.relative_to(PROJECT_ROOT)}")
            all_good = False

    return all_good


def test_executable_permission():
    """检查可执行权限"""
    print("\n🧪 检查可执行文件权限...")
    if _skip_if_missing_release_dir():
        return True

    if not EXECUTABLE.exists():
        print("❌ 可执行文件不存在")
        return False

    if os.access(EXECUTABLE, os.X_OK):
        print("✅ 可执行权限正常")
        return True

    print("❌ 缺少执行权限")
    return False


def test_launcher_script():
    """检查启动脚本内容与权限"""
    print("\n🧪 检查启动脚本...")
    if _skip_if_missing_release_dir():
        return True

    if not LAUNCHER.exists():
        print("❌ 启动脚本不存在")
        return False

    content = LAUNCHER.read_text(encoding="utf-8")
    has_exec_permission = os.access(LAUNCHER, os.X_OK)
    references_binary = "SundayPhotoOrganizer" in content

    if references_binary:
        print("✅ 脚本包含可执行文件调用")
    else:
        print("❌ 脚本未引用可执行文件")

    if has_exec_permission:
        print("✅ 脚本执行权限正常")
    else:
        print("❌ 脚本缺少执行权限")

    return references_binary and has_exec_permission


def test_documentation():
    """检查控制台用户文档"""
    print("\n🧪 检查用户文档...")
    if _skip_if_missing_release_dir():
        return True

    if not DOC_PATH.exists():
        print("❌ 用户文档不存在")
        return False

    content = DOC_PATH.read_text(encoding="utf-8")
    required_sections = [
        "使用方法",
        "文件夹位置",
        "常见问题",
    ]

    all_good = True
    for section in required_sections:
        if section in content:
            print(f"✅ 包含'{section}'部分")
        else:
            print(f"❌ 缺少'{section}'部分")
            all_good = False

    return all_good


def main():
    """运行所有控制台打包测试"""
    print("🚀 开始测试控制台发布包 (release_console)...")
    print("=" * 60)

    if _skip_if_missing_release_dir():
        return True

    tests = [
        ("产物存在性", test_artifacts_exist),
        ("可执行权限", test_executable_permission),
        ("启动脚本", test_launcher_script),
        ("用户文档", test_documentation),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试出错: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")

    print(f"\n📈 统计:")
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")

    print("\n📂 交付文件:")
    print("• release_console/SundayPhotoOrganizer - 可执行文件")
    print("• release_console/启动工具.sh - 启动脚本")
    print("• release_console/使用说明.txt - 用户手册")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)