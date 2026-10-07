"""通用工具：路径、时间戳、json 读写、zip 打包、目录定位。"""
from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path

# 项目根目录（src 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"

DEFAULT_SETTINGS = {
    "pcl_root": "",       # PCL 安装根目录（含 .minecraft）
    "mc_dir": "",         # .minecraft 目录（pcl_root 存在时优先用 pcl_root/.minecraft）
    "backup_dir": "",     # 备份保存目录，留空则用 mc_dir/../MCLauncherHelper_backups
    "keep_backups": 10,   # 每个存档保留的最近备份数
}


def now_stamp() -> str:
    """返回 20261007_1430 格式的时间戳。"""
    return time.strftime("%Y%m%d_%H%M%S")


def safe_name(name: str) -> str:
    """把不合法的文件名字符替换为下划线。"""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


def load_settings() -> dict:
    """读取 settings.json，缺失字段补默认值；文件不存在时写入默认。"""
    if not CONFIG_PATH.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}
    merged = {**DEFAULT_SETTINGS, **data}
    return merged


def save_settings(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def resolve_mc_dir(settings: dict) -> Path | None:
    """解析 .minecraft 目录。优先 settings['mc_dir']，其次 pcl_root/.minecraft。"""
    if settings.get("mc_dir"):
        p = Path(settings["mc_dir"]).expanduser()
        if p.is_dir():
            return p
    if settings.get("pcl_root"):
        p = Path(settings["pcl_root"]).expanduser() / ".minecraft"
        if p.is_dir():
            return p
    return None


def resolve_backup_dir(settings: dict, mc_dir: Path) -> Path:
    """确定备份保存目录；不存在则创建。"""
    if settings.get("backup_dir"):
        p = Path(settings["backup_dir"]).expanduser()
    else:
        p = mc_dir.parent / "MCLauncherHelper_backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_zip(src_dir: Path, dest_zip: Path) -> Path:
    """把目录打包为 zip，返回生成的 zip 路径。"""
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(src_dir.parent))
    return dest_zip


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """解压 zip 到目标目录（覆盖式，先清空目标）。"""
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    return dest_dir


def human_time(timestamp: float) -> str:
    """时间戳转本地时间字符串；非法值返回 '-'。"""
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
    except (ValueError, OSError):
        return "-"


def format_size(num_bytes: int) -> str:
    """字节数转可读大小。"""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def dir_size(path: Path) -> int:
    """递归统计目录总字节数。"""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total
