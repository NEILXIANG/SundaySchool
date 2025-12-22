"""测试数据构建器（供多个测试用例复用）。

核心目标：
- 为测试提供“真实可打开”的 JPEG（默认用 Pillow 合成，避免版权/IP 风险）。
- 覆盖边界情况：少量 0 字节文件/坏文件，验证主流程不会崩溃且不会产生误报。

联网策略（按你的最新要求）：
- 默认启用联网并且默认严格：只要联网数据获取失败/数量不足，就应让测试失败。
- 通过共享缓存目录复用已下载资源，减少重复下载并提高稳定性。

本模块设计为被多个测试文件 import 并复用。
"""

from __future__ import annotations

import os
import random
import io
import json
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class GeneratedDataset:
    input_dir: Path
    student_dir: Path
    class_dir: Path
    output_dir: Path
    log_dir: Path
    student_names: List[str]
    dates: List[str]


def _truthy_env(name: str, default: str = "0") -> bool:
    val = os.environ.get(name, default).strip().lower()
    return val in ("1", "true", "yes", "y", "on")


def net_testdata_enabled() -> bool:
    """是否启用联网测试数据。

    约定：默认启用；只有显式设置 FORCE_OFFLINE_TESTDATA=1 才关闭。
    """
    if _truthy_env("FORCE_OFFLINE_TESTDATA", default="0"):
        return False
    # Default ON
    return os.environ.get("ALLOW_NET_TESTDATA", "1").strip() == "1"


def net_testdata_strict() -> bool:
    """是否启用严格模式。

    严格模式含义：在联网启用时，只要数据不足/下载失败，就必须抛错使测试失败。
    """
    return os.environ.get("STRICT_NET_TESTDATA", "1").strip() == "1"


def testdata_cache_dir(fallback: Path) -> Path:
    """返回联网测试数据缓存目录。

    - 优先使用环境变量 TESTDATA_CACHE_DIR（便于 run_all_tests.py 在沙箱中指定共享缓存）
    - 否则回退到调用方提供的 fallback
    """
    raw = os.environ.get("TESTDATA_CACHE_DIR", "").strip()
    if raw:
        return Path(raw)
    return fallback


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def write_empty_file(path: Path) -> None:
    write_bytes(path, b"")


def write_jpeg(path: Path, text: str, size: Tuple[int, int] = (640, 420), seed: int = 0) -> None:
    """写入一张可打开的合成 JPEG。

    用途：
    - 让测试使用“真实图片文件”而不是 0 字节占位文件
    - 完全离线生成，规避版权/IP 风险
    """
    from PIL import Image, ImageDraw

    rnd = random.Random(seed)
    bg = (rnd.randint(30, 220), rnd.randint(30, 220), rnd.randint(30, 220))
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    draw.text((12, 12), text, fill=(255, 255, 255))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG", quality=80)


def _parse_urls_from_env(env_var: str = "TESTDATA_URLS") -> List[str]:
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return []
    # Support comma-separated or newline-separated lists.
    parts: List[str] = []
    for line in raw.splitlines():
        parts.extend([p.strip() for p in line.split(",")])
    urls = [p for p in parts if p]
    # Basic sanity filter
    return [u for u in urls if u.startswith("http://") or u.startswith("https://")]


def _parse_queries_from_env(env_var: str = "TESTDATA_OPENVERSE_QUERIES") -> List[str]:
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return []
    parts: List[str] = []
    for line in raw.splitlines():
        parts.extend([p.strip() for p in line.split(",")])
    return [p for p in parts if p]


def openverse_cc0_image_urls(
    query: str,
    page_size: int = 20,
    timeout_sec: int = 10,
) -> List[str]:
    """从 Openverse 获取 CC0 图片的直链 URL 列表。

    说明：
    - Openverse 是 CC 资源聚合平台，这里只取 `license=cc0` 的图片。
    - 返回的是可直接下载的图片 URL（但不同来源的格式/内容可能不一致，后续会做“解码后再编码为 JPEG”的规范化）。
    """
    import urllib.parse
    import urllib.request

    def _ssl_context():
        try:
            import certifi  # type: ignore

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context()

    qs = urllib.parse.urlencode(
        {
            "q": query,
            "license": "cc0",
            "page_size": str(int(page_size)),
        }
    )
    url = f"https://api.openverse.org/v1/images/?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "SundaySchool-TestData/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_sec, context=_ssl_context()) as resp:
        payload = resp.read()
    data = json.loads(payload.decode("utf-8"))
    results = data.get("results", [])
    urls: List[str] = []
    for item in results:
        if item.get("license") != "cc0":
            continue
        u = item.get("url")
        if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
            urls.append(u)
    return urls


