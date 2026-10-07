"""PCL 根目录定位与 config.json 解析（容错实现）。

说明：PCL2 的配置文件为普通 JSON，位于 PCL 安装根目录下（通常名为 config.json）。
不同版本字段名可能不同，这里采用「递归扫描 + 路径匹配」的容错策略：
只要配置里存在指向 java.exe 的路径，就能识别出来，不依赖特定字段名。
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from .java_manager import SKIP_DIR_NAMES, _get_fixed_drives

JAVA_EXE_RE = re.compile(r"([A-Za-z]:[\\/][^\"]*?[\\/]java\.exe)", re.IGNORECASE)


def scan_minecraft_dirs(progress=None, max_time: float = 180.0,
                        stop_event=None) -> list[Path]:
    """全盘遍历所有盘符，查找 PCL/MC 的 .minecraft 目录（含 versions 或 saves）。

    progress(drive: str, found: int, current: int, total: int) 为进度回调。
    找到 50 个或超过 max_time 秒自动停止。
    """
    found: dict[str, Path] = {}
    start = time.time()
    drives = _get_fixed_drives()
    total = len(drives)
    for idx, drive in enumerate(drives):
        if stop_event is not None and stop_event.is_set():
            break
        if progress:
            progress(drive, len(found), idx + 1, total)
        try:
            for dirpath, dirnames, filenames in os.walk(drive):
                dirnames[:] = [d for d in dirnames
                               if d not in SKIP_DIR_NAMES and not d.startswith("$")]
                if stop_event is not None and stop_event.is_set():
                    break
                if time.time() - start > max_time:
                    return list(found.values())
                for name in dirnames:
                    if name.lower() == ".minecraft":
                        full = os.path.join(dirpath, name)
                        if os.path.isdir(os.path.join(full, "versions")) or \
                           os.path.isdir(os.path.join(full, "saves")):
                            found[full.lower()] = Path(full)
                if len(found) >= 50:
                    return list(found.values())
        except OSError:
            continue
        if time.time() - start > max_time:
            break
    return list(found.values())


def find_pcl_config(pcl_root: str | Path) -> Path | None:
    """在 PCL 根目录下定位配置文件 config.json（浅层搜索）。"""
    root = Path(pcl_root).expanduser()
    if not root.is_dir():
        return None
    # 直接位于根目录
    for cand in (root / "config.json", root / "PCL" / "config.json"):
        if cand.is_file():
            return cand
    # 浅层（两层内）找名为 config.json 的文件
    for level in range(2):
        for f in root.rglob("config.json"):
            try:
                f.relative_to(root)
            except ValueError:
                continue
            if len(f.relative_to(root).parts) <= level + 1:
                return f
    return None


def load_pcl_config(pcl_root: str | Path) -> dict:
    """读取 PCL 配置为 dict；未找到返回空 dict。"""
    cfg = find_pcl_config(pcl_root)
    if not cfg:
        return {}
    try:
        return json.loads(cfg.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def find_java_paths(pcl_config: dict) -> list[str]:
    """递归扫描配置中所有指向 java.exe 的路径（去重、保序）。"""
    paths: list[str] = []
    seen: set[str] = set()

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            for m in JAVA_EXE_RE.findall(obj):
                norm = m.replace("\\\\", "\\").replace("/", "\\")
                if norm.lower() not in seen:
                    seen.add(norm.lower())
                    paths.append(norm)

    walk(pcl_config)
    return paths
