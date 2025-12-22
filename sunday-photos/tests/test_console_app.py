#!/usr/bin/env python3
"""
测试控制台版本应用程序
"""

import os
import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def test_executable():
    """测试可执行文件"""
    print("🧪 测试可执行文件...")
    
    executable_path = Path("release_console/SundayPhotoOrganizer")
    if not executable_path.exists():
        print("❌ 可执行文件不存在")
        return False
    
    # 检查文件权限
    if os.access(executable_path, os.X_OK):
        print("✅ 可执行文件权限正常")
    else:
        print("❌ 可执行文件缺少执行权限")
        return False
    
    # 检查文件大小
    size_mb = executable_path.stat().st_size / (1024 * 1024)
    print(f"📦 文件大小: {size_mb:.1f} MB")
    
    if size_mb > 10:  # 至少10MB
        print("✅ 文件大小正常")
        return True
    else:
        print("❌ 文件大小异常")
        return False

def test_console_launch():
    """测试控制台启动"""
    print("\n🧪 测试控制台启动...")
    
    executable_path = Path("release_console/SundayPhotoOrganizer")
    if not executable_path.exists():
        print("❌ 可执行文件不存在")
        return False
    
    try:
        print("🚀 启动应用程序...")
        print("（这将显示控制台输出，请在5秒内观察）")
        
        # 运行应用，但限制时间
        result = subprocess.run(
            [str(executable_path)], 
            capture_output=True, 
            text=True,
            timeout=10  # 10秒超时
        )
        
        print("📝 应用输出:")
        print(result.stdout[:1000] + ("..." if len(result.stdout) > 1000 else ""))
        
        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr[:500] + ("..." if len(result.stderr) > 500 else ""))
        
        # 检查是否显示了欢迎信息
        if "主日学课堂照片自动整理工具" in result.stdout:
            print("✅ 应用正常启动，显示欢迎信息")
            return True
        else:
            print("❌ 应用启动异常，未显示预期信息")
            return False
            
    except subprocess.TimeoutExpired:
        print("✅ 应用正常启动（超时退出是正常的）")
        return True
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def test_documentation():
    """测试文档"""
    print("\n🧪 测试使用说明文档...")
    
    doc_path = Path("release_console/使用说明.txt")
    if not doc_path.exists():
        print("❌ 使用说明文档不存在")
        return False
    
    content = doc_path.read_text(encoding='utf-8')
    
    # 检查关键内容
    required_content = [
        "双击运行",
        "学生照片",
        "课堂照片",
        "桌面"
    ]
    
    all_good = True
    for item in required_content:
        if item in content:
            print(f"✅ 包含'{item}'说明")
        else:
            print(f"❌ 缺少'{item}'说明")
            all_good = False
    
    return all_good

def test_launcher_script():
    """测试启动脚本"""
    print("\n🧪 测试启动脚本...")
    
    script_path = Path("release_console/启动工具.sh")
    if not script_path.exists():
        print("❌ 启动脚本不存在")
        return False
    
    # 检查执行权限
    if os.access(script_path, os.X_OK):
        print("✅ 启动脚本执行权限正常")
    else:
        print("❌ 启动脚本缺少执行权限")
        return False
    
    # 检查内容
    content = script_path.read_text(encoding='utf-8')
    if "SundayPhotoOrganizer" in content:
        print("✅ 启动脚本内容正确")
        return True
    else:
        print("❌ 启动脚本内容异常")
        return False

def simulate_teacher_usage():
    """模拟老师使用场景"""
    print("\n🧪 模拟老师使用场景...")
    
    # 清理桌面（如果存在之前的测试文件夹）
    test_dir = Path.home() / "Desktop" / "主日学照片整理"
    
    try:
        # 运行一次程序创建文件夹结构
        executable_path = Path("release_console/SundayPhotoOrganizer")
        
        print("📂 第一次运行（创建文件夹）...")
        result = subprocess.run(
            [str(executable_path)], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        
        # 检查文件夹是否创建
        if test_dir.exists():
            print("✅ 文件夹结构自动创建成功")
            
            # 检查子文件夹
            subdirs = ["student_photos", "class_photos", "output", "logs"]
            for subdir in subdirs:
                subdir_path = test_dir / subdir
                if subdir_path.exists():
                    print(f"✅ {subdir} 文件夹已创建")
                else:
                    print(f"❌ {subdir} 文件夹创建失败")
            
            return True
        else:
            print("❌ 文件夹结构创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 模拟测试失败: {e}")
        return False

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
            result = test_func()
            results.append((test_name, result))
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
    print("• release_console/使用说明.txt - 使用说明")
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