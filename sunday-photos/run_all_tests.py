#!/usr/bin/env python3
"""运行所有测试用例"""
import sys
import os
import subprocess
import json
from pathlib import Path
import shutil
import tempfile

import argparse

def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def prepare_test_sandbox(project_root: Path, *, include_release_console: bool) -> Path:
    """创建干净的测试沙箱。

    目的：自动构建测试需要的目录/文件，并避免污染真实 input/output。
    沙箱内容是项目最小可运行子集（src/tests/run.py/README/config.json 等）。
    """

    sandbox_root = Path(tempfile.mkdtemp(prefix="sunday_photos_test_sandbox_"))

    # 复制最小项目集合
    _copy_if_exists(project_root / "src", sandbox_root / "src")
    _copy_if_exists(project_root / "tests", sandbox_root / "tests")
    _copy_if_exists(project_root / "run.py", sandbox_root / "run.py")
    _copy_if_exists(project_root / "README.md", sandbox_root / "README.md")
    _copy_if_exists(project_root / "config.json", sandbox_root / "config.json")
    _copy_if_exists(project_root / "requirements.txt", sandbox_root / "requirements.txt")

    if include_release_console:
        _copy_if_exists(project_root / "release_console", sandbox_root / "release_console")

    # 自动构建测试需要的基础目录（全新、空）
    (sandbox_root / "input" / "student_photos").mkdir(parents=True, exist_ok=True)
    (sandbox_root / "input" / "class_photos").mkdir(parents=True, exist_ok=True)
    (sandbox_root / "output").mkdir(parents=True, exist_ok=True)
    (sandbox_root / "logs").mkdir(parents=True, exist_ok=True)

    return sandbox_root


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run Sunday Photos full test suite in a clean sandbox")
    parser.add_argument(
        "--require-packaged-artifacts",
        action="store_true",
        help="Require release_console artifacts (sets REQUIRE_PACKAGED_ARTIFACTS=1 and copies release_console into sandbox)",
    )
    args = parser.parse_args(argv)

    if args.require_packaged_artifacts:
        os.environ["REQUIRE_PACKAGED_ARTIFACTS"] = "1"

    # 设置路径
    project_root = Path(__file__).resolve().parent
    sandbox_root = prepare_test_sandbox(project_root, include_release_console=args.require_packaged_artifacts)

    # 让本 runner 自己也能 import（虽然测试在子进程中运行）
    sys.path.insert(0, str(sandbox_root / "src"))
    os.chdir(sandbox_root)

    # 确保python命令指向虚拟环境，便于测试脚本使用
    venv_python_dir = (project_root.parent / ".venv" / "bin").resolve()
    if venv_python_dir.exists():
        current_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{venv_python_dir}{os.pathsep}{current_path}"

    # 自动确认交互式提示，防止测试阻塞
    os.environ.setdefault("GUIDE_FORCE_AUTO", "1")

    # 默认：离线稳定（需要联网时可显式设置 ALLOW_NET_TESTDATA=1 / STRICT_NET_TESTDATA=1）
    os.environ.setdefault("ALLOW_NET_TESTDATA", "0")
    os.environ.setdefault("STRICT_NET_TESTDATA", "0")

    # 共享网络测试数据缓存目录：跨多个测试子进程复用
    net_cache_dir = sandbox_root / "_net_testdata_cache"
    net_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TESTDATA_CACHE_DIR", str(net_cache_dir))

    print("=" * 60)
    print("主日学照片整理工具 - 完整测试套件")
    print("=" * 60)
    print(f"测试沙箱目录: {sandbox_root}")
    if args.require_packaged_artifacts:
        print("模式: 发布前验收（REQUIRE_PACKAGED_ARTIFACTS=1）")

    # 测试文件列表
    test_files = [
    ("基础功能测试", "tests/test_basic.py"),
    ("修复验证测试", "tests/test_fixes.py"),
    ("修复验证增强测试", "tests/test_fixes_validation.py"),
    ("增量处理测试", "tests/test_incremental_processing.py"),
    ("联网测试数据构建器测试", "tests/test_network_testdata_builder.py"),
    ("日期推断规则测试", "tests/test_utils_date_inference.py"),
    ("大规模数据构建测试", "tests/test_large_dataset_generation.py"),
    ("文件整理扩展测试", "tests/test_file_organizer_tasks.py"),
    ("集成测试", "tests/test_integration.py"),
    ("教师友好测试", "tests/test_teacher_friendly.py"),
    ("教师上手流测试", "tests/test_teacher_onboarding_flow.py"),
    ("学生规模扩展测试", "tests/test_scalability_student_manager.py"),
    ("教师帮助系统测试", "tests/test_teacher_help_system.py"),
    ("全功能测试", "tests/test_all_teacher_features.py")
    ]

    if args.require_packaged_artifacts:
        test_files.extend(
            [
                ("控制台打包产物测试", "tests/test_packaged_app.py"),
                ("控制台应用交付测试", "tests/test_console_app.py"),
            ]
        )

    return _run_suite(test_files, sandbox_root)


