#!/usr/bin/env python3
"""
主日学课堂照片自动整理工具
运行入口
"""

import os
import sys
import argparse
import warnings
import importlib
import importlib.util
from pathlib import Path

# Ensure project root (containing the src/ package) is importable.
# This avoids importing duplicate modules via top-level "core".
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _sanitize_sys_path_for_app_runtime() -> None:
    """Remove VS Code extension injected site-packages from sys.path.

    Some VS Code extensions prepend their own vendored `tools/site-packages` onto
    `sys.path` during debugging. Those vendored deps (e.g. pydantic v1) can
    shadow the project's venv deps (e.g. pydantic v2), causing imports like
    `insightface` to fail in debug sessions while succeeding in terminals.
    """

    cleaned: list[str] = []
    removed: list[str] = []
    for p in sys.path:
        ps = str(p)
        if "/.vscode/extensions/" in ps and "/tools/site-packages" in ps:
            removed.append(ps)
            continue
        cleaned.append(p)

    if removed:
        sys.path[:] = cleaned

        # Only emit a short message in diagnostic mode to avoid confusing teachers.
        diag_enabled = os.environ.get("SUNDAY_PHOTOS_DIAG_ENV", "").strip().lower() in ("1", "true", "yes")
        if diag_enabled:
            print("🧹 已清理 VS Code 扩展注入的 site-packages 路径:")
            for ps in removed:
                print(f"   - {ps}")


_sanitize_sys_path_for_app_runtime()

from src.core.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_TOLERANCE


def _normalize_backend_engine(raw: str) -> str:
    v = (raw or "").strip().lower()
    if v in ("dlib", "face_recognition", "facerecognition"):
        return "dlib"
    return "insightface"


