"""PCL 根目录定位与 config.json 解析（容错实现）。

说明：PCL2 的配置文件为普通 JSON，位于 PCL 安装根目录下（通常名为 config.json）。
不同版本字段名可能不同，这里采用「递归扫描 + 路径匹配」的容错策略：
只要配置里存在指向 java.exe 的路径，就能识别出来，不依赖特定字段名。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

JAVA_EXE_RE = re.compile(r"([A-Za-z]:[\\/][^\"]*?[\\/]java\.exe)", re.IGNORECASE)


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
