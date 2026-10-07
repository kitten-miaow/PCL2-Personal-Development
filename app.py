"""MCLauncherHelper · Streamlit 主程序（PCL2 风格深色界面）"""
import os
import shutil
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import utils, pcl_parser, archive_manager as am, java_manager as jm

st.set_page_config(page_title="MCLauncherHelper", page_icon="⛏", layout="wide")

# 注入深色样式
_css = (Path(__file__).resolve().parent / "assets" / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

APP_VERSION = "0.1.0"

# --------------------------------------------------------------------------
# 侧边栏：Logo + 导航 + 设置
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="mc-logo">⛏ MCLauncherHelper</div>'
                f'<div class="mc-sub">PCL2 配套工具 · v{APP_VERSION}</div>', unsafe_allow_html=True)
    st.divider()
    nav = st.radio("功能导航", ["存档管理", "Java 管理", "附加工具", "关于"],
                   label_visibility="collapsed")

    settings = utils.load_settings()
    with st.expander("⚙️ 设置", expanded=settings.get("pcl_root") is None):
        pcl_root = st.text_input("PCL 根目录（含 .minecraft）", value=settings.get("pcl_root", ""),
                                 placeholder=r"D:\PCL")
        mc_dir = st.text_input(".minecraft 目录（留空自动用 PCL）", value=settings.get("mc_dir", ""),
                               placeholder=r"D:\PCL\.minecraft")
        backup_dir = st.text_input("备份保存目录（留空自动）", value=settings.get("backup_dir", ""),
                                   placeholder=r"D:\MCBackups")
        keep = st.number_input("每个存档保留最近备份数", min_value=1, max_value=99,
                               value=int(settings.get("keep_backups", 10)))
        if st.button("保存设置", use_container_width=True):
            settings.update(pcl_root=pcl_root.strip(), mc_dir=mc_dir.strip(),
                            backup_dir=backup_dir.strip(), keep_backups=int(keep))
            utils.save_settings(settings)
            st.success("设置已保存")
            st.rerun()


def _mc_dir():
    """返回可用的 .minecraft 目录，没有则提示。"""
    md = utils.resolve_mc_dir(settings)
    if md is None:
        st.warning("尚未配置有效的 .minecraft 目录，请在左侧「设置」填写 PCL 根目录或 MC 目录。")
    return md


# --------------------------------------------------------------------------
# 页面：存档管理
# --------------------------------------------------------------------------
def page_archive():
    st.markdown("## 📦 存档备份与恢复")
    md = _mc_dir()
    if md is None:
        return
    saves = am.list_saves(md)
    backup_dir = utils.resolve_backup_dir(settings, md)
    st.caption(f"存档目录：`{am.find_saves_dir(md)}` ｜ 共 {len(saves)} 个存档")

    if not saves:
        st.info("未发现存档。请确认目录配置正确，或先在游戏中创建世界。")
        return

    # ---- 批量备份 ----
    st.markdown("### 批量备份")
    choices = st.multiselect("勾选要备份的存档", [f"{s.name}（{s.dir_name}）" for s in saves])
    if st.button(f"备份所选（{len(choices)} 个）", type="primary", disabled=not choices):
        keep_n = int(settings.get("keep_backups", 10))
        for c in choices:
            name = c.split("（")[0]
            s = next(x for x in saves if x.name == name)
            z = am.backup_save(s, backup_dir, keep=keep_n)
            st.write(f"✅ 已备份：`{z.name}`")
        st.success("批量备份完成")
        st.rerun()

    st.divider()
    st.markdown("### 存档列表")
    for s in saves:
        with st.container():
            st.markdown(
                f'<div class="mc-card">'
                f'<div class="title">🗺 {s.name}</div>'
                f'<div class="meta">'
                f'<b>版本</b> {s.game_version} ｜ <b>最后游玩</b> {s.last_played} ｜ '
                f'<b>大小</b> {s.size} ｜ <b>文件数</b> {s.file_count}<br>'
                f'<b>目录</b> {s.path}</div></div>',
                unsafe_allow_html=True)

            c1, c2 = st.columns([1, 3])
            with c1:
                if st.button("一键备份", key=f"bk_{s.dir_name}"):
                    z = am.backup_save(s, backup_dir, keep=int(settings.get("keep_backups", 10)))
                    st.success(f"已备份：{z.name}")
                    st.rerun()
            with c2:
                bks = am.list_backups(backup_dir, s.name)
                st.caption(f"历史备份 {len(bks)} 份")
                with st.expander(f"查看历史备份（{len(bks)}）"):
                    if not bks:
                        st.write("暂无备份")
                    for b in bks:
                        col_a, col_b, col_c = st.columns([4, 1, 1])
                        col_a.write(b.name)
                        if col_b.button("恢复", key=f"res_{b.stem}"):
                            st.session_state[f"cfm_res_{b.stem}"] = True
                        if col_c.button("删除", key=f"del_{b.stem}"):
                            st.session_state[f"cfm_del_{b.stem}"] = True

                        # 恢复二次确认
                        if st.session_state.get(f"cfm_res_{b.stem}"):
                            st.warning(f"恢复将**覆盖**当前存档「{s.name}」，且不可撤销！")
                            c_ok, c_no = st.columns(2)
                            if c_ok.button("确认恢复", key=f"cfm_res_ok_{b.stem}", type="primary"):
                                am.restore_save(b, s.path)
                                st.success("恢复完成")
                                st.session_state.pop(f"cfm_res_{b.stem}", None)
                                st.rerun()
                            if c_no.button("取消", key=f"cfm_res_no_{b.stem}"):
                                st.session_state.pop(f"cfm_res_{b.stem}", None)
                                st.rerun()
                        # 删除二次确认
                        if st.session_state.get(f"cfm_del_{b.stem}"):
                            st.warning(f"确认删除备份文件 `{b.name}` ？")
                            c_ok, c_no = st.columns(2)
                            if c_ok.button("确认删除", key=f"cfm_del_ok_{b.stem}", type="primary"):
                                am.delete_backup(b)
                                st.success("已删除")
                                st.session_state.pop(f"cfm_del_{b.stem}", None)
                                st.rerun()
                            if c_no.button("取消删除", key=f"cfm_del_no_{b.stem}"):
                                st.session_state.pop(f"cfm_del_{b.stem}", None)
                                st.rerun()


