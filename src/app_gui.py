"""MCLauncherHelper 桌面版主程序（CustomTkinter，PCL2 风格深色界面）。

独立可执行：打包为 exe 后，用户无需安装 Python 即可使用。
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import utils, pcl_parser, archive_manager as am, java_manager as jm

# ---- PCL2 风格深色配色 ----
BG = "#1e2026"
SIDEBAR = "#17181c"
CARD = "#25272f"
CARD_HOVER = "#2b2e37"
BORDER = "#30333d"
ACCENT = "#59e0a0"
ACCENT_DARK = "#1f8f5f"
TEXT = "#d6d9e0"
MUTED = "#8b90a0"

APP_VERSION = "0.2.0"


def run_async(func, *args, on_done=None, **kwargs):
    """在后台线程执行 func，完成后用 on_done(result) 回到主线程更新 UI。"""
    def _worker():
        try:
            result = func(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            result = e
        if on_done is not None:
            app = None
            # 找到主窗口调度
            try:
                import customtkinter as _c
                for w in _c.CTk._windows:
                    if w.winfo_exists():
                        app = w
                        break
            except Exception:
                pass
            if app is not None:
                app.after(0, lambda: on_done(result))
            else:
                on_done(result)
    threading.Thread(target=_worker, daemon=True).start()


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("MCLauncherHelper")
        self.geometry("1120x720")
        self.minsize(980, 620)
        self.settings = utils.load_settings()
        self.saves_cache: list[am.SaveInfo] = []
        self.java_cache: list[jm.JavaInfo] = []
        self._current_page = "存档管理"

        self._build_sidebar()
        self._build_content()
        self.show_page("存档管理")

    # ------------------------------------------------------------------
    # 侧边栏导航
    # ------------------------------------------------------------------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="⛏ MCLauncherHelper",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=ACCENT,
                     anchor="w").pack(padx=18, pady=(20, 0), fill="x")
        ctk.CTkLabel(self.sidebar, text=f"PCL2 配套工具 · v{APP_VERSION}",
                     font=ctk.CTkFont(size=11), text_color=MUTED,
                     anchor="w").pack(padx=18, fill="x")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(
            fill="x", padx=12, pady=14)

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for name in ["存档管理", "Java 管理", "附加工具", "设置", "关于"]:
            btn = ctk.CTkButton(
                self.sidebar, text=name, anchor="w", height=40,
                corner_radius=8, fg_color="transparent", hover_color=CARD_HOVER,
                text_color=TEXT, font=ctk.CTkFont(size=14),
                command=lambda n=name: self.show_page(n))
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[name] = btn
        self.nav_buttons["存档管理"].configure(fg_color=CARD, text_color=ACCENT)

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

    def show_page(self, name: str):
        self._current_page = name
        # 更新侧边栏高亮
        for k, b in self.nav_buttons.items():
            b.configure(fg_color=CARD if k == name else "transparent",
                        text_color=ACCENT if k == name else TEXT)
        # 清空内容区
        for w in self.content.winfo_children():
            w.destroy()
        self._page_title(name)
        if name == "存档管理":
            self._render_archive_page()
        elif name == "Java 管理":
            self._render_java_page()
        elif name == "附加工具":
            self._render_tools_page()
        elif name == "设置":
            self._render_settings_page()
        else:
            self._render_about_page()

    def _page_title(self, name: str):
        ctk.CTkLabel(self.content, text=name, font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#eef1f5", anchor="w").pack(
            padx=24, pady=(20, 6), fill="x")

    def _hint(self, text: str):
        ctk.CTkLabel(self.content, text=text, font=ctk.CTkFont(size=12),
                     text_color=MUTED, anchor="w", wraplength=820).pack(
            padx=26, pady=(0, 8), fill="x")

    # ------------------------------------------------------------------
    # 设置页
    # ------------------------------------------------------------------
    def _render_settings_page(self):
        self._hint("配置 PCL 根目录或 .minecraft 目录。所有路径留空则使用默认。")

        self.settings = utils.load_settings()
        s = self.settings
        entries: dict[str, ctk.CTkEntry] = {}

        def browse(key):
            d = filedialog.askdirectory(title="选择文件夹")
            if d:
                entries[key].delete(0, "end")
                entries[key].insert(0, d)

        def row(label, key, ph):
            f = ctk.CTkFrame(self.content, fg_color="transparent")
            f.pack(fill="x", padx=26, pady=4)
            ctk.CTkLabel(f, text=label, width=170, anchor="w",
                         text_color=TEXT).pack(side="left")
            e = ctk.CTkEntry(f, placeholder_text=ph, text_color=TEXT,
                             fg_color=CARD, border_color=BORDER)
            e.pack(side="left", fill="x", expand=True)
            ctk.CTkButton(f, text="浏览…", width=64, height=30, fg_color=CARD,
                          hover_color=CARD_HOVER, text_color=TEXT,
                          command=lambda k=key: browse(k)).pack(side="left", padx=(6, 0))
            e.insert(0, s.get(key, ""))
            entries[key] = e
            return f

        row("PCL 根目录", "pcl_root", r"D:\PCL")
        row(".minecraft 目录", "mc_dir", r"D:\PCL\.minecraft")
        row("备份保存目录", "backup_dir", r"D:\MCBackups（留空自动）")

        kf = ctk.CTkFrame(self.content, fg_color="transparent")
        kf.pack(fill="x", padx=26, pady=6)
        ctk.CTkLabel(kf, text="每个存档保留备份数", width=170, anchor="w",
                     text_color=TEXT).pack(side="left")
        keep_var = tk.StringVar(value=str(s.get("keep_backups", 10)))
        ke = ctk.CTkEntry(kf, textvariable=keep_var, width=80, text_color=TEXT,
                          fg_color=CARD, border_color=BORDER)
        ke.pack(side="left")

        def save():
            try:
                keep = max(1, min(99, int(keep_var.get())))
            except ValueError:
                keep = 10
            self.settings = {
                "pcl_root": entries["pcl_root"].get().strip(),
                "mc_dir": entries["mc_dir"].get().strip(),
                "backup_dir": entries["backup_dir"].get().strip(),
                "keep_backups": keep,
            }
            utils.save_settings(self.settings)
            messagebox.showinfo("MCLauncherHelper", "设置已保存")

        ctk.CTkButton(self.content, text="保存设置", command=save,
                      width=160, height=38, fg_color=ACCENT_DARK,
                      hover_color="#24a86e", text_color="#ffffff",
                      corner_radius=8).pack(padx=26, pady=14, anchor="w")

    # ------------------------------------------------------------------
    # 存档管理页
    # ------------------------------------------------------------------
    def _render_archive_page(self):
        self.settings = utils.load_settings()
        self._hint("自动扫描 .minecraft/saves 目录下的全部存档。备份、恢复、删除均带确认。")

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=26, pady=4)
        ctk.CTkButton(toolbar, text="🔄 刷新", width=90, height=32,
                      fg_color=CARD, hover_color=CARD_HOVER, text_color=TEXT,
                      command=self.show_page_now).pack(side="left")
        self.batch_btn = ctk.CTkButton(
            toolbar, text="批量备份", width=100, height=32, fg_color=ACCENT_DARK,
            hover_color="#24a86e", text_color="#ffffff",
            command=self._batch_backup)
        self.batch_btn.pack(side="left", padx=8)

        self.saves_scroll = ctk.CTkScrollableFrame(
            self.content, fg_color=BG, corner_radius=0)
        self.saves_scroll.pack(fill="both", expand=True, padx=18, pady=(6, 16))

        md = utils.resolve_mc_dir(self.settings)
        if md is None:
            self._empty("未配置有效的 .minecraft 目录。请到「设置」填写 PCL 根目录或 MC 目录。")
            return
        self._load_saves(md)

    def show_page_now(self):
        self.show_page(self._current_page)

    def _empty(self, text: str):
        ctk.CTkLabel(self.saves_scroll, text=text, text_color=MUTED,
                     font=ctk.CTkFont(size=14), wraplength=700).pack(pady=40)

    def _load_saves(self, md: Path):
        ctk.CTkLabel(self.saves_scroll, text="正在扫描存档…",
                     text_color=MUTED).pack(pady=30)
        run_async(am.list_saves, md, on_done=lambda r: self._render_saves(r, md))

    def _render_saves(self, result, md: Path):
        for w in self.saves_scroll.winfo_children():
            w.destroy()
        if isinstance(result, Exception):
            self._empty(f"扫描失败：{result}")
            return
        self.saves_cache = result
        backup_dir = utils.resolve_backup_dir(self.settings, md)
        if not result:
            self._empty("未发现存档。请确认目录配置，或先在游戏中创建世界。")
            return
        ctk.CTkLabel(self.saves_scroll, text=f"共 {len(result)} 个存档",
                     text_color=ACCENT, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", padx=4, pady=(0, 6))
        self._save_rows = []
        for i, s in enumerate(result):
            self._save_rows.append(self._build_save_row(s, backup_dir))

    def _build_save_row(self, s: am.SaveInfo, backup_dir: Path):
        card = ctk.CTkFrame(self.saves_scroll, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=5, padx=2)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=14, pady=10)
        title = f"🗺 {s.name}"
        if s.isolated_version:
            title += f"   🔒 版本隔离：{s.isolated_version}"
        ctk.CTkLabel(info, text=title, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#eef1f5", anchor="w").pack(fill="x")
        ctk.CTkLabel(
            info,
            text=f"版本 {s.game_version} ｜ 最后游玩 {s.last_played} ｜ 大小 {s.size} ｜ {s.file_count} 个文件",
            font=ctk.CTkFont(size=12), text_color=MUTED, anchor="w",
            wraplength=600).pack(fill="x")
        ctk.CTkLabel(info, text=f"目录：{s.path}", font=ctk.CTkFont(size=11),
                     text_color=MUTED, anchor="w").pack(fill="x")

        btns = ctk.CTkFrame(card, fg_color="transparent", width=200)
        btns.pack(side="right", padx=10, pady=10)
        btns.pack_propagate(False)
        ctk.CTkButton(btns, text="备份", width=80, height=30, fg_color=ACCENT_DARK,
                      hover_color="#24a86e", text_color="#ffffff",
                      command=lambda: self._do_backup(s, backup_dir)).pack(pady=2)
        ctk.CTkButton(btns, text="备份历史", width=80, height=30, fg_color=CARD,
                      hover_color=CARD_HOVER, text_color=TEXT,
                      command=lambda: self._open_history(s, backup_dir)).pack(pady=2)
        return card

    def _do_backup(self, s: am.SaveInfo, backup_dir: Path):
        if not messagebox.askyesno("备份存档", f"确定备份存档「{s.name}」吗？"):
            return
        try:
            z = am.backup_save(s, backup_dir, keep=int(self.settings.get("keep_backups", 10)))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("备份失败", str(e))
            return
        messagebox.showinfo("备份完成", f"已备份：\n{z.name}")

    def _batch_backup(self):
        if not self.saves_cache:
            messagebox.showwarning("批量备份", "暂无可备份的存档")
            return
        if not messagebox.askyesno("批量备份", f"确定备份全部 {len(self.saves_cache)} 个存档吗？"):
            return
        md = utils.resolve_mc_dir(self.settings)
        backup_dir = utils.resolve_backup_dir(self.settings, md)
        done, fail = 0, 0
        for s in self.saves_cache:
            try:
                am.backup_save(s, backup_dir, keep=int(self.settings.get("keep_backups", 10)))
                done += 1
            except Exception:  # noqa: BLE001
                fail += 1
        messagebox.showinfo("批量备份", f"成功 {done} 个，失败 {fail} 个")

    def _open_history(self, s: am.SaveInfo, backup_dir: Path):
        win = ctk.CTkToplevel(self)
        win.title(f"备份历史 - {s.name}")
        win.geometry("680x420")
        win.configure(fg_color=BG)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text=f"「{s.name}」的历史备份", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#eef1f5").pack(padx=16, pady=(14, 6), anchor="w")

        bks = am.list_backups(backup_dir, s.name)
        scroll = ctk.CTkScrollableFrame(win, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=12, pady=6)
        if not bks:
            ctk.CTkLabel(scroll, text="暂无备份", text_color=MUTED).pack(pady=20)
            return
        for b in bks:
            row = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=8, border_width=1,
                               border_color=BORDER)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=b.name, font=ctk.CTkFont(size=12), text_color=TEXT,
                         anchor="w").pack(side="left", padx=10, pady=8, fill="x", expand=True)
            ctk.CTkButton(row, text="恢复", width=64, height=28, fg_color=ACCENT_DARK,
                          text_color="#ffffff",
                          command=lambda b=b: self._confirm_restore(win, s, b)).pack(
                side="right", padx=(0, 6), pady=6)
            ctk.CTkButton(row, text="删除", width=64, height=28, fg_color=CARD,
                          hover_color="#7a2b2b", text_color="#ff8a8a",
                          command=lambda b=b: self._confirm_delete(win, s, b)).pack(
                side="right", pady=6)

    def _confirm_restore(self, win, s: am.SaveInfo, backup: Path):
        if not messagebox.askyesno(
                "恢复存档",
                f"恢复将【覆盖】当前存档「{s.name}」，且不可撤销！\n\n备份文件：{backup.name}\n\n确认继续？",
                icon="warning"):
            return
        try:
            am.restore_save(backup, s.path)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("恢复失败", str(e))
            return
        messagebox.showinfo("恢复完成", "存档已恢复")
        win.destroy()

    def _confirm_delete(self, win, s: am.SaveInfo, backup: Path):
        if not messagebox.askyesno(
                "删除备份", f"确认删除备份文件？\n\n{backup.name}", icon="warning"):
            return
        try:
            am.delete_backup(backup)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("删除失败", str(e))
            return
        messagebox.showinfo("已删除", "备份已删除")
        win.destroy()

    # ------------------------------------------------------------------
    # Java 管理页
    # ------------------------------------------------------------------
    def _render_java_page(self):
        self._hint("扫描本机 Java，识别版本与可用性。只读操作，不会改动任何 Java 文件。")

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=26, pady=4)
        ctk.CTkButton(toolbar, text="🔍 扫描并校验", width=120, height=34,
                      fg_color=ACCENT_DARK, hover_color="#24a86e", text_color="#ffffff",
                      command=self._scan_java).pack(side="left")
        ctk.CTkButton(toolbar, text="💿 全盘扫描", width=110, height=34, fg_color=CARD,
                      hover_color=CARD_HOVER, text_color=TEXT,
                      command=self._scan_whole_disk).pack(side="left", padx=8)
        self.extra_entry = ctk.CTkEntry(toolbar, placeholder_text="额外 Java 目录（可选，分号分隔）",
                                        fg_color=CARD, border_color=BORDER,
                                        text_color=TEXT, width=300)
        self.extra_entry.pack(side="left", padx=10)

        self.java_scroll = ctk.CTkScrollableFrame(self.content, fg_color=BG, corner_radius=0)
        self.java_scroll.pack(fill="both", expand=True, padx=18, pady=(6, 10))

        bottom = ctk.CTkFrame(self.content, fg_color="transparent")
        bottom.pack(fill="x", padx=26, pady=(0, 14))
        ctk.CTkButton(bottom, text="导出为 JSON", width=120, height=32, fg_color=CARD,
                      hover_color=CARD_HOVER, text_color=TEXT,
                      command=self._export_java).pack(side="left")
        ctk.CTkButton(bottom, text="导入 JSON", width=120, height=32, fg_color=CARD,
                      hover_color=CARD_HOVER, text_color=TEXT,
                      command=self._import_java).pack(side="left", padx=8)
        self.java_status = ctk.CTkLabel(bottom, text="", text_color=ACCENT,
                                        font=ctk.CTkFont(size=12))
        self.java_status.pack(side="left", padx=14)

        if self.java_cache:
            self._render_java_list(self.java_cache)

    def _scan_java(self):
        self.java_status.configure(text="正在扫描并校验…")
        extra = [Path(x.strip()) for x in self.extra_entry.get().split(";") if x.strip()]
        run_async(jm.scan_java, extra, on_done=self._render_java_list)

    def _scan_whole_disk(self):
        """全盘遍历所有盘符查找 java.exe（跳过系统目录），后台执行并实时显示进度。"""
        self.java_status.configure(text="正在全盘扫描（跳过系统目录），可能需要几分钟…")
        extra = [Path(x.strip()) for x in self.extra_entry.get().split(";") if x.strip()]

        def progress(drive, found, cur, total):
            self.after(0, lambda: self.java_status.configure(
                text=f"正在扫描 {drive}（{cur}/{total} 个盘）…已找到 {found} 个 Java"))

        def worker():
            try:
                paths = jm.scan_java_whole_disk(progress=progress)
                # 合并额外目录
                extra_found = jm.scan_java_dirs(extra)
                merged = {str(Path(p)).lower(): Path(p) for p in list(paths) + extra_found}
                infos = [jm.probe_java(p) for p in merged.values()]
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self.java_status.configure(text=f"全盘扫描失败：{e}"))
                return
            self.after(0, lambda: self._render_java_list(infos))

        threading.Thread(target=worker, daemon=True).start()

    def _render_java_list(self, result):
        for w in self.java_scroll.winfo_children():
            w.destroy()
        if isinstance(result, Exception):
            self.java_status.configure(text=f"扫描失败：{result}")
            return
        self.java_cache = result
        ok = sum(1 for x in result if x.ok)
        self.java_status.configure(text=f"发现 {len(result)} 个，可用 {ok} 个")
        if not result:
            ctk.CTkLabel(self.java_scroll, text="未发现 Java，可填写额外目录再试。",
                         text_color=MUTED).pack(pady=30)
            return
        for x in result:
            card = ctk.CTkFrame(self.java_scroll, fg_color=CARD, corner_radius=8,
                                border_width=1, border_color=BORDER)
            card.pack(fill="x", pady=3)
            state = "✅ 可用" if x.ok else "❌ 不可用"
            col = ACCENT if x.ok else "#ff8a8a"
            ctk.CTkLabel(card, text=f"{x.version}（{x.bitness}位）",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=col, width=180, anchor="w").pack(
                side="left", padx=12, pady=8)
            ctk.CTkLabel(card, text=str(x.path), font=ctk.CTkFont(size=12),
                         text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(card, text=state, font=ctk.CTkFont(size=12),
                         text_color=col, width=90, anchor="e").pack(side="right", padx=12)

    def _export_java(self):
        if not self.java_cache:
            messagebox.showwarning("导出", "请先扫描 Java")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile="java_list.json", title="导出 Java 列表")
        if not path:
            return
        data = [jm.build_pcl_java_entry(x) for x in self.java_cache]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("导出", f"已导出到：\n{path}")

    def _import_java(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], title="导入 Java 列表")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("导入失败", str(e))
            return
        added = 0
        for item in data:
            jp = Path(item.get("Path", "")).expanduser()
            if jp.is_file() and all(jp != x.path for x in self.java_cache):
                self.java_cache.append(jm.probe_java(jp))
                added += 1
        self._render_java_list(self.java_cache)
        messagebox.showinfo("导入", f"导入完成，新增 {added} 个 Java")

    # ------------------------------------------------------------------
    # 附加工具页
    # ------------------------------------------------------------------
    def _render_tools_page(self):
        md = utils.resolve_mc_dir(self.settings)
        if md is None:
            self._hint("请先在「设置」配置 .minecraft 目录。")
            return
        self._hint("快捷打开常用目录，或清理日志/崩溃报告/临时文件（不删除 mod 和存档）。")

        f = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=10, border_width=1,
                         border_color=BORDER)
        f.pack(fill="x", padx=26, pady=8)
        ctk.CTkLabel(f, text="📂 快捷打开目录", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#eef1f5").pack(padx=16, pady=(12, 6), anchor="w")
        # 版本作用域选择：统一目录 或 某个隔离版本
        self.tools_base = md
        scope_row = ctk.CTkFrame(f, fg_color="transparent")
        scope_row.pack(fill="x", padx=14, pady=(2, 6))
        ctk.CTkLabel(scope_row, text="版本作用域：", font=ctk.CTkFont(size=13),
                     text_color=MUTED).pack(side="left")
        versions = am.list_isolated_version_dirs(md)
        choices = ["📁 统一目录（非隔离）"] + [f"🔒 {v.name}" for v in versions]
        self.tools_scope_var = tk.StringVar(value=choices[0])

        def on_scope(choice: str):
            if choice.startswith("🔒"):
                self.tools_base = md / "versions" / choice[2:].strip()
            else:
                self.tools_base = md
            self.tools_scope_label.configure(text=f"→ {self.tools_base}")

        ctk.CTkOptionMenu(scope_row, values=choices, variable=self.tools_scope_var,
                          command=on_scope, width=280, fg_color=CARD,
                          button_color=CARD_HOVER, button_hover_color="#3a3e49",
                          text_color=TEXT, dropdown_fg_color=CARD,
                          dropdown_hover_color=CARD_HOVER, dropdown_text_color=TEXT
                          ).pack(side="left", padx=(0, 8))
        self.tools_scope_label = ctk.CTkLabel(scope_row, text=f"→ {md}",
                                              font=ctk.CTkFont(size=12),
                                              text_color=ACCENT, anchor="w")
        self.tools_scope_label.pack(side="left", fill="x", expand=True)

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))
        for label in ["mods", "config", "saves", "版本根目录"]:
            ctk.CTkButton(row, text=f"打开 {label}", width=110, height=34, fg_color=CARD,
                          hover_color=CARD_HOVER, text_color=TEXT,
                          command=lambda l=label: self._open_dir(
                              self.tools_base if l == "版本根目录" else self.tools_base / l)
                          ).pack(side="left", padx=4)

        f2 = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=10, border_width=1,
                          border_color=BORDER)
        f2.pack(fill="x", padx=26, pady=8)
        ctk.CTkLabel(f2, text="🧹 缓存清理", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#eef1f5").pack(padx=16, pady=(12, 4), anchor="w")
        ctk.CTkLabel(f2, text="只清理 logs、crash-reports 与临时文件，不删除 mod 和存档。",
                     text_color=MUTED, font=ctk.CTkFont(size=12),
                     anchor="w").pack(padx=16, fill="x")
        ctk.CTkButton(f2, text="开始清理", width=140, height=34, fg_color=ACCENT_DARK,
                      hover_color="#24a86e", text_color="#ffffff",
                      command=lambda: self._clean_cache(md)).pack(padx=16, pady=10, anchor="w")

    def _open_dir(self, p: Path):
        try:
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(str(p))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("打开失败", str(e))

    def _clean_cache(self, md: Path):
        if not messagebox.askyesno("清理缓存", "确定清理日志、崩溃报告与临时文件吗？", icon="warning"):
            return
        removed = 0
        for sub in ("logs", "crash-reports"):
            t = md / sub
            if t.is_dir():
                shutil.rmtree(t)
                removed += 1
        for pat in ("*.tmp", "*.bak"):
            for f in md.glob(pat):
                try:
                    f.unlink()
                    removed += 1
                except OSError:
                    pass
        messagebox.showinfo("清理完成", f"已清理 {removed} 项")

    # ------------------------------------------------------------------
    # 关于页
    # ------------------------------------------------------------------
    def _render_about_page(self):
        self._hint("PCL2 风格的 Minecraft 启动器配套增强工具。")
        info = (
            "一款 PCL2 风格的 Minecraft 启动器配套增强工具，专注「存档管理」与「Java 批量管理」。\n\n"
            "· 不替换原有启动器，作为辅助面板使用\n"
            "· 只读写 PCL 配置文件与用户指定的备份目录，不删除任何本地 Java\n"
            "· 危险操作（恢复/删除/清理）全部带确认\n\n"
            f"版本 {APP_VERSION} ｜ Python + CustomTkinter"
        )
        box = ctk.CTkTextbox(self.content, fg_color=CARD, corner_radius=10,
                             text_color=TEXT, font=ctk.CTkFont(size=13),
                             height=200, wrap="word", border_width=1, border_color=BORDER)
        box.pack(fill="x", padx=26, pady=10)
        box.insert("1.0", info)
        box.configure(state="disabled")


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
