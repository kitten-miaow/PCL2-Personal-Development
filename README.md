# MCLauncherHelper · PCL2 风格配套小工具

> 一款 PCL2 风格的 Minecraft 启动器配套增强工具，专注 **存档管理** 与 **Java 版本批量管理**。
> 轻量化本地工具，不替换原有启动器，作为 PCL2 的辅助面板使用。

## 功能特性

### 📦 存档备份与恢复（核心）
- 扫描 PCL 实例的存档目录（`.minecraft/saves`），列出所有世界存档
- 读取 `level.dat`，展示存档名称、游戏版本、最后游玩时间
- 一键备份为 zip，备份包自动命名 `世界名_时间戳.zip`
- 备份管理：查看历史备份、删除旧备份、从备份包恢复存档（带二次确认）
- 批量备份：勾选多个存档一次性打包
- 备份策略：可设置「保留最近 N 份备份，自动清理更早的」

### ☕ Java 版本批量管理（核心）
- 扫描本地 Java 目录，识别 `java.exe`，提取版本、位数、路径
- 批量校验 Java 可用性（运行 `java -version` 测试）
- 生成/更新 PCL 的 Java 配置条目（只写配置文件，**不删除任何本地 java 文件**）
- 导出 / 导入 Java 列表（json），重装启动器可一键恢复

### 🧰 附加小工具
- 一键打开 PCL 根目录 / mods 目录 / config 目录
- 实例缓存清理（日志、崩溃报告、临时文件，不碰 mod 和存档）

## 安全设计
> 本工具**只读写 PCL 的配置文件与用户指定的存档/备份目录**。
> 恢复存档、删除备份、清理缓存等危险操作**全部带二次确认**，防止误操作。
> 不删除任何本地 Java 文件。

## 技术栈
- Python 3.9+
- Streamlit（WebGUI，仿 PCL 深色界面）
- nbtlib（解析 Minecraft 存档 level.dat）
- pathlib / shutil / zipfile（文件与打包）

## 目录结构
```
MCLauncherHelper/
├── app.py                 # Streamlit 主程序入口
├── requirements.txt       # 依赖清单
├── README.md
├── .gitignore
├── src/
│   ├── utils.py           # 通用工具：路径、时间戳、zip、json
│   ├── pcl_parser.py      # PCL 根目录定位、config.json 解析
│   ├── archive_manager.py # 存档扫描、level.dat 读取、备份、恢复
│   └── java_manager.py    # Java 扫描、校验、PCL 配置生成
├── config/
│   └── settings.json      # 工具自身配置（首次运行自动生成）
└── assets/
    └── style.css          # PCL 深色主题样式
```

## 快速开始
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
streamlit run app.py
```

首次运行在侧边栏「设置」中填入你的 PCL 根目录（或 MC 目录），工具会自动扫描。

## 开发计划（按提交分批）
| Commit | 内容 |
|--------|------|
| 1 | 项目初始化：目录、README、gitignore、requirements |
| 2 | PCL 配置解析（pcl_parser） |
| 3 | 存档扫描 + level.dat 读取（archive_manager 基础） |
| 4 | 存档备份 / 恢复 |
| 5 | Streamlit 页面框架 + PCL 深色样式 |
| 6 | Java 扫描 + 可用性校验 |
| 7 | Java 批量导入 PCL 配置、清理无效条目 |
| 8 | 批量备份、旧备份自动清理 |
| 9 | 附加工具（打开目录、清理缓存） |
| 10 | Bug 修复 + 完善文档 |

## 许可
仅供个人学习使用。与 Mojang / Microsoft / PCL 官方无关。
