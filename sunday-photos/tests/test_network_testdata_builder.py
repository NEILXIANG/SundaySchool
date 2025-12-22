"""联网测试数据构建器的单元测试（稳定、无需真实联网）。

目标：
- 验证 FORCE_OFFLINE_TESTDATA / STRICT_NET_TESTDATA 等开关语义正确
- 验证缓存命中时不会触发联网逻辑
- 验证严格模式下获取不到数据会失败（符合“必须强制成功”的要求）

说明：
- 这里通过 mock Openverse URL 获取与下载函数来避免真实网络依赖，确保测试稳定。
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class TestNetworkTestdataBuilder(unittest.TestCase):
    def test_force_offline_short_circuit(self) -> None:
        """FORCE_OFFLINE_TESTDATA=1 时必须直接短路返回，不触发任何联网逻辑。"""
        from tests import testdata_builder

        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td) / "cache"
            env = {
                "FORCE_OFFLINE_TESTDATA": "1",
                "ALLOW_NET_TESTDATA": "1",
                "STRICT_NET_TESTDATA": "1",
                "TESTDATA_CACHE_DIR": str(cache_dir),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(testdata_builder, "openverse_cc0_image_urls", side_effect=AssertionError("should not call")):
                    with mock.patch.object(testdata_builder, "maybe_download_images", side_effect=AssertionError("should not call")):
                        got = testdata_builder.ensure_network_testdata(min_images=2)
                        self.assertEqual(got, [])

    def test_strict_mode_raises_when_no_urls(self) -> None:
        """严格模式下，如果 Openverse 无法返回任何 URL，则应直接失败。"""
        from tests import testdata_builder

        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td) / "cache"
            env = {
                "FORCE_OFFLINE_TESTDATA": "0",
                "ALLOW_NET_TESTDATA": "1",
                "STRICT_NET_TESTDATA": "1",
                "TESTDATA_CACHE_DIR": str(cache_dir),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(testdata_builder, "openverse_cc0_image_urls", return_value=[]):
                    with self.assertRaises(RuntimeError):
                        testdata_builder.ensure_network_testdata(min_images=2, queries=["classroom"])

    def test_cache_hit_skips_network(self) -> None:
        """缓存已经足够时，不应触发 Openverse 查询或下载。"""
        from tests import testdata_builder

        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td) / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # 直接写入两个假 jpg（只要非空即可，构建器只检查 st_size>0）
            (cache_dir / "a.jpg").write_bytes(b"x")
            (cache_dir / "b.jpg").write_bytes(b"y")

            env = {
                "FORCE_OFFLINE_TESTDATA": "0",
                "ALLOW_NET_TESTDATA": "1",
                "STRICT_NET_TESTDATA": "1",
                "TESTDATA_CACHE_DIR": str(cache_dir),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(testdata_builder, "openverse_cc0_image_urls", side_effect=AssertionError("should not call")):
                    with mock.patch.object(testdata_builder, "maybe_download_images", side_effect=AssertionError("should not call")):
                        got = testdata_builder.ensure_network_testdata(min_images=2)
                        self.assertGreaterEqual(len(got), 2)


if __name__ == "__main__":
    unittest.main()