def _get_backend_engine_from_env_or_config() -> str:
    """Best-effort determine selected face backend.

    Priority:
    - env SUNDAY_PHOTOS_FACE_BACKEND
    - config.json face_backend.engine
    - default insightface

    Note: This is used for *environment checks* (to print correct install hints).
    Main pipeline still applies the authoritative selection logic in core.
    """

    env_raw = os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND", "")
    if env_raw.strip():
        return _normalize_backend_engine(env_raw)

    try:
        from src.core import config as core_config
        from src.core.config_loader import ConfigLoader

        # 显式传入配置路径，避免 ConfigLoader 在 import 时绑定旧的默认常量。
        return _normalize_backend_engine(
            ConfigLoader(config_file=core_config.CONFIG_FILE_PATH).get_face_backend_engine()
        )
    except Exception:
        return "insightface"

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")

    # 某些依赖会触发 pkg_resources 弃用警告；不影响运行，避免干扰老师/调试输出。
    warnings.filterwarnings("ignore", message=r"pkg_resources is deprecated as an API\.")
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        return False
    
    # 检查依赖包（根据人脸后端）
    engine = _get_backend_engine_from_env_or_config()
    if engine == "dlib":
        required_packages = ['face_recognition', 'PIL', 'numpy', 'tqdm']
    else:
        required_packages = ['insightface', 'onnxruntime', 'cv2', 'PIL', 'numpy', 'tqdm']

    diag_enabled = os.environ.get("SUNDAY_PHOTOS_DIAG_ENV", "").strip().lower() in ("1", "true", "yes")
    missing_packages: list[str] = []
    broken_packages: list[tuple[str, str]] = []

    for package in required_packages:
        spec = importlib.util.find_spec(package)
        try:
            importlib.import_module(package)
        except Exception as e:
            # 说明：即使包“已安装”，也可能因为子依赖缺失/二进制库问题/警告被提升为异常等导致导入失败。
            if spec is None:
                missing_packages.append(package)
            else:
                broken_packages.append((package, f"{type(e).__name__}: {e}"))

    if missing_packages or broken_packages:
        print("❌ 环境依赖检查失败")

        # 在失败时输出关键诊断信息（尤其用于 VS Code debug 会话定位解释器/路径差异）。
        print("\n🧭 诊断信息:")
        print(f"   - engine: {engine}")
        print(f"   - cwd: {os.getcwd()}")
        print(f"   - sys.executable: {sys.executable}")
        print(f"   - sys.prefix: {getattr(sys, 'prefix', '')}")
        print(f"   - VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', '')}")
        print(f"   - PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
        print(f"   - SUNDAY_PHOTOS_FACE_BACKEND: {os.environ.get('SUNDAY_PHOTOS_FACE_BACKEND', '')}")

        if missing_packages:
            print("\n📦 未安装的模块:")
            for pkg in missing_packages:
                print(f"   - {pkg}")

        if broken_packages:
            print("\n🧩 已安装但导入失败的模块:")
            for pkg, err in broken_packages:
                print(f"   - {pkg}: {err}")

        print("\n💡 安装/修复建议:")
        if engine == "dlib":
            print("   pip install -r requirements-dlib.txt")
            print("   # 或者：pip install face_recognition dlib")
        else:
            print("   pip install -r requirements.txt")
            print("   # 如果仅 insightface 导入失败：优先看上面的具体异常信息（常见是子依赖/二进制库问题）")
        return False
    
    if diag_enabled:
        print("\n🧭 诊断信息(已开启 SUNDAY_PHOTOS_DIAG_ENV):")
        print(f"   - engine: {engine}")
        print(f"   - cwd: {os.getcwd()}")
        print(f"   - sys.executable: {sys.executable}")
        print(f"   - sys.prefix: {getattr(sys, 'prefix', '')}")
        print(f"   - VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', '')}")
        print(f"   - PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
        print(f"   - SUNDAY_PHOTOS_FACE_BACKEND: {os.environ.get('SUNDAY_PHOTOS_FACE_BACKEND', '')}")

    print("✅ 环境检查通过")
    print("\n✅ 环境检查通过，准备运行主程序。")
    return True

def show_help():
    """显示帮助信息"""
    help_text = f"""
🏫 主日学课堂照片自动整理工具

📋 使用方法:
    1. 在 {DEFAULT_INPUT_DIR}/student_photos/ 里为每个学生创建一个文件夹（文件夹名用于区分学生）
    2. 把该学生的参考照放进对应文件夹（文件名随意，不用改名）
    3. 将待整理课堂照片放入 {DEFAULT_INPUT_DIR}/class_photos/ 目录，可按日期子目录存放（如 2024-12-21/照片.jpg）
    4. 运行此程序

📁 目录结构示例:
   input/
   ├── student_photos/
    │   ├── Alice/
    │   │   ├── ref_01.jpg
    │   │   └── ref_02.png
    │   └── Bob/
    │       └── img_0001.jpg
   └── class_photos/
       ├── 2024-12-21/
       │   ├── group_photo.jpg
       │   └── ...
       └── 2024-12-28/
           └── ...

⚙️ 命令行选项:
    --input-dir      输入数据目录 (默认: {DEFAULT_INPUT_DIR})
    --classroom-dir  输入数据目录兼容参数（已废弃，隐藏）
    --output-dir     输出目录 (默认: {DEFAULT_OUTPUT_DIR})
    --tolerance      人脸识别阈值 (0-1, 默认: {DEFAULT_TOLERANCE})
    --no-parallel    强制禁用并行识别（排障用）
    # 人脸识别后端切换（技术同工/维护者）：
    #   - 环境变量优先：SUNDAY_PHOTOS_FACE_BACKEND=insightface|dlib
    #   - 或在 config.json 中设置 face_backend.engine
    --help           显示此帮助信息

🚀 运行程序:
   python run.py

🆘 遇到问题?
   - 检查照片格式是否支持 (jpg, png等)
   - 确保参考照片清晰且包含完整人脸
    - 识别不准：优先给该学生补 2-5 张更清晰的正脸参考照（放进该学生文件夹即可）
    - 高级（技术同工）：可用 --tolerance 进行微调（0.4-0.8）
"""
    print(help_text)

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="主日学课堂照片自动整理工具",
        add_help=False
    )
    
    parser.add_argument(
        "--input-dir", 
        default=DEFAULT_INPUT_DIR,
        help="输入数据目录 (默认: input)"
    )
    
    parser.add_argument(
        "--output-dir", 
        default=DEFAULT_OUTPUT_DIR,
        help="输出目录 (默认: output)"
    )
    
    parser.add_argument(
        "--tolerance", 
        type=float, 
        default=DEFAULT_TOLERANCE,
        help="人脸识别阈值 (0-1, 默认: 0.6)"
    )

    # 兼容参数（历史版本/文档可能出现；不再推荐使用）
    parser.add_argument(
        "--classroom-dir",
        dest="classroom_dir",
        default=None,
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="强制禁用并行识别（排障用）",
    )
    
    parser.add_argument(
        "--help",
        action="store_true",
        help="显示帮助信息"
    )
    
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="检查运行环境"
    )
    
    args = parser.parse_args()
    input_dir = args.input_dir

    # 让文档口径的 --no-parallel 生效：通过环境变量强制串行。
    if getattr(args, "no_parallel", False):
        os.environ["SUNDAY_PHOTOS_NO_PARALLEL"] = "1"
    
    # 显示帮助
    if args.help:
        show_help()
        return
    
    # 检查环境
    if args.check_env:
        check_environment()
        return
    
    # 启动画面
    print("\n" + "="*60)
    print("🏫 主日学课堂照片自动整理工具")
    print("="*60)
    print("🏫 欢迎使用湖东教会(LECC)主日学照片整理工具！")
    
    # 环境检查
    if not check_environment():
        print("\n❌ 环境检查失败，请解决上述问题后重试")
        sys.exit(1)
    
    # 导入主模块并运行
    try:
        print("\n🚀 启动照片整理程序...")

        # 延迟导入，减少冷启动时的重型依赖加载
        from src.core.main import SimplePhotoOrganizer

        # 创建整理器实例
        organizer = SimplePhotoOrganizer(
            input_dir=input_dir,
            classroom_dir=getattr(args, "classroom_dir", None),
            output_dir=args.output_dir
        )
        
        # 初始化系统（这会初始化face_recognizer）
        if not organizer.initialize():
            print("\n❌ 系统初始化失败")
            sys.exit(1)
            
        # 设置人脸识别阈值
        if hasattr(organizer, 'face_recognizer'):
            organizer.face_recognizer.tolerance = args.tolerance
        
        # 运行整理流程
        print("📂 正在整理照片，请稍候...")
        print("📸 正在扫描照片，寻找每一张笑脸...")
        success = organizer.run()
        
        if success:
            print("✨ 整理完成！所有照片已分类存放到输出目录。")
            print("🎯 照片整理完成！快去看看成果吧！")
            print("\n🎉 程序执行完成！")
        else:
            print("\n❌ 程序执行失败，请查看日志了解详情")
            sys.exit(1)
            
    except ImportError as e:
        print(f"\n❌ 导入模块失败: {e}")
        print("请确保所有依赖包都已正确安装")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        print("请查看详细日志了解问题原因")
        sys.exit(1)

    print("\n🎉 所有准备工作完成，开始整理照片吧！")

if __name__ == "__main__":
    main()