# --------------------------------------------------------------------------
# 页面：Java 管理
# --------------------------------------------------------------------------
def page_java():
    st.markdown("## ☕ Java 版本批量管理")
    extra_str = st.text_input("额外 Java 目录（可选，多个用分号隔开）", placeholder=r"C:\Custom\Java")

    scan_col = st.button("🔍 扫描并校验本地 Java", type="primary")
    st.caption("仅扫描常见安装目录 + 你填写的额外目录，不会改动任何本地文件。")

    java_list = st.session_state.get("java_list", [])
    if scan_col:
        extra = [Path(x.strip()) for x in extra_str.split(";") if x.strip()]
        java_list = jm.scan_java(extra)
        st.session_state["java_list"] = java_list

    if not java_list:
        st.info("点击上方按钮扫描本机 Java。")
        return

    ok_count = sum(1 for x in java_list if x.ok)
    st.write(f"发现 **{len(java_list)}** 个 Java，其中可用 **{ok_count}** 个。")

    # 表格展示
    rows = [[str(x.path), x.version, x.bitness, "✅ 可用" if x.ok else "❌ 不可用", x.detail]
            for x in java_list]
    st.dataframe(rows, column_config={
        "0": st.column_config.TextColumn("路径"), "1": "版本",
        "2": "位数", "3": "状态", "4": "详情",
    }, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### 导出 / 导入 Java 列表")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("导出为 JSON"):
            data = [jm.build_pcl_java_entry(x) for x in java_list]
            out = Path(utils.CONFIG_PATH.parent.parent) / "java_list_export.json"
            out.write_text(__import__("json").dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success(f"已导出到 `{out}`")
    with c2:
        imp = st.text_input("导入 JSON 文件路径", placeholder=r"D:\java_list.json")
        if st.button("导入并合并"):
            p = Path(imp.strip())
            if p.is_file():
                import json as _json
                data = _json.loads(p.read_text(encoding="utf-8"))
                for item in data:
                    jp = Path(item.get("Path", "")).expanduser()
                    if jp.is_file() and all(jp != x.path for x in java_list):
                        java_list.append(jm.probe_java(jp))
                st.session_state["java_list"] = java_list
                st.success(f"导入完成，当前 {len(java_list)} 个")
                st.rerun()
            else:
                st.error("文件不存在，请检查路径")

    st.divider()
    st.markdown("### 生成 PCL Java 配置")
    if st.button("生成配置 JSON（可复制到 PCL config.json）"):
        data = [jm.build_pcl_java_entry(x) for x in java_list if x.ok]
        st.code(__import__("json").dumps(data, ensure_ascii=False, indent=2), language="json")


# --------------------------------------------------------------------------
# 页面：附加工具
# --------------------------------------------------------------------------
def page_tools():
    st.markdown("## 🧰 附加小工具")
    md = _mc_dir()
    if md is None:
        return
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📂 快捷打开目录")
        for label, p in [(".minecraft", md), ("mods", md / "mods"),
                         ("config", md / "config"), ("saves", md / "saves")]:
            if st.button(f"打开 {label}", key=f"open_{label}"):
                p.mkdir(parents=True, exist_ok=True)
                os.startfile(str(p))
    with c2:
        st.markdown("### 🧹 缓存清理")
        st.caption("只清理日志、崩溃报告与临时文件，**不删除 mod 和存档**。")
        if st.button("清理日志 / 崩溃报告 / 临时文件", type="primary"):
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
            st.success(f"清理完成，移除 {removed} 项")


# --------------------------------------------------------------------------
# 页面：关于
# --------------------------------------------------------------------------
def page_about():
    st.markdown("## 关于 MCLauncherHelper")
    st.markdown("""
一款 PCL2 风格的 Minecraft 启动器配套增强工具，专注 **存档管理** 与 **Java 批量管理**。

- **不替换** 原有启动器，作为辅助面板使用
- 只读写 PCL 配置文件与用户指定的备份目录，**不删除任何本地 Java**
- 危险操作（恢复/删除/清理）全部带二次确认

技术栈：Python + Streamlit + nbtlib
""")


# --------------------------------------------------------------------------
# 路由
# --------------------------------------------------------------------------
if nav == "存档管理":
    page_archive()
elif nav == "Java 管理":
    page_java()
elif nav == "附加工具":
    page_tools()
else:
    page_about()