def _normalize_bytes_to_jpeg_bytes(content: bytes) -> bytes:
    """Best-effort decode then re-encode as JPEG bytes."""
    from PIL import Image

    with Image.open(io.BytesIO(content)) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue()


def generate_dates(prefix: str, start_day: int, count: int) -> List[str]:
    """Generate YYYY-MM-DD strings like 2025-12-01.."""
    dates: List[str] = []
    for i in range(count):
        day = start_day + i
        dates.append(f"{prefix}-{day:02d}")
    return dates


def generate_students(count: int, prefix: str = "Student") -> List[str]:
    return [f"{prefix}_{i:02d}" for i in range(1, count + 1)]


def build_dataset(
    base_dir: Path,
    student_count: int = 12,
    date_prefix: str = "2025-12",
    date_start_day: int = 1,
    date_count: int = 12,
    photos_per_date: int = 6,
    unknown_per_date: int = 1,
    empty_file_ratio: float = 0.05,
    seed: int = 123,
) -> GeneratedDataset:
    """Build a deterministic dataset under base_dir.

    - Writes real JPEGs for student reference photos and class photos.
    - Optionally sprinkles a few 0-byte files to validate robustness.
    """
    rnd = random.Random(seed)
    input_dir = base_dir / "input"
    student_dir = input_dir / "student_photos"
    class_dir = input_dir / "class_photos"
    output_dir = base_dir / "output"
    log_dir = base_dir / "logs"

    student_names = generate_students(student_count)
    dates = generate_dates(date_prefix, date_start_day, date_count)

    # Optional/Default: network-backed CC0 images.
    # - Default is ON + strict, unless FORCE_OFFLINE_TESTDATA=1.
    # - If enabled and strict: must succeed (no silent fallback).
    cache_dir = testdata_cache_dir(base_dir / "_downloaded_images")
    urls = _parse_urls_from_env("TESTDATA_URLS")
    downloaded_paths: List[Path] = []

    if net_testdata_enabled():
        if urls:
            downloaded_paths = maybe_download_images(cache_dir, urls)
        else:
            # Ensure a baseline cache via Openverse.
            downloaded_paths = ensure_network_testdata(min_images=8)

        # Strict mode: require some downloaded assets.
        if net_testdata_strict() and not downloaded_paths:
            raise RuntimeError("联网测试数据：未能获得任何可用图片（严格模式）")

    downloaded_bytes: List[bytes] = []
    for p in _list_cached_jpegs(cache_dir):
        try:
            b = p.read_bytes()
            if b:
                downloaded_bytes.append(b)
        except Exception:
            continue

    if net_testdata_enabled() and net_testdata_strict() and not downloaded_bytes:
        raise RuntimeError("联网测试数据：缓存中没有可用图片字节（严格模式）")

    # Students: 1 photo each
    for i, name in enumerate(student_names):
        p = student_dir / f"{name}.jpg"
        if rnd.random() < empty_file_ratio:
            write_empty_file(p)
        else:
            if downloaded_bytes:
                content = downloaded_bytes[i % len(downloaded_bytes)]
                write_bytes(p, content)
            else:
                # Only allowed when offline/explicitly non-network.
                write_jpeg(p, text=f"student={name}", seed=seed + i)

    # Class photos by date
    for di, date in enumerate(dates):
        for pi in range(1, photos_per_date + 1):
            p = class_dir / date / f"photo_{pi:02d}.jpg"
            if rnd.random() < empty_file_ratio:
                write_empty_file(p)
            else:
                if downloaded_bytes:
                    content = downloaded_bytes[(di * photos_per_date + (pi - 1)) % len(downloaded_bytes)]
                    write_bytes(p, content)
                else:
                    write_jpeg(p, text=f"date={date} photo={pi:02d}", seed=seed + di * 100 + pi)

        for ui in range(1, unknown_per_date + 1):
            p = class_dir / date / f"unknown_{ui:02d}.jpg"
            if rnd.random() < empty_file_ratio:
                write_empty_file(p)
            else:
                if downloaded_bytes:
                    content = downloaded_bytes[(di * unknown_per_date + (ui - 1)) % len(downloaded_bytes)]
                    write_bytes(p, content)
                else:
                    write_jpeg(p, text=f"date={date} unknown={ui:02d}", seed=seed + di * 1000 + ui)

    # Ensure dirs exist
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    return GeneratedDataset(
        input_dir=input_dir,
        student_dir=student_dir,
        class_dir=class_dir,
        output_dir=output_dir,
        log_dir=log_dir,
        student_names=student_names,
        dates=dates,
    )