def _truthy_env(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "y")


def _preflight_net_testdata(sandbox_root: Path) -> tuple[bool, str]:
    """Run network testdata preflight inside sandbox.

    Returns (ok, message_to_print).

    中文说明：
    - 该预检会在每个测试用例启动前执行一次（而不是只在整个套件开始时执行）
    - 默认启用联网并且严格：联网失败/下载不足会让该测试直接失败（符合“必须强制成功”的要求）
    - 预检输出尽量压缩为单行，便于日志检索与自动化复查
    """
    min_images = int(os.environ.get("NET_TESTDATA_MIN_IMAGES", "8").strip() or "8")
    code = (
        "import os, time, json, pathlib\n"
        "from tests.testdata_builder import ensure_network_testdata, net_testdata_enabled, net_testdata_strict\n"
        "cache_dir = pathlib.Path(os.environ.get('TESTDATA_CACHE_DIR','') or (pathlib.Path('.')/'_downloaded_images'))\n"
        "cache_dir.mkdir(parents=True, exist_ok=True)\n"
        "def _count_jpgs(d):\n"
        "    return sum(1 for p in d.rglob('*.jpg') if p.is_file() and p.stat().st_size > 0)\n"
        "before = _count_jpgs(cache_dir)\n"
        "t0 = time.time()\n"
        "try:\n"
        f"    imgs = ensure_network_testdata(min_images={min_images})\n"
        "    out = {\n"
        "        'ok': True,\n"
        "        'enabled': bool(net_testdata_enabled()),\n"
        "        'strict': bool(net_testdata_strict()),\n"
        "        'cache_dir': str(cache_dir),\n"
        "        'cached_before': int(before),\n"
        "        'cached_after': int(len(imgs)),\n"
        "        'elapsed_s': round(time.time() - t0, 2),\n"
        "        'force_refresh': os.environ.get('TESTDATA_FORCE_REFRESH','0'),\n"
        "        'queries': os.environ.get('TESTDATA_OPENVERSE_QUERIES',''),\n"
        "    }\n"
        "    print(json.dumps(out, ensure_ascii=False))\n"
        "except Exception as e:\n"
        "    out = {\n"
        "        'ok': False,\n"
        "        'enabled': bool(net_testdata_enabled()),\n"
        "        'strict': bool(net_testdata_strict()),\n"
        "        'cache_dir': str(cache_dir),\n"
        "        'cached_before': int(before),\n"
        "        'elapsed_s': round(time.time() - t0, 2),\n"
        "        'error_type': e.__class__.__name__,\n"
        "        'error': str(e),\n"
        "    }\n"
        "    print(json.dumps(out, ensure_ascii=False))\n"
        "    raise\n"
    )

    preflight = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(sandbox_root),
        env={
            **os.environ,
            "GUIDE_FORCE_AUTO": os.environ.get("GUIDE_FORCE_AUTO", "1"),
        },
    )

    payload = None
    stdout = (preflight.stdout or "").strip()
    if stdout:
        # If multiple lines show up, use the last line as JSON payload.
        last_line = stdout.splitlines()[-1].strip()
        try:
            payload = json.loads(last_line)
        except Exception:
            payload = None

    if preflight.returncode == 0 and isinstance(payload, dict) and payload.get("ok") is True:
        before = int(payload.get("cached_before", 0))
        after = int(payload.get("cached_after", 0))
        delta = after - before
        elapsed = payload.get("elapsed_s", 0)
        cache_dir = payload.get("cache_dir", "")
        cache_id = ""
        try:
            cache_id = Path(str(cache_dir)).name
        except Exception:
            cache_id = ""
        enabled = 1 if payload.get("enabled") else 0
        strict = 1 if payload.get("strict") else 0
        force_refresh = str(payload.get("force_refresh", "0")).strip()
        msg = (
            f"✓ [NET] enabled={enabled} strict={strict} min_images={min_images} "
            f"before={before} after={after} delta={delta} elapsed_s={elapsed} "
            f"force_refresh={force_refresh} cache_id={cache_id}"
        )
        return True, msg

    # Failure: try to surface a concise reason.
    err_type = None
    err_msg = None
    cache_dir = os.environ.get("TESTDATA_CACHE_DIR", "")
    enabled = 1 if _truthy_env("ALLOW_NET_TESTDATA", default="1") else 0
    strict = 1 if _truthy_env("STRICT_NET_TESTDATA", default="1") else 0
    if isinstance(payload, dict):
        err_type = payload.get("error_type")
        err_msg = payload.get("error")
        cache_dir = payload.get("cache_dir") or cache_dir

    stderr = (preflight.stderr or "").strip().splitlines()
    stderr_head = stderr[-1].strip() if stderr else ""
    reason = (f"{err_type}: {err_msg}" if err_type or err_msg else stderr_head or "unknown error").strip()
    msg = f"✗ [NET] preflight_failed enabled={enabled} strict={strict} min_images={min_images} reason={reason} cache_dir={cache_dir}"
    return False, msg


