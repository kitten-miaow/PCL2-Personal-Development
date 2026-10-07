"""Java 扫描、版本识别与可用性校验。"""
from __future__ import annotations

import ctypes
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

VERSION_RE = re.compile(r"version \"([^\"]+)\"")
BITS_RE = re.compile(r"(\d+)-?[Bb]it")

# 全盘扫描时跳过的系统/无关目录（这些位置几乎不可能有 Java 且遍历极慢）
SKIP_DIR_NAMES = {
    "$RECYCLE.BIN", "System Volume Information", "Windows", "ProgramData",
    "Recovery", "Documents and Settings", "PerfLogs", "node_modules", ".git",
    "__pycache__", "venv", ".venv", ".gradle", ".m2", "AppData",
    "GameSave", "Steam", "Epic Games",
}


@dataclass
class JavaInfo:
    path: Path            # java.exe 绝对路径
    version: str = "-"    # 如 17.0.10 / 1.8.0_392
    bitness: str = "-"    # 64 / 32
    ok: bool = False      # 是否能运行
    detail: str = ""

    def key(self) -> str:
        return str(self.path).lower()


def _common_java_roots() -> list[Path]:
    """返回常见 Java 安装根目录。"""
    roots: list[Path] = []
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    names = ["Java", "Eclipse Adoptium", "Microsoft", "Zulu", "OpenJDK", "AdoptOpenJDK", "jdk*"]
    for base in (program_files, program_files_x86, os.path.join(local, "Programs")):
        if not base:
            continue
        for n in names:
            roots.append(Path(base) / n)
    return roots


def probe_java(java_exe: Path, timeout: float = 8.0) -> JavaInfo:
    """运行 java -version，识别版本、位数与可用性。"""
    info = JavaInfo(path=java_exe)
    try:
        proc = subprocess.run(
            [str(java_exe), "-version"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        info.detail = f"无法运行: {e}"
        return info
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    m = VERSION_RE.search(output)
    if not m:
        info.detail = "未识别到版本信息"
        return info
    raw = m.group(1)
    # 规范化版本号：1.8.0_392 -> 1.8.0_392（保留），17.0.10 保持
    info.version = raw
    bits = BITS_RE.search(output)
    info.bitness = bits.group(1) if bits else "-"
    info.ok = True
    info.detail = output.strip().splitlines()[0] if output.strip() else "ok"
    return info


def scan_java_dirs(extra_dirs: list[Path] | None = None) -> list[Path]:
    """递归扫描常见目录，返回所有 java.exe 路径（去重）。"""
    roots = _common_java_roots()
    for d in (extra_dirs or []):
        roots.append(d)
    found: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        try:
            matches = root.rglob("java.exe") if root.is_dir() else []
        except OSError:
            continue
        for p in matches:
            key = str(p).lower()
            if key not in seen:
                seen.add(key)
                found.append(p)
    return found


def scan_java(extra_dirs: list[Path] | None = None) -> list[JavaInfo]:
    """扫描并探测所有 Java，返回信息列表。"""
    infos = [probe_java(p) for p in scan_java_dirs(extra_dirs)]
    infos.sort(key=lambda x: (not x.ok, x.path.name.lower()))
    return infos


def build_pcl_java_entry(info: JavaInfo) -> dict:
    """生成一条 PCL 风格的 Java 配置条目（通用字段，供写入/导出）。"""
    return {
        "Path": str(info.path),
        "Version": info.version,
        "Bitness": info.bitness,
        "Available": info.ok,
    }


def _get_fixed_drives() -> list[str]:
    """枚举所有存在盘符（A: 到 Z:），返回如 ['C:\\', 'D:\\']。"""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in range(ord("A"), ord("Z") + 1):
        if bitmask & (1 << (letter - ord("A"))):
            drive = f"{chr(letter)}:\\"
            if os.path.isdir(drive):
                drives.append(drive)
    return drives


def scan_java_whole_disk(progress=None, max_time: float = 180.0,
                         stop_event=None) -> list[Path]:
    """全盘遍历所有盘符查找 java.exe（跳过系统/无关目录）。

    progress(drive: str, found: int, current: int, total: int) 为进度回调。
    找到 200 个或超过 max_time 秒自动停止，防止异常耗时。
    """
    found: set[str] = set()
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
                # 过滤黑名单与隐藏目录
                dirnames[:] = [d for d in dirnames
                               if d not in SKIP_DIR_NAMES and not d.startswith("$")]
                if stop_event is not None and stop_event.is_set():
                    break
                if time.time() - start > max_time:
                    return sorted(found)
                for fn in filenames:
                    if fn.lower() == "java.exe":
                        found.add(os.path.join(dirpath, fn))
                if len(found) >= 200:
                    return sorted(found)
        except OSError:
            continue
        if time.time() - start > max_time:
            break
    return sorted(found)