def maybe_download_images(
    dest_dir: Path,
    urls: Iterable[str],
    enabled_env: str = "ALLOW_NET_TESTDATA",
) -> List[Path]:
    """Optionally download images into dest_dir.

    This is OFF by default because it makes tests flaky/offline-unfriendly.
    Enable by setting env var ALLOW_NET_TESTDATA=1.
    """
    # Keep compatibility with the old flag, but also respect the new defaults.
    if not net_testdata_enabled() or os.environ.get(enabled_env, "1") != "1":
        return []

    import urllib.request

    def _ssl_context():
        try:
            import certifi  # type: ignore

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context()

    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    for i, url in enumerate(urls):
        target = dest_dir / f"download_{i:02d}.jpg"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SundaySchool-TestData/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
                content = resp.read()
            if not content:
                continue
            # Normalize to a real JPEG for downstream consumers.
            try:
                jpeg_bytes = _normalize_bytes_to_jpeg_bytes(content)
                if not jpeg_bytes:
                    continue
                write_bytes(target, jpeg_bytes)
                saved.append(target)
            except Exception:
                # If decode fails, skip to avoid producing broken test assets.
                continue
        except Exception:
            # Keep best-effort; caller can decide whether to assert.
            continue
    return saved


def _list_cached_jpegs(cache_dir: Path) -> List[Path]:
    if not cache_dir.exists():
        return []
    files = [p for p in cache_dir.rglob("*.jpg") if p.is_file() and p.stat().st_size > 0]
    return sorted(files)


def ensure_network_testdata(
    min_images: int = 8,
    queries: List[str] | None = None,
    force_refresh_env: str = "TESTDATA_FORCE_REFRESH",
) -> List[Path]:
    """确保共享缓存中至少存在 `min_images` 张可用的 CC0 图片（JPEG）。

    行为约定：
    - 未启用联网（FORCE_OFFLINE_TESTDATA=1）：直接返回空列表，不做任何联网。
    - 启用联网：优先复用缓存；缓存不足时才去 Openverse 拉 URL 并下载。
    - 严格模式（默认开启）：若最终仍不足 `min_images`，抛出 RuntimeError 让测试失败。

    刷新策略：
    - 设置 TESTDATA_FORCE_REFRESH=1 会忽略“缓存已足够”的短路逻辑，强制重新拉取/下载。
    """
    if not net_testdata_enabled():
        return []

    if queries is None:
        queries = _parse_queries_from_env("TESTDATA_OPENVERSE_QUERIES") or ["classroom", "kids", "church"]

    cache_dir = testdata_cache_dir(Path(".") / "_downloaded_images")
    cache_dir.mkdir(parents=True, exist_ok=True)

    force = _truthy_env(force_refresh_env, default="0")
    cached = _list_cached_jpegs(cache_dir)
    if (not force) and len(cached) >= int(min_images):
        return cached

    # Fetch candidate URLs from Openverse.
    urls: List[str] = []
    for q in queries:
        urls.extend(openverse_cc0_image_urls(q, page_size=max(10, int(min_images))))
        if len(urls) >= int(min_images) * 2:
            break

    if not urls:
        if net_testdata_strict():
            raise RuntimeError("联网测试数据：无法从 Openverse 获取任何 CC0 图片 URL")
        return cached

    # Download and normalize. Stop early once we have enough.
    needed = int(min_images)
    saved: List[Path] = []
    # Spread across urls but keep cap.
    for batch_start in range(0, len(urls), 20):
        batch = urls[batch_start:batch_start + 20]
        saved = maybe_download_images(cache_dir, batch)
        cached = _list_cached_jpegs(cache_dir)
        if len(cached) >= needed:
            return cached

    cached = _list_cached_jpegs(cache_dir)
    if net_testdata_strict() and len(cached) < needed:
        raise RuntimeError(f"联网测试数据：下载后仍不足 {needed} 张有效图片（当前 {len(cached)}）")
    return cached
