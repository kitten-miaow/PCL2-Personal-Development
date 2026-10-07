"""存档扫描、level.dat 读取、备份与恢复。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import utils

try:
    import nbtlib
    HAS_NBT = True
except Exception:  # pragma: no cover
    HAS_NBT = False


@dataclass
class SaveInfo:
    name: str                # 世界名
    dir_name: str            # 存档文件夹名
    path: Path               # 存档目录绝对路径
    game_version: str = "-"
    last_played: str = "-"
    size: str = "-"
    file_count: int = 0
    isolated_version: str = ""  # PCL 隔离版本名（空 = 统一 .minecraft/saves 目录）
    backups: list = field(default_factory=list)  # 该存档的备份文件路径


def find_saves_dir(mc_dir: Path) -> Path:
    """返回存档目录（.minecraft/saves）。"""
    return mc_dir / "saves"


def read_level_dat(save_dir: Path) -> dict:
    """读取 level.dat，返回 {'name','game_version','last_played'}，失败返回空。"""
    level = save_dir / "level.dat"
    info: dict[str, str] = {}
    if not level.is_file() or not HAS_NBT:
        return info
    try:
        data = nbtlib.load(level)
        root = data.get("Data", data)
        if isinstance(root, dict):
            name = root.get("LevelName")
            if name is not None:
                info["name"] = str(name)
            played = root.get("LastPlayed")
            if played is not None:
                info["last_played"] = utils.human_time(float(played))
            ver = root.get("Version") or {}
            if isinstance(ver, dict) and ver.get("Name"):
                info["game_version"] = str(ver["Name"])
    except Exception:
        pass
    return info


def list_isolated_version_dirs(mc_dir: Path) -> list[Path]:
    """返回 .minecraft/versions 下所有版本隔离目录（排除 .json/.jar 等文件）。

    PCL2 开启「版本隔离」后，每个版本的存档/资源存放在
    .minecraft/versions/<版本名>/saves 等独立目录，避免版本间互相冲突。
    """
    vdir = mc_dir / "versions"
    if not vdir.is_dir():
        return []
    dirs = [d for d in vdir.iterdir() if d.is_dir()]
    dirs.sort(key=lambda p: p.name.lower())
    return dirs


def _scan_saves_dir(saves_dir: Path, isolated_version: str) -> list[SaveInfo]:
    """扫描单个存档目录，返回其下所有世界存档（按最后修改时间倒序）。"""
    result: list[SaveInfo] = []
    if not saves_dir.is_dir():
        return result
    for sub in sorted(saves_dir.iterdir(),
                      key=lambda p: p.stat().st_mtime if p.is_dir() else 0,
                      reverse=True):
        if not sub.is_dir():
            continue
        meta = read_level_dat(sub)
        name = meta.get("name") or sub.name
        result.append(SaveInfo(
            name=name,
            dir_name=sub.name,
            path=sub,
            game_version=meta.get("game_version", "-"),
            last_played=meta.get("last_played", "-"),
            size=utils.format_size(utils.dir_size(sub)),
            file_count=sum(1 for _ in sub.rglob("*") if _.is_file()),
            isolated_version=isolated_version,
        ))
    return result


def list_saves(mc_dir: Path) -> list[SaveInfo]:
    """扫描存档，自动识别版本隔离。

    同时检测两类位置，并合并返回：
    1. 统一存档：.minecraft/saves（未隔离版本）
    2. 版本隔离：.minecraft/versions/<版本名>/saves（PCL2 版本隔离）
    """
    result: list[SaveInfo] = []
    result += _scan_saves_dir(mc_dir / "saves", isolated_version="")
    for vdir in list_isolated_version_dirs(mc_dir):
        result += _scan_saves_dir(vdir / "saves", isolated_version=vdir.name)
    # 统一按最后修改时间倒序
    result.sort(key=lambda s: s.path.stat().st_mtime, reverse=True)
    return result


def save_backup_dir(backup_dir: Path, save_name: str) -> Path:
    """该存档专属的备份目录（按世界名安全命名）。"""
    d = backup_dir / utils.safe_name(save_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_backups(backup_dir: Path, save_name: str) -> list[Path]:
    """列出某存档的所有备份 zip（按修改时间倒序）。"""
    d = save_backup_dir(backup_dir, save_name)
    return sorted(d.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)


def backup_save(save: SaveInfo, backup_dir: Path, keep: int = 10) -> Path:
    """打包备份，并清理超出 keep 数量的旧备份。返回新备份路径。"""
    d = save_backup_dir(backup_dir, save.name)
    zip_path = d / f"{utils.safe_name(save.name)}_{utils.now_stamp()}.zip"
    utils.make_zip(save.path, zip_path)
    # 清理旧备份
    backups = sorted(d.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[keep:]:
        try:
            old.unlink()
        except OSError:
            pass
    return zip_path


def restore_save(zip_path: Path, target_dir: Path) -> Path:
    """从备份 zip 恢复到目标存档目录（覆盖式，需二次确认）。"""
    return utils.extract_zip(zip_path, target_dir)


def delete_backup(zip_path: Path) -> None:
    """删除单个备份 zip。"""
    zip_path.unlink()
