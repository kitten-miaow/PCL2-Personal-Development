<div align="center">

![MCLauncherHelper](assets/banner.png)

</div>

# MCLauncherHelper · PCL2 风格配套小工具（桌面版）

> 一款 PCL2 风格的 Minecraft 启动器配套增强工具，专注 **存档管理** 与 **Java 版本批量管理**。
> **桌面可执行软件**：打包为 .exe，任何 Windows 用户下载即用，无需安装 Python 和依赖。

## 功能特性

### 📦 存档备份与恢复（核心）
- **自动识别 PCL2 版本隔离**：同时扫描统一存档（`.minecraft/saves`）与各版本隔离存档（`.minecraft/versions/<版本名>/saves`），界面标注存档所属版本，防止不同版本 MC 互相冲突
- 扫描全部世界存档，读取 `level.dat`，展示存档名称、游戏版本、最后游玩时间
- 一键备份为 zip，备份包自动命名 `世界名_时间戳.zip`
- 备份管理：查看历史备份、删除旧备份、从备份包恢复存档（带二次确认）
- 批量备份、备份策略：保留最近 N 份备份，自动清理更早的

### ☕ Java 版本批量管理（核心）
- **自动扫描全机**：支持遍历所有盘符全盘查找 `java.exe`（自动跳过系统目录），再偏的安装位置也能找到，并实时显示扫描进度
- 快速扫描：常见目录 + 自定义额外目录
- 批量校验 Java 可用性（运行 `java -version` 测试），展示版本、位数、路径
- 导出 / 导入 Java 列表（json），重装启动器可一键恢复
- 只读操作，**不删除任何本地 java 文件**

### 🧰 附加小工具
- 一键打开 .minecraft / mods / config / saves 目录
- 实例缓存清理（日志、崩溃报告、临时文件，不碰 mod 和存档）

## 安全设计
> 本工具**只读写 PCL 的配置文件与用户指定的存档/备份目录**。
> 恢复存档、删除备份、清理缓存等危险操作**全部带确认弹窗**，防止误操作。
> 不删除任何本地 Java 文件。

## 使用方法（最终用户）
1. 拿到 `MCLauncherHelper.exe`，双击运行即可（免安装 Python）
2. 打开后进入「设置」，点「🔍 自动扫描目录」可**全盘自动发现**你的 PCL 根目录 / `.minecraft` 目录（也可手动浏览选择），一键填入
3. 回到「存档管理」即可看到存档，开始备份/管理

> ⚠️ 杀毒软件可能对未签名 exe 误报，属正常现象，选择"仍要运行"即可。

## 技术栈
- Python 3.9+
- CustomTkinter（桌面 GUI，PCL 深色界面）
- nbtlib（解析 Minecraft 存档 level.dat）
- PyInstaller（打包为 exe）

## 目录结构
```
MCLauncherHelper/
├── main.py                # 桌面版入口
├── requirements.txt       # 依赖清单
├── README.md
├── LICENSE                # MIT 开源许可证
├── .gitignore
├── assets/
│   └── banner.png         # README 封面图
├── src/
│   ├── __init__.py
│   ├── app_gui.py         # CustomTkinter 桌面界面（设置/存档/Java/工具页）
│   ├── utils.py           # 通用工具：路径、时间戳、zip、json
│   ├── pcl_parser.py      # PCL 根目录定位、config.json 解析、全盘扫描
│   ├── archive_manager.py # 存档扫描、level.dat 读取、备份、恢复、版本隔离
│   └── java_manager.py    # Java 全盘扫描、校验、配置导出
├── config/
│   └── settings.json      # 工具自身配置（首次运行自动生成）
└── dist/
    └── MCLauncherHelper.exe  # 打包产物（已提交 git，可随仓库直接下载）
```

## 从源码运行
```bash
pip install -r requirements.txt
python main.py
```

## 打包为 exe
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name MCLauncherHelper main.py
```
产物位于 `dist\MCLauncherHelper.exe`，单文件 30MB 左右，可直接分发。

## 开发计划（按提交分批）
| Commit | 内容 |
|--------|------|
| 1 | 项目初始化：目录、README、gitignore、requirements |
| 2 | PCL 配置解析（pcl_parser） |
| 3 | 存档扫描 + level.dat 读取（archive_manager 基础） |
| 4 | 存档备份 / 恢复 |
| 5 | 桌面版 UI（CustomTkinter）+ 设置页 |
| 6 | Java 扫描 + 可用性校验 |
| 7 | Java 配置导入导出 |
| 8 | 批量备份、旧备份自动清理 |
| 9 | 附加工具（打开目录、清理缓存） |
| 10 | 打包 exe + Bug 修复 + 完善文档 |

## 许可
本项目采用 [MIT 许可证](LICENSE)。与 Mojang / Microsoft / PCL 官方无关。