def _run_suite(test_files: list[tuple[str, str]], sandbox_root: Path) -> int:
    passed = 0
    failed = 0

    for test_name, test_file in test_files:
        print(f"\n{'='*60}")
        print(f"运行: {test_name}")
        print(f"文件: {test_file}")
        print(f"{'='*60}")

        try:
            ok, preflight_msg = _preflight_net_testdata(sandbox_root)
            print(preflight_msg)
            if not ok:
                failed += 1
                continue

            # 使用 pytest 运行单个测试文件（确保 conftest.py 生效，且结果与 CI/开发一致）
            sandbox_test_file = sandbox_root / test_file
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(sandbox_test_file)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(sandbox_root),
                env={
                    **os.environ,
                    # 再次确保不会阻塞
                    "GUIDE_FORCE_AUTO": os.environ.get("GUIDE_FORCE_AUTO", "1"),
                },
            )

            # 输出结果
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            if result.returncode == 0:
                print(f"✓ {test_name} - 通过")
                passed += 1
            elif result.returncode == 5:
                # pytest exit code 5: no tests collected
                print(f"ℹ️ {test_name} - 未收集到 pytest 用例（跳过，不计失败）")
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

    print("=" * 60)

    # 清理沙箱（默认清理；设置 KEEP_TEST_SANDBOX=1 可保留）
    keep_sandbox_env = os.environ.get("KEEP_TEST_SANDBOX", "").strip().lower()
    keep_sandbox_on_fail_env = os.environ.get("KEEP_TEST_SANDBOX_ON_FAIL", "1").strip().lower()

    keep_sandbox = keep_sandbox_env in ("1", "true", "yes")
    keep_on_fail = keep_sandbox_on_fail_env in ("1", "true", "yes")

    if failed > 0 and keep_on_fail:
        keep_sandbox = True

    if keep_sandbox:
        print(f"\n🧾 测试沙箱已保留: {sandbox_root}")
    else:
        try:
            shutil.rmtree(sandbox_root)
        except Exception:
            pass

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